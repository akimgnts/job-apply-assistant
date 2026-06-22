import logging
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from sqlalchemy.orm import Session
from app.database.db import SessionLocal
from app.config import config
from app.services.elevia_gateway import EleviaGateway
from app.services.elevia_user_service import EleviaUserService
from app.agents.elevia_agent import EleviaAgent
from app.bot.keyboards import home_menu, offer_extracted_menu

logger = logging.getLogger(__name__)


async def elevia_health_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Check Elevia API health."""
    is_healthy = await EleviaAgent.health_check()

    if is_healthy:
        await update.message.reply_text("✅ Elevia API est disponible!")
    else:
        await update.message.reply_text(
            "❌ Elevia API n'est pas disponible.\n\n"
            "Vérifiez la configuration ou réessayez plus tard."
        )


async def search_offers_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Search for offers with natural language query."""
    if not context.args:
        await update.message.reply_text(
            "Usage: /search_offers <query>\n\n"
            "Exemples:\n"
            "  /search_offers data scientist Spain\n"
            "  /search_offers engineer France\n"
            "  /search_offers business analyst Germany"
        )
        return

    query = " ".join(context.args)
    await update.message.reply_text(f"🔍 Recherche pour: {query}...")

    db = SessionLocal()
    try:
        user_id = str(update.effective_user.id)
        result = await EleviaAgent.search_and_rank_offers(
            db,
            user_id,
            query=query,
            limit=10,
        )

        if not result.get("success"):
            await update.message.reply_text(
                f"❌ Erreur: {result.get('error', 'Unknown error')}"
            )
            return

        offers = result.get("offers", [])
        ranking_mode = result.get("ranking_mode", "unknown")

        if not offers:
            await update.message.reply_text(
                f"❌ Aucune offre trouvée pour: {query}\n\n"
                "Essayez une autre recherche."
            )
            return

        response = f"📋 Trouvé {len(offers)} offres ({ranking_mode})\n\n"
        for i, offer in enumerate(offers[:10], 1):
            title = offer.get("title", "Unknown Position")
            company = offer.get("company", "Unknown Company")
            location = offer.get("city", "Unknown Location")
            offer_id = offer.get("id", offer.get("offer_id", ""))

            response += f"{i}. {title}\n"
            response += f"   {company} — {location}\n"
            if offer_id:
                response += f"   ID: `{offer_id}`\n"
            response += "\n"

        await update.message.reply_text(response, parse_mode="Markdown")

    except Exception as e:
        logger.error("[ELEVIA_HANDLER] Error in search: %s", str(e), exc_info=True)
        await update.message.reply_text(
            f"❌ Erreur: {str(e)[:100]}"
        )
    finally:
        db.close()


async def load_elevia_offer_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Load and analyze specific Elevia offer."""
    if not context.args:
        await update.message.reply_text(
            "Usage: /load_elevia_offer <offer_id>\n\n"
            "Exemple: /load_elevia_offer BF-12345"
        )
        return

    offer_id = context.args[0]
    await update.message.reply_text(f"⏳ Chargement de l'offre: {offer_id}...")

    user_id = str(update.effective_user.id)
    db = SessionLocal()

    try:
        result = await EleviaAgent.load_and_prepare_offer(
            db,
            offer_id,
            user_id,
        )

        if not result.get("success"):
            await update.message.reply_text(
                f"❌ Impossible de charger l'offre:\n{result.get('error', 'Unknown error')}"
            )
            return

        offer_context_dict = result.get("offer_context", {})
        profile_id = result.get("profile_id")
        positioning = result.get("positioning", "Unknown Position")

        title = offer_context_dict.get("job_title", "Unknown")
        company = offer_context_dict.get("company", "Unknown")
        location = offer_context_dict.get("location", "Unknown")
        description = offer_context_dict.get("offer_detail", {}).get("description", "")
        skills = offer_context_dict.get("offer_detail", {}).get("required_skills", [])
        match_score = offer_context_dict.get("matching_context", {}).get("score")

        response = f"📄 {title}\n\n"
        response += f"🏢 {company}\n"
        response += f"📍 {location}\n"
        if match_score:
            response += f"📊 Match (profile): {match_score:.1f}/10\n"
        response += "\n"

        if description:
            response += f"📝 Description:\n{description[:400]}\n\n"

        if skills:
            response += f"🔧 Compétences requises:\n"
            response += ", ".join(skills[:8]) + "\n\n"

        response += "Que veux-tu faire?\n"
        response += "• GO — Générer CV + lettre + mail\n"
        response += "• CV — Générer seulement le CV\n"
        response += "• LETTRE — Générer seulement la lettre"

        await update.message.reply_text(response, reply_markup=home_menu())

        # Store offer context in user context for next command
        if context.user_data is None:
            context.user_data = {}
        context.user_data["elevia_offer_context"] = offer_context_dict
        context.user_data["elevia_offer_id"] = offer_id
        context.user_data["elevia_positioning"] = positioning
        context.user_data["elevia_profile_id"] = profile_id

        logger.info(
            "[ELEVIA_HANDLER] Offer loaded and stored for user %s: %s",
            user_id,
            offer_id,
        )

    except Exception as e:
        logger.error(
            "[ELEVIA_HANDLER] Error loading offer: %s",
            str(e),
            exc_info=True,
        )
        await update.message.reply_text(
            f"❌ Erreur lors du chargement: {str(e)[:100]}"
        )
    finally:
        db.close()


async def catalog_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Browse job offers catalog."""
    page = 1
    if context.args:
        try:
            page = int(context.args[0])
        except ValueError:
            pass

    limit = 10
    offset = (page - 1) * limit

    await update.message.reply_text(f"📋 Parcourir le catalogue (page {page})...")

    db = SessionLocal()
    try:
        user_id = str(update.effective_user.id)
        result = await EleviaAgent.search_and_rank_offers(
            db,
            user_id,
            query=None,
            limit=limit + 1,
        )

        if not result.get("success"):
            await update.message.reply_text(
                f"❌ Erreur: {result.get('error', 'Unknown error')}"
            )
            return

        offers = result.get("offers", [])
        if not offers:
            await update.message.reply_text(
                "❌ Aucune offre disponible pour le moment."
            )
            return

        paginated_offers = offers[offset : offset + limit]
        has_next = len(offers) > offset + limit

        response = f"📋 Catalogue des offres (page {page})\n\n"
        for i, offer in enumerate(paginated_offers, offset + 1):
            title = offer.get("title", "Unknown Position")
            company = offer.get("company", "Unknown Company")
            location = offer.get("city", "Unknown Location")
            offer_id = offer.get("id", offer.get("offer_id", ""))

            response += f"{i}. {title}\n"
            response += f"   {company} — {location}\n"
            if offer_id:
                response += f"   `/load_elevia_offer {offer_id}`\n"
            response += "\n"

        if has_next:
            response += f"\n➡️ `/catalog {page + 1}` pour la page suivante"

        await update.message.reply_text(response, parse_mode="Markdown")

    except Exception as e:
        logger.error("[ELEVIA_HANDLER] Error in catalog: %s", str(e), exc_info=True)
        await update.message.reply_text(f"❌ Erreur: {str(e)[:100]}")
    finally:
        db.close()

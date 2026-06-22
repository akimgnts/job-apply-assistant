import logging
from telegram import Update
from telegram.ext import ContextTypes
from sqlalchemy.orm import Session
from app.database.db import SessionLocal
from app.config import config
from app.services.elevia_gateway import EleviaGateway
from app.bot.keyboards import home_menu

logger = logging.getLogger(__name__)


async def elevia_health_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Check Elevia API health."""
    gateway = EleviaGateway()
    is_healthy = await gateway.health_check()

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

    gateway = EleviaGateway()
    offers = await gateway.search_offers(query=query, limit=10)

    if not offers:
        await update.message.reply_text(
            f"❌ Aucune offre trouvée pour: {query}\n\n"
            "Essayez une autre recherche."
        )
        return

    response = f"📋 Trouvé {len(offers)} offres pour: {query}\n\n"
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

    # Get user's profile_id if exists
    user_id = str(update.effective_user.id)
    db = SessionLocal()

    try:
        # For now, load without profile context
        # In future, retrieve user's elevia_profile_id from DB
        gateway = EleviaGateway()
        offer_context = await gateway.get_offer_context(offer_id=offer_id)

        if not offer_context:
            await update.message.reply_text(
                f"❌ Impossible de charger l'offre: {offer_id}\n\n"
                "Vérifiez que l'ID est correct."
            )
            return

        title = offer_context.get_job_title()
        company = offer_context.get_company()
        location = offer_context.get_location()
        description = offer_context.get_description()
        skills = offer_context.get_required_skills()
        match_score = offer_context.get_match_score()

        response = f"📄 {title}\n\n"
        response += f"🏢 {company}\n"
        response += f"📍 {location}\n"
        if match_score:
            response += f"📊 Match: {match_score:.1f}/10\n"
        response += "\n"

        if description:
            response += f"📝 Description:\n{description[:500]}\n\n"

        if skills:
            response += f"🔧 Compétences requises:\n"
            response += ", ".join(skills[:10]) + "\n\n"

        response += "Que veux-tu faire?\n"
        response += "• GO — Générer CV + lettre + mail\n"
        response += "• CV — Générer seulement le CV\n"
        response += "• LETTRE — Générer seulement la lettre"

        await update.message.reply_text(response, reply_markup=home_menu())

        # Store offer context in user context for next command
        if context.user_data is None:
            context.user_data = {}
        context.user_data["elevia_offer_context"] = offer_context.to_dict()
        context.user_data["elevia_offer_id"] = offer_id

    except Exception as e:
        logger.error("[ELEVIA] Error loading offer: %s", str(e), exc_info=True)
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

    gateway = EleviaGateway()
    offers = await gateway.search_offers(limit=limit + 1, source="all")

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

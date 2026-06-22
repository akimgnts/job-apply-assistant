import logging
import io
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from sqlalchemy.orm import Session
from app.database.db import SessionLocal
from app.config import config
from app.services.elevia_gateway import EleviaGateway
from app.services.elevia_client import EleviaClient
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


async def upload_profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Upload and parse user profile from CV/resume file."""
    user_id = str(update.effective_user.id)
    db = SessionLocal()

    try:
        # Check if a file was provided
        if not update.message.document:
            await update.message.reply_text(
                "📄 Envoie moi ton CV ou resume (PDF, DOCX, TXT, etc.)\n\n"
                "Usage: Télécharge un fichier ou utilise `/upload_profile` directement avec un document."
            )
            return

        # Download file
        file = await update.message.document.get_file()
        file_bytes = await file.download_as_bytearray()

        await update.message.reply_text("⏳ Parsing du profil en cours...")

        # Parse file with Elevia API
        client = EleviaClient()
        result = await client.parse_profile_file(
            file_content=bytes(file_bytes),
            filename=update.message.document.file_name or "profile.pdf",
        )

        if "error" in result:
            await update.message.reply_text(
                f"❌ Erreur lors du parsing:\n{result.get('error', 'Unknown error')}"
            )
            logger.error(
                "[UPLOAD_PROFILE] Parse failed for user %s: %s",
                user_id,
                result.get("error"),
            )
            return

        profile_id = result.get("profile_id")
        if not profile_id:
            await update.message.reply_text(
                "❌ Profil non créé: l'API n'a pas retourné de profile_id."
            )
            logger.error(
                "[UPLOAD_PROFILE] No profile_id in response for user %s",
                user_id,
            )
            return

        # Check if user already has a profile
        existing_profile_id = EleviaUserService.get_elevia_profile_id(db, user_id)

        # Store profile_id for user
        EleviaUserService.set_elevia_profile_id(db, user_id, profile_id)

        response = f"✅ Profil mis à jour:\n\n"
        response += f"Profile ID: `{profile_id}`\n"
        response += f"Nom: {result.get('name', 'N/A')}\n"
        response += f"Compétences: {len(result.get('skills', []))} détectées\n"
        response += f"Expériences: {len(result.get('experience', []))} détectées\n"

        if existing_profile_id and existing_profile_id != profile_id:
            response += f"\n(ancien profil: `{existing_profile_id}` remplacé)"

        response += "\n\nTu peux maintenant:"
        response += "\n• `/search_offers` - chercher des offres"
        response += "\n• `/catalog` - parcourir le catalogue"
        response += "\n• `/my_profile` - voir ton profil"

        await update.message.reply_text(response, parse_mode="Markdown")

        logger.info(
            "[UPLOAD_PROFILE] Profile created/updated for user %s: profile_id=%s, skills=%d",
            user_id,
            profile_id,
            len(result.get("skills", [])),
        )

    except Exception as e:
        logger.error(
            "[UPLOAD_PROFILE] Error: %s",
            str(e),
            exc_info=True,
        )
        await update.message.reply_text(
            f"❌ Erreur lors du chargement: {str(e)[:100]}"
        )
    finally:
        db.close()


async def my_profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show current user profile."""
    user_id = str(update.effective_user.id)
    db = SessionLocal()

    try:
        profile_id = EleviaUserService.get_elevia_profile_id(db, user_id)

        if not profile_id:
            await update.message.reply_text(
                "❌ Aucun profil Elevia actif.\n\n"
                "Utilise `/upload_profile` pour en créer un."
            )
            return

        # Try to fetch profile details from Elevia
        client = EleviaClient()
        profile_data = await client.get_profile(profile_id)

        if "error" in profile_data:
            response = f"⚠️ Profil trouvé mais détails indisponibles:\n\n"
            response += f"Profile ID: `{profile_id}`\n"
            response += f"(Erreur: {profile_data.get('error')})"
        else:
            response = f"✅ Profil Elevia actif:\n\n"
            response += f"Profile ID: `{profile_id}`\n"

            if profile_data.get("name"):
                response += f"Nom: {profile_data.get('name')}\n"

            skills = profile_data.get("skills", [])
            if skills:
                response += f"Compétences ({len(skills)}): {', '.join(skills[:5])}"
                if len(skills) > 5:
                    response += f", +{len(skills) - 5} autres"
                response += "\n"

            experience = profile_data.get("experience", [])
            if experience:
                response += f"Expériences ({len(experience)})\n"

        response += "\n\nCommandes:"
        response += "\n• `/upload_profile` - mettre à jour"
        response += "\n• `/clear_profile` - réinitialiser"

        await update.message.reply_text(response, parse_mode="Markdown")

        logger.info(
            "[MY_PROFILE] Profile queried for user %s: profile_id=%s",
            user_id,
            profile_id,
        )

    except Exception as e:
        logger.error(
            "[MY_PROFILE] Error: %s",
            str(e),
            exc_info=True,
        )
        await update.message.reply_text(
            f"❌ Erreur: {str(e)[:100]}"
        )
    finally:
        db.close()


async def clear_profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Clear user's Elevia profile."""
    user_id = str(update.effective_user.id)
    db = SessionLocal()

    try:
        profile_id = EleviaUserService.get_elevia_profile_id(db, user_id)

        if not profile_id:
            await update.message.reply_text(
                "ℹ️ Aucun profil Elevia à supprimer."
            )
            return

        # Clear profile
        EleviaUserService.clear_elevia_profile_id(db, user_id)

        await update.message.reply_text(
            f"✅ Profil supprimé.\n\n"
            f"Ancien profil: `{profile_id}`\n\n"
            f"Utilise `/upload_profile` pour en charger un nouveau.",
            parse_mode="Markdown"
        )

        logger.info(
            "[CLEAR_PROFILE] Profile cleared for user %s (was: %s)",
            user_id,
            profile_id,
        )

    except Exception as e:
        logger.error(
            "[CLEAR_PROFILE] Error: %s",
            str(e),
            exc_info=True,
        )
        await update.message.reply_text(
            f"❌ Erreur: {str(e)[:100]}"
        )
    finally:
        db.close()

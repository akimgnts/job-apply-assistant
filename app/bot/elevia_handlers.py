import logging
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from sqlalchemy.orm import Session
from app.database.db import SessionLocal
from app.config import config
from app.agents.elevia_agent import EleviaAgent
from app.agents.analysis_agent import AnalysisAgent
from app.agents.matching_agent import MatchingAgent
from app.agents.positioning_agent import PositioningAgent
from app.agents.generation_agent import GenerationAgent
from app.services.application_service import (
    create_application,
    save_analysis,
    update_application_with_analysis,
    update_user_session,
    get_last_application,
    mark_application_as_generated,
)
from app.services.offer_enrichment_service import OfferEnrichmentService
from app.database.models import GeneratedDocument, Application
from app.utils.debug import format_exception_for_telegram, split_telegram_message
from app.bot.keyboards import home_menu, offer_extracted_menu, save_or_regenerate_menu
from app.bot.message_formatter import format_analysis_message

logger = logging.getLogger(__name__)


async def elevia_health_check(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Check Elevia API health."""
    if not EleviaAgent.is_enabled():
        await update.message.reply_text(
            "❌ Elevia est désactivé.",
            reply_markup=home_menu()
        )
        return

    is_healthy = await EleviaAgent.health_check()
    if is_healthy:
        await update.message.reply_text(
            "✅ Elevia API est disponible!",
            reply_markup=home_menu()
        )
    else:
        await update.message.reply_text(
            "❌ Elevia API est indisponible.",
            reply_markup=home_menu()
        )


async def elevia_search_offers(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Search Elevia offers with natural language query."""
    if not EleviaAgent.is_enabled():
        await update.message.reply_text(
            "❌ Elevia est désactivé.",
            reply_markup=home_menu()
        )
        return

    user_query = " ".join(context.args) if context.args else None
    if not user_query:
        await update.message.reply_text(
            "📌 Usage: /search_offers <query>\n\n"
            "Exemples:\n"
            "• /search_offers data scientist Spain\n"
            "• /search_offers business analyst France",
            reply_markup=home_menu()
        )
        return

    await update.message.reply_text("🔍 Recherche des meilleures offres...")
    await update.message.chat.send_action("typing")

    try:
        offers = await EleviaAgent.search_offers(query=user_query, limit=10)
        if not offers:
            await update.message.reply_text(
                "Aucune offre trouvée.",
                reply_markup=home_menu()
            )
            return

        response = f"📋 Offres trouvées pour: *{user_query}*\n\n"
        for i, offer in enumerate(offers, 1):
            response += (
                f"{i}. *{offer.title}*\n"
                f"   Entreprise: {offer.company}\n"
                f"   Localisation: {offer.location}\n"
                f"   ID: `{offer.offer_id}`\n\n"
            )

        response += "Utilise `/load_elevia_offer <offer_id>` pour charger une offre."
        await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN, reply_markup=home_menu())

    except Exception as e:
        logger.error(f"Error searching Elevia offers: {e}", exc_info=True)
        await update.message.reply_text(
            f"❌ Erreur: {str(e)[:100]}",
            reply_markup=home_menu()
        )


async def elevia_catalog(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Browse Elevia offers catalog."""
    if not EleviaAgent.is_enabled():
        await update.message.reply_text(
            "❌ Elevia est désactivé.",
            reply_markup=home_menu()
        )
        return

    skip = 0
    if context.args and context.args[0].isdigit():
        skip = int(context.args[0])

    await update.message.reply_text("📚 Chargement du catalogue...")
    await update.message.chat.send_action("typing")

    try:
        offers = await EleviaAgent.get_catalog(skip=skip, limit=20)
        if not offers:
            await update.message.reply_text(
                "Aucune offre trouvée.",
                reply_markup=home_menu()
            )
            return

        response = f"📋 Catalogue Elevia (page {skip//20 + 1})\n\n"
        for i, offer in enumerate(offers, 1):
            response += (
                f"{i}. *{offer.title}*\n"
                f"   {offer.company} - {offer.location}\n"
                f"   ID: `{offer.offer_id}`\n\n"
            )

        response += "Utilise `/load_elevia_offer <offer_id>` pour charger une offre.\n"
        response += f"Utilise `/catalog {skip + 20}` pour la prochaine page."
        await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN, reply_markup=home_menu())

    except Exception as e:
        logger.error(f"Error loading Elevia catalog: {e}", exc_info=True)
        await update.message.reply_text(
            f"❌ Erreur: {str(e)[:100]}",
            reply_markup=home_menu()
        )


async def elevia_load_offer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Load and analyze a specific Elevia offer."""
    if not EleviaAgent.is_enabled():
        await update.message.reply_text("❌ Elevia est désactivé.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /load_elevia_offer <offer_id>")
        return

    offer_id = context.args[0]
    user_id = str(update.effective_user.id)
    db = SessionLocal()

    try:
        await update.message.reply_text("⏳ Chargement de l'offre Elevia...")
        await update.message.chat.send_action("typing")

        # Get offer context from Elevia
        elevia_context = await EleviaAgent.get_offer_with_context(
            offer_id=offer_id,
            db=db,
            telegram_user_id=user_id,
        )

        if not elevia_context or not elevia_context.offer_detail:
            await update.message.reply_text("❌ Impossible de charger l'offre.")
            return

        # Get job offer text
        offer_text = OfferEnrichmentService.get_offer_text_from_elevia_context(elevia_context)

        await update.message.reply_text("🔍 Analyse en cours...")

        # Create application record
        app = create_application(
            db,
            user_id,
            offer_text,
            source_url=elevia_context.offer_detail.raw_data.get("url", None),
        )

        # Analyze offer
        analysis = await AnalysisAgent.analyze(db, offer_text)

        # Enrich with matching
        analysis = MatchingAgent.enrich_analysis(analysis, db)

        # Enrich with Elevia context
        analysis = OfferEnrichmentService.enrich_analysis_with_elevia_context(
            analysis,
            elevia_context,
        )

        # Save analysis
        save_analysis(db, app.id, analysis)
        update_application_with_analysis(db, app.id, analysis)

        # Choose positioning
        positioning_result = await PositioningAgent.choose_angle(analysis)
        positioning = positioning_result.get("positioning", "")
        skill_profile = positioning_result.get("skill_profile", "general_business_data")

        if context.user_data is None:
            context.user_data = {}
        context.user_data["skill_profile"] = skill_profile
        context.user_data["elevia_context"] = elevia_context.to_dict()

        update_user_session(db, user_id, app.id, state="waiting_for_command")

        # Format response
        text, parse_mode = format_analysis_message(
            job_title=analysis.get("job_title", ""),
            company=analysis.get("company", ""),
            positioning=positioning,
            match_score=app.match_score or 0,
            strengths=analysis.get("strengths", []),
            weaknesses=analysis.get("missing_points", []),
        )

        text += "\n\n📌 *Source: Elevia*"

        await update.message.reply_text(
            text,
            parse_mode=parse_mode,
            reply_markup=offer_extracted_menu(app.id),
        )

    except Exception as e:
        logger.error(f"Error loading Elevia offer: {e}", exc_info=True)

        if config.DEBUG_TELEGRAM_ERRORS:
            error_msg = format_exception_for_telegram(
                e,
                {"user_id": user_id, "offer_id": offer_id},
            )
            chunks = split_telegram_message(error_msg)
            for chunk in chunks:
                await update.message.reply_text(chunk)
        else:
            await update.message.reply_text("❌ Erreur lors du chargement de l'offre.")

    finally:
        db.close()


async def elevia_upload_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Upload a profile file to Elevia."""
    if not EleviaAgent.is_enabled():
        await update.message.reply_text(
            "❌ Elevia est désactivé.",
            reply_markup=home_menu()
        )
        return

    user_id = str(update.effective_user.id)
    db = SessionLocal()

    try:
        # Check if called with command or if document is attached
        if not update.message.document:
            await update.message.reply_text(
                "📤 Envoie un fichier PDF ou Word avec ton profil pour l'analyser.\n\n"
                "Utilisation: envoie la commande puis attache le fichier, ou "
                "envoie simplement le fichier.",
                reply_markup=home_menu()
            )
            return

        await update.message.reply_text("⏳ Upload et analyse du profil...")
        await update.message.chat.send_action("typing")

        # Download file
        file_obj = await update.message.document.get_file()
        file_content = await file_obj.download_as_bytearray()

        # Upload to Elevia
        profile_id = await EleviaAgent.upload_profile_from_file(
            file_content=bytes(file_content),
            filename=update.message.document.file_name or "profile.pdf",
            db=db,
            telegram_user_id=user_id,
        )

        if profile_id:
            await update.message.reply_text(
                f"✅ Profil téléchargé et analysé!\n"
                f"ID: `{profile_id}`\n\n"
                f"Cet ID sera utilisé pour matcher tes offres automatiquement.",
                reply_markup=home_menu()
            )
        else:
            await update.message.reply_text(
                "❌ Impossible d'analyser le profil.",
                reply_markup=home_menu()
            )

    except Exception as e:
        logger.error(f"Error uploading Elevia profile: {e}", exc_info=True)
        await update.message.reply_text(
            f"❌ Erreur: {str(e)[:100]}",
            reply_markup=home_menu()
        )

    finally:
        db.close()


async def elevia_get_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Get current user's Elevia profile."""
    if not EleviaAgent.is_enabled():
        await update.message.reply_text(
            "❌ Elevia est désactivé.",
            reply_markup=home_menu()
        )
        return

    user_id = str(update.effective_user.id)
    db = SessionLocal()

    try:
        profile_data = await EleviaAgent.get_user_profile(db, user_id)

        if not profile_data:
            await update.message.reply_text(
                "❌ Aucun profil Elevia trouvé.\n\n"
                "Utilise /upload_profile pour envoyer ton profil.",
                reply_markup=home_menu()
            )
            return

        response = "👤 *Ton profil Elevia*\n\n"
        if profile_data.get("name"):
            response += f"Nom: {profile_data['name']}\n"
        if profile_data.get("email"):
            response += f"Email: {profile_data['email']}\n"
        if profile_data.get("location"):
            response += f"Localisation: {profile_data['location']}\n"

        skills = profile_data.get("skills", [])
        if skills:
            response += f"\n💼 Compétences ({len(skills)}):\n"
            for skill in skills[:5]:
                response += f"• {skill}\n"
            if len(skills) > 5:
                response += f"• ... et {len(skills) - 5} autres"

        await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN, reply_markup=home_menu())

    except Exception as e:
        logger.error(f"Error getting Elevia profile: {e}", exc_info=True)
        await update.message.reply_text(
            "❌ Erreur lors de la récupération du profil.",
            reply_markup=home_menu()
        )

    finally:
        db.close()

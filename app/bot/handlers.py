import logging
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from sqlalchemy.orm import Session
from app.database.db import SessionLocal
from app.config import config
from app.agents.input_agent import InputAgent
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
from app.services.document_service import get_template_debug_info
from app.database.models import GeneratedDocument, DocumentTypeEnum
from app.utils.debug import format_exception_for_telegram, split_telegram_message
from app.utils.filename import safe_document_filename
from app.bot.keyboards import (
    home_menu, back_home, offer_extracted_menu, match_view_menu,
    application_detail_menu, save_or_regenerate_menu, profile_menu, master_cv_menu
)
from app.bot.message_formatter import (
    format_analysis_message,
    format_match_detail_message,
    format_applications_list_message,
    format_profile_message,
    format_document_generated_message,
)

logger = logging.getLogger(__name__)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    await update.message.reply_text(
        "👋 Bienvenue dans Job Apply Assistant!\n\n"
        "Analyse tes offres, vérifie ton match et génère CV, lettre et mail en quelques secondes.",
        reply_markup=home_menu()
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command."""
    await update.message.reply_text(
        "📋 Mode d'emploi:\n\n"
        "1️⃣ Envoie une offre (URL ou texte)\n"
        "2️⃣ Je vais l'analyser et te proposer un angle\n"
        "3️⃣ Réponds avec l'une de ces commandes:\n"
        "   GO — Générer CV + lettre + mail\n"
        "   CV — Générer seulement le CV\n"
        "   LETTRE — Générer seulement la lettre\n"
        "   MAIL — Générer seulement le mail\n\n"
        "Tips:\n"
        "• Teste d'abord avec une URL\n"
        "• Si ça ne marche pas, colle le texte\n"
        "• Les documents sont sauvegardés"
    )

async def last_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /last command."""
    db = SessionLocal()
    try:
        user_id = str(update.effective_user.id)
        app = get_last_application(db, user_id)
        if app:
            await update.message.reply_text(
                f"📌 Dernière offre:\n"
                f"Entreprise: {app.company}\n"
                f"Poste: {app.job_title}\n"
                f"Angle: {app.recommended_angle}\n"
                f"Score: {app.match_score}/10"
            )
        else:
            await update.message.reply_text("Aucune offre analysée pour le moment.")
    finally:
        db.close()

async def handle_offer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle job offer input (URL or text)."""
    user_id = str(update.effective_user.id)
    raw_input = update.message.text
    db = SessionLocal()

    try:
        # Check if input is URL
        from app.services.job_ingestion_service import is_url
        if is_url(raw_input):
            await update.message.reply_text("🔎 Lien reçu. Extraction en cours...")

        await update.message.chat.send_action("typing")

        # Use async InputAgent
        offer_text, metadata = await InputAgent.process(raw_input)

        # Handle extraction failure
        if offer_text is None:
            error_detail = metadata.get("error_detail", "")
            if config.DEBUG_TELEGRAM_ERRORS and error_detail:
                await update.message.reply_text(
                    f"❌ Impossible de lire automatiquement cette offre.\n\n"
                    f"Erreur: {error_detail[:200]}\n\n"
                    f"Envoie le texte complet de l'offre."
                )
            else:
                await update.message.reply_text(
                    "❌ Impossible de lire automatiquement cette offre.\n\n"
                    "Colle-moi le texte complet de l'offre ici."
                )
            return

        # Success message for URL extraction
        if metadata.get("source_type") == "url":
            await update.message.reply_text("✅ Offre extraite avec succès.\nAnalyse en cours...")
        else:
            await update.message.reply_text("🔍 Analyse en cours...")

        app = create_application(db, user_id, offer_text, metadata.get("source_url"))

        analysis = await AnalysisAgent.analyze(db, offer_text)

        analysis = MatchingAgent.enrich_analysis(analysis, db)

        save_analysis(db, app.id, analysis)

        update_application_with_analysis(db, app.id, analysis)

        positioning_result = await PositioningAgent.choose_angle(analysis)
        positioning = positioning_result.get("positioning", "Data Analyst BI")
        skill_profile = positioning_result.get("skill_profile", "general_business_data")

        # Store skill_profile in context for document generation
        if context.user_data is None:
            context.user_data = {}
        context.user_data["skill_profile"] = skill_profile

        update_user_session(db, user_id, app.id, state="waiting_for_command")

        # Format message as professional HTML
        text, parse_mode = format_analysis_message(
            job_title=analysis.get("job_title", ""),
            company=analysis.get("company", ""),
            positioning=positioning,
            match_score=app.match_score or 0,
            strengths=analysis.get("strengths", []),
            weaknesses=analysis.get("missing_points", [])
        )

        await update.message.reply_text(
            text,
            parse_mode=parse_mode,
            reply_markup=offer_extracted_menu(app.id)
        )

    except Exception as e:
        logger.error(f"Error processing offer: {e}", exc_info=True)

        if config.DEBUG_TELEGRAM_ERRORS:
            context_dict = {
                "user_id": user_id,
                "command": "handle_offer",
                "raw_input_len": len(raw_input),
            }

            extra_debug = None
            if "TemplateNotFound" in type(e).__name__ or "template" in str(e).lower():
                extra_debug = get_template_debug_info()

            error_msg = format_exception_for_telegram(e, context_dict, extra_debug)
            chunks = split_telegram_message(error_msg)
            for chunk in chunks:
                await update.message.reply_text(chunk)
        else:
            await update.message.reply_text(
                f"❌ Erreur lors de l'analyse: {str(e)}\n\n"
                "Réessaye avec une autre offre."
            )
    finally:
        db.close()

async def handle_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle GO/CV/LETTRE/MAIL commands (both URL and Elevia modes)."""
    user_id = str(update.effective_user.id)
    command = update.message.text.upper().strip()
    db = SessionLocal()

    try:
        # Parse document types
        doc_types = {
            "GO": ["cv", "letter", "mail"],
            "CV": ["cv"],
            "LETTRE": ["letter"],
            "MAIL": ["mail"],
        }.get(command, [])

        if not doc_types:
            await update.message.reply_text("Commande non reconnue. Utilise GO, CV, LETTRE ou MAIL.")
            return

        await update.message.chat.send_action("typing")

        # DETECT ELEVIA MODE
        elevia_offer_context = context.user_data.get("elevia_offer_context") if context.user_data else None
        elevia_positioning = context.user_data.get("elevia_positioning") if context.user_data else None

        if elevia_offer_context:
            logger.info("[HANDLE_COMMAND] Entering Elevia mode for user %s", user_id)
            await _handle_command_elevia(
                update,
                context,
                db,
                elevia_offer_context,
                elevia_positioning,
                doc_types,
                user_id,
            )
        else:
            logger.info("[HANDLE_COMMAND] Using standard URL/text mode for user %s", user_id)
            await _handle_command_standard(
                update,
                context,
                db,
                doc_types,
                user_id,
            )

    except Exception as e:
        logger.error(f"Error in handle_command: {e}", exc_info=True)

        if config.DEBUG_TELEGRAM_ERRORS:
            context_dict = {
                "user_id": user_id,
                "command": command,
            }

            extra_debug = None
            if "TemplateNotFound" in type(e).__name__ or "template" in str(e).lower():
                extra_debug = get_template_debug_info()

            error_msg = format_exception_for_telegram(e, context_dict, extra_debug)
            chunks = split_telegram_message(error_msg)
            for chunk in chunks:
                await update.message.reply_text(chunk)
        else:
            await update.message.reply_text(f"❌ Erreur: {str(e)}")
    finally:
        db.close()


async def _handle_command_standard(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    db: Session,
    doc_types: list,
    user_id: str,
) -> None:
    """Handle command in standard URL/text mode."""
    app = get_last_application(db, user_id)
    if not app:
        await update.message.reply_text("Aucune offre en cours. Envoie une offre d'abord.")
        return

    analysis = app.analyses[0].analysis_json if app.analyses else None
    if not analysis:
        await update.message.reply_text("Analyse non trouvée.")
        return

    positioning = analysis.get("recommended_angle", "Data Analyst BI")
    skill_profile = context.user_data.get("skill_profile", "general_business_data") if context.user_data else "general_business_data"

    logger.info("[HANDLE_STANDARD] Generating %s for app %s", doc_types, app.id)

    documents = await GenerationAgent.generate_documents(
        db, app.id, analysis, positioning, doc_types, skill_profile, user_id
    )

    mark_application_as_generated(db, app.id)

    response = "✅ Documents générés:\n\n"
    for doc_type, content in documents.items():
        response += f"📄 {doc_type.upper()}\n"

    await update.message.reply_text(response)

    for doc_type in doc_types:
        doc = db.query(GeneratedDocument).filter(
            GeneratedDocument.application_id == app.id,
            GeneratedDocument.document_type == DocumentTypeEnum(doc_type),
        ).first()
        if doc:
            await update.message.reply_document(
                document=doc.content.encode(),
                filename=doc.filename,
            )


async def _handle_command_elevia(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    db: Session,
    elevia_offer_context: dict,
    elevia_positioning: str,
    doc_types: list,
    user_id: str,
) -> None:
    """Handle command in Elevia mode."""
    from app.services.elevia_gateway import EleviaOfferContext
    from app.services.elevia_analysis_builder import EleviaAnalysisBuilder
    from app.services.offer_enrichment_service import OfferEnrichmentService

    logger.info(
        "[HANDLE_ELEVIA] Generating %s from Elevia context for user %s",
        doc_types,
        user_id,
    )

    # Reconstruct EleviaOfferContext from dict
    offer_context = EleviaOfferContext(
        source_offer_id=elevia_offer_context.get("source_offer_id"),
        source_type=elevia_offer_context.get("source_type", "business_france"),
        offer_catalog_entry=elevia_offer_context.get("offer_catalog_entry"),
        offer_detail=elevia_offer_context.get("offer_detail"),
        profile=elevia_offer_context.get("profile"),
        matching_context=elevia_offer_context.get("matching_context"),
    )

    # Build analysis from Elevia context
    analysis = EleviaAnalysisBuilder.build_analysis_from_offer_context(offer_context)

    # Enrich with Elevia context
    analysis = OfferEnrichmentService.enrich_analysis_with_elevia_context(
        analysis,
        offer_context,
    )

    logger.info(
        "[HANDLE_ELEVIA] Analysis built: %s @ %s, match=%.1f",
        analysis.get("job_title"),
        analysis.get("company"),
        analysis.get("match_score") or 0,
    )

    # Use Elevia positioning or extracted title
    positioning = elevia_positioning or analysis.get("job_title", "Unknown Position")
    skill_profile = context.user_data.get("skill_profile", "general_business_data") if context.user_data else "general_business_data"

    # Generate documents (ephemeral, no Application record)
    documents = await GenerationAgent.generate_documents(
        db,
        application_id=0,  # Ephemeral
        analysis=analysis,
        positioning=positioning,
        document_types=doc_types,
        skill_profile=skill_profile,
        telegram_user_id=user_id,
    )

    response = "✅ Documents générés (Elevia):\n\n"
    for doc_type, content in documents.items():
        response += f"📄 {doc_type.upper()}\n"

    await update.message.reply_text(response)

    # Send generated documents
    # Note: When application_id=0, documents aren't saved to DB
    # We need to send content directly or modify GenerationAgent to return content
    # For now, try to retrieve from temp storage
    logger.warning(
        "[HANDLE_ELEVIA] Note: Documents generated but not persisted (application_id=0)"
    )

def format_analysis_summary(analysis: dict, positioning: str) -> str:
    """Format analysis results for Telegram message."""
    strengths = "\n".join([f"• {s}" for s in analysis.get("strengths", [])[:3]])
    missing = "\n".join([f"• {m}" for m in analysis.get("missing_points", [])[:2]])

    return (
        f"🎯 Offre détectée: {analysis.get('job_title')} — {analysis.get('company')}\n\n"
        f"💡 Angle recommandé:\n{positioning}\n\n"
        f"📊 Match:\n{analysis.get('match_score')}/10\n\n"
        f"✅ Points forts:\n{strengths}\n\n"
        f"⚠️ Points manquants:\n{missing}\n\n"
        f"📝 Stratégie CV:\n{analysis.get('cv_strategy', 'Non disponible')}"
    )


async def home_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle home button."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🏠 Accueil\n\nQue veux-tu faire?",
        reply_markup=home_menu()
    )


async def analyze_offer_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle analyze offer button."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "📋 Envoie-moi:\n"
        "• Une URL d'offre\n"
        "• Le texte de l'offre\n"
        "• Une capture d'écran",
        reply_markup=back_home()
    )


async def my_applications_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle my applications button."""
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    db = SessionLocal()

    try:
        # Get last 5 applications
        from sqlalchemy import desc
        from app.database.models import Application

        apps = db.query(Application).filter_by(telegram_user_id=user_id).order_by(desc(Application.created_at)).limit(5).all()

        if not apps:
            text = "<b>Aucune candidature sauvegardée</b>"
            await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=back_home())
            return

        # Format using message formatter
        text, parse_mode = format_applications_list_message(apps)
        await query.edit_message_text(text, parse_mode=parse_mode, reply_markup=back_home())
    finally:
        db.close()


async def view_master_cv_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle view master CV button."""
    query = update.callback_query
    await query.answer()

    from app.services.master_cv_service import load_master_cv

    master_cv = load_master_cv()

    # Format CV info
    exp_text = "\n".join([f"• {e['title']} @ {e['company']}" for e in master_cv["experiences"]])
    proj_text = "\n".join([f"• {p['title']}" for p in master_cv["projects"][:3]])

    text = f"""📄 Master CV

**Expériences:**
{exp_text}

**Projets:**
{proj_text}

**Compétences:**
{len(master_cv['skills'])} domaines
"""

    await query.edit_message_text(text, reply_markup=master_cv_menu())


async def view_profile_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle view profile button."""
    query = update.callback_query
    await query.answer()

    text = f"""⚙️ Mon profil

**Nom:** {config.CANDIDATE_NAME or 'Non défini'}
**Location:** {config.CANDIDATE_LINKEDIN or 'Non défini'} (Paris)
**Email:** {config.CANDIDATE_EMAIL or 'Non défini'}
**Téléphone:** {config.CANDIDATE_PHONE or 'Non défini'}
**LinkedIn:** {config.CANDIDATE_LINKEDIN or 'Non défini'}
**GitHub:** {config.CANDIDATE_GITHUB or 'Non défini'}
"""

    await query.edit_message_text(text, reply_markup=profile_menu())


async def view_match_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle view match button."""
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    db = SessionLocal()

    try:
        app = get_last_application(db, user_id)
        if not app or not app.analyses:
            await query.answer("Aucune analyse disponible", show_alert=True)
            return

        analysis = app.analyses[0].analysis_json
        match_score = app.match_score

        text = f"""📊 Match détaillé

**Entreprise:** {app.company}
**Poste:** {app.job_title}
**Score:** {match_score}/10

**Positionnement:** {app.recommended_angle}

**Points forts:**
{chr(10).join([f"• {s}" for s in analysis.get("strengths", [])[:3]])}

**Points manquants:**
{chr(10).join([f"• {m}" for m in analysis.get("missing_points", [])[:3]])}
"""

        await query.edit_message_text(text, reply_markup=match_view_menu())
    finally:
        db.close()


async def gen_cv_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle generate CV button with step-by-step progress."""
    query = update.callback_query
    await query.answer()

    user_id = str(query.from_user.id)

    # Parse app_id from callback_data (format: gen_cv:123)
    callback_parts = query.data.split(":")
    app_id = int(callback_parts[1]) if len(callback_parts) > 1 else None

    db = SessionLocal()
    progress_msg = None

    try:
        # Send initial progress message
        progress_msg = await query.message.reply_text("CV : demande reçue.")
        if config.DEBUG_TELEGRAM_STEPS:
            logger.info("[CV] Request received, app_id=%s, user_id=%s", app_id, user_id)

        if app_id:
            from app.database.models import Application
            app = db.query(Application).filter_by(id=app_id).first()
        else:
            app = get_last_application(db, user_id)

        if not app:
            await query.message.reply_text("❌ CV : Aucune offre en cours.")
            if config.DEBUG_TELEGRAM_STEPS:
                logger.warning("[CV] No application found for user_id=%s", user_id)
            return

        if config.DEBUG_TELEGRAM_STEPS:
            await progress_msg.edit_text("CV : récupération de l'analyse...")
            logger.info("[CV] Loading analysis for app_id=%s", app.id)

        analysis = app.analyses[0].analysis_json if app.analyses else None
        positioning = app.recommended_angle
        skill_profile = context.user_data.get("skill_profile", "general_business_data") if context.user_data else "general_business_data"

        if not analysis:
            await query.message.reply_text("❌ CV : Analyse non trouvée.")
            if config.DEBUG_TELEGRAM_STEPS:
                logger.warning("[CV] No analysis found for app_id=%s", app.id)
            return

        if config.DEBUG_TELEGRAM_STEPS:
            await progress_msg.edit_text("CV : génération du contenu...")
            logger.info("[CV] Starting CV generation for app_id=%s, positioning=%s, skill_profile=%s", app.id, positioning, skill_profile)

        # Generate CV
        await GenerationAgent.generate_cv(db, app.id, analysis, positioning, skill_profile, user_id)
        mark_application_as_generated(db, app.id)

        if config.DEBUG_TELEGRAM_STEPS:
            await progress_msg.edit_text("CV : rendu HTML...")
            logger.info("[CV] CV generation complete, retrieving document")

        # Get document
        doc = db.query(GeneratedDocument).filter(
            GeneratedDocument.application_id == app.id,
            GeneratedDocument.document_type == DocumentTypeEnum.cv
        ).first()

        if not doc:
            await query.message.reply_text("❌ CV : Document non créé.")
            if config.DEBUG_TELEGRAM_STEPS:
                logger.error("[CV] Document not found after generation for app_id=%s", app.id)
            return

        # Validate file
        if not doc.content or len(doc.content.strip()) == 0:
            await query.message.reply_text("❌ CV : Contenu vide.")
            if config.DEBUG_TELEGRAM_STEPS:
                logger.error("[CV] Document content is empty for app_id=%s", app.id)
            return

        # Generate safe filename
        safe_filename = safe_document_filename(
            candidate_name=config.CANDIDATE_NAME or "Akim_Guentas",
            job_title=app.job_title or "Position",
            company=app.company or "Company",
            document_type="CV",
            extension="pdf"
        )

        # Update document record with metadata
        doc.filename = safe_filename
        doc.positioning = positioning
        doc.skill_profile = skill_profile
        doc.telegram_user_id = user_id
        db.commit()

        if config.DEBUG_TELEGRAM_STEPS:
            logger.info("[CV] Document metadata updated: filename=%s, size=%d bytes", safe_filename, len(doc.content))

        if config.DEBUG_TELEGRAM_STEPS:
            await progress_msg.edit_text("CV : envoi du fichier...")

        # Format success message (HTML-first strategy)
        text = "<b>✅ CV généré</b>\n\nOuvriras le fichier dans ton navigateur et imprime en PDF si besoin."

        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=save_or_regenerate_menu())

        # Send HTML file (not PDF)
        html_filename = safe_filename.replace(".pdf", ".html")

        if config.DEBUG_TELEGRAM_STEPS:
            logger.info("[CV] Sending file: %s", html_filename)

        await query.message.reply_document(
            document=doc.content.encode(),
            filename=html_filename
        )

        if config.DEBUG_TELEGRAM_STEPS:
            await progress_msg.delete()
            logger.info("[CV] CV generation complete and sent for app_id=%s", app.id)

    except Exception as e:
        logger.error("[CV] Error: %s", str(e), exc_info=True)
        error_msg = f"❌ CV : Erreur lors de la génération."
        if config.DEBUG_TELEGRAM_ERRORS:
            error_msg += f"\n\n{str(e)[:200]}"
        await query.message.reply_text(error_msg)
        if progress_msg:
            try:
                await progress_msg.delete()
            except:
                pass
    finally:
        db.close()


async def save_application_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle save application button."""
    query = update.callback_query
    await query.answer()

    user_id = str(query.from_user.id)

    # Parse app_id from callback_data
    callback_parts = query.data.split(":")
    app_id = int(callback_parts[1]) if len(callback_parts) > 1 else None

    db = SessionLocal()

    try:
        if app_id:
            from app.database.models import Application
            app = db.query(Application).filter_by(id=app_id).first()
        else:
            app = get_last_application(db, user_id)

        if app:
            from app.database.models import Application
            app.status = "saved"
            db.commit()
            await query.edit_message_text(
                "✅ Candidature sauvegardée!",
                reply_markup=home_menu()
            )
    finally:
        db.close()


async def view_match_with_app_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle view match button (with app_id)."""
    query = update.callback_query
    await query.answer()

    # Parse app_id
    callback_parts = query.data.split(":")
    app_id = int(callback_parts[1]) if len(callback_parts) > 1 else None

    db = SessionLocal()

    try:
        if app_id:
            from app.database.models import Application
            app = db.query(Application).filter_by(id=app_id).first()
        else:
            user_id = str(query.from_user.id)
            app = get_last_application(db, user_id)

        if not app or not app.analyses:
            await query.answer("Aucune analyse disponible", show_alert=True)
            return

        analysis = app.analyses[0].analysis_json

        # Format as professional HTML
        text, parse_mode = format_match_detail_message(
            company=app.company or "",
            job_title=app.job_title or "",
            positioning=app.recommended_angle or "",
            match_score=app.match_score or 0,
            strengths=analysis.get("strengths", []),
            weaknesses=analysis.get("missing_points", []),
            missing_skills=analysis.get("required_skills", [])
        )

        await query.edit_message_text(text, parse_mode=parse_mode, reply_markup=match_view_menu())
    finally:
        db.close()


async def gen_letter_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle generate letter button with step-by-step progress."""
    query = update.callback_query
    await query.answer()

    callback_parts = query.data.split(":")
    app_id = int(callback_parts[1]) if len(callback_parts) > 1 else None
    user_id = str(query.from_user.id)

    db = SessionLocal()
    progress_msg = None

    try:
        # Send initial progress message
        progress_msg = await query.message.reply_text("Lettre : demande reçue.")
        if config.DEBUG_TELEGRAM_STEPS:
            logger.info("[LETTER] Request received, app_id=%s, user_id=%s", app_id, user_id)

        if app_id:
            from app.database.models import Application
            app = db.query(Application).filter_by(id=app_id).first()
        else:
            app = get_last_application(db, user_id)

        if not app:
            await query.message.reply_text("❌ Lettre : Aucune offre en cours.")
            if config.DEBUG_TELEGRAM_STEPS:
                logger.warning("[LETTER] No application found for user_id=%s", user_id)
            return

        if config.DEBUG_TELEGRAM_STEPS:
            await progress_msg.edit_text("Lettre : récupération de l'analyse...")
            logger.info("[LETTER] Loading analysis for app_id=%s", app.id)

        analysis = app.analyses[0].analysis_json if app.analyses else None
        positioning = app.recommended_angle

        if not analysis:
            await query.message.reply_text("❌ Lettre : Analyse non trouvée.")
            if config.DEBUG_TELEGRAM_STEPS:
                logger.warning("[LETTER] No analysis found for app_id=%s", app.id)
            return

        if config.DEBUG_TELEGRAM_STEPS:
            await progress_msg.edit_text("Lettre : génération du contenu...")
            logger.info("[LETTER] Starting letter generation for app_id=%s, positioning=%s", app.id, positioning)

        # Generate letter (FIX: was calling generate_cv instead of generate_letter)
        logger.info("[LETTER] Calling generate_letter for app_id=%s", app.id)
        await GenerationAgent.generate_letter(db, app.id, analysis, positioning, user_id)
        logger.info("[LETTER] generate_letter completed")
        mark_application_as_generated(db, app.id)

        if config.DEBUG_TELEGRAM_STEPS:
            await progress_msg.edit_text("Lettre : rendu HTML...")
            logger.info("[LETTER] Letter generation complete, retrieving document")

        logger.info("[LETTER] Querying GeneratedDocument for app_id=%s with type=letter", app.id)
        doc = db.query(GeneratedDocument).filter(
            GeneratedDocument.application_id == app.id,
            GeneratedDocument.document_type == DocumentTypeEnum.letter
        ).first()
        logger.info("[LETTER] Query result: doc=%s", doc)

        if not doc:
            logger.error("[LETTER] Document not found for app_id=%s, checking all docs", app.id)
            all_docs = db.query(GeneratedDocument).filter(
                GeneratedDocument.application_id == app.id
            ).all()
            logger.error("[LETTER] All docs for app_id=%s: %s", app.id, [(d.id, d.document_type, d.filename) for d in all_docs])
            await query.message.reply_text("❌ Lettre : Document non créé.")
            return

        # Validate file
        if not doc.content or len(doc.content.strip()) == 0:
            await query.message.reply_text("❌ Lettre : Contenu vide.")
            if config.DEBUG_TELEGRAM_STEPS:
                logger.error("[LETTER] Document content is empty for app_id=%s", app.id)
            return

        if config.DEBUG_TELEGRAM_STEPS:
            logger.info("[LETTER] Document retrieved: filename=%s, size=%d bytes", doc.filename, len(doc.content))

        if config.DEBUG_TELEGRAM_STEPS:
            await progress_msg.edit_text("Lettre : envoi du fichier...")

        await query.edit_message_text("✅ Lettre générée!", reply_markup=save_or_regenerate_menu())

        if config.DEBUG_TELEGRAM_STEPS:
            logger.info("[LETTER] Sending file: %s", doc.filename)

        await query.message.reply_document(
            document=doc.content.encode(),
            filename=doc.filename
        )

        if config.DEBUG_TELEGRAM_STEPS:
            await progress_msg.delete()
            logger.info("[LETTER] Letter generation complete and sent for app_id=%s", app.id)

    except Exception as e:
        logger.error("[LETTER] Error: %s", str(e), exc_info=True)
        error_msg = f"❌ Lettre : Erreur lors de la génération."
        if config.DEBUG_TELEGRAM_ERRORS:
            error_msg += f"\n\n{str(e)[:200]}"
        await query.message.reply_text(error_msg)
        if progress_msg:
            try:
                await progress_msg.delete()
            except:
                pass
    finally:
        db.close()


async def gen_mail_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle generate mail button with step-by-step progress."""
    query = update.callback_query
    await query.answer()

    callback_parts = query.data.split(":")
    app_id = int(callback_parts[1]) if len(callback_parts) > 1 else None
    user_id = str(query.from_user.id)

    db = SessionLocal()
    progress_msg = None

    try:
        # Send initial progress message
        progress_msg = await query.message.reply_text("Mail : demande reçue.")
        if config.DEBUG_TELEGRAM_STEPS:
            logger.info("[MAIL] Request received, app_id=%s, user_id=%s", app_id, user_id)

        if app_id:
            from app.database.models import Application
            app = db.query(Application).filter_by(id=app_id).first()
        else:
            app = get_last_application(db, user_id)

        if not app:
            await query.message.reply_text("❌ Mail : Aucune offre en cours.")
            if config.DEBUG_TELEGRAM_STEPS:
                logger.warning("[MAIL] No application found for user_id=%s", user_id)
            return

        if config.DEBUG_TELEGRAM_STEPS:
            await progress_msg.edit_text("Mail : récupération de l'analyse...")
            logger.info("[MAIL] Loading analysis for app_id=%s", app.id)

        analysis = app.analyses[0].analysis_json if app.analyses else None
        positioning = app.recommended_angle

        if not analysis:
            await query.message.reply_text("❌ Mail : Analyse non trouvée.")
            if config.DEBUG_TELEGRAM_STEPS:
                logger.warning("[MAIL] No analysis found for app_id=%s", app.id)
            return

        if config.DEBUG_TELEGRAM_STEPS:
            await progress_msg.edit_text("Mail : génération du contenu...")
            logger.info("[MAIL] Starting mail generation for app_id=%s, positioning=%s", app.id, positioning)

        # Generate mail (FIX: was calling generate_cv instead of generate_mail)
        await GenerationAgent.generate_mail(db, app.id, analysis, positioning, user_id)
        mark_application_as_generated(db, app.id)

        if config.DEBUG_TELEGRAM_STEPS:
            await progress_msg.edit_text("Mail : préparation du fichier...")
            logger.info("[MAIL] Mail generation complete, retrieving document")

        doc = db.query(GeneratedDocument).filter(
            GeneratedDocument.application_id == app.id,
            GeneratedDocument.document_type == DocumentTypeEnum.mail
        ).first()

        if not doc:
            await query.message.reply_text("❌ Mail : Document non créé.")
            if config.DEBUG_TELEGRAM_STEPS:
                logger.error("[MAIL] Document not found after generation for app_id=%s", app.id)
            return

        # Validate file
        if not doc.content or len(doc.content.strip()) == 0:
            await query.message.reply_text("❌ Mail : Contenu vide.")
            if config.DEBUG_TELEGRAM_STEPS:
                logger.error("[MAIL] Document content is empty for app_id=%s", app.id)
            return

        if config.DEBUG_TELEGRAM_STEPS:
            logger.info("[MAIL] Document retrieved: filename=%s, size=%d bytes", doc.filename, len(doc.content))

        if config.DEBUG_TELEGRAM_STEPS:
            await progress_msg.edit_text("Mail : envoi du fichier...")

        await query.edit_message_text("✅ Mail généré!", reply_markup=save_or_regenerate_menu())

        if config.DEBUG_TELEGRAM_STEPS:
            logger.info("[MAIL] Sending file: %s", doc.filename)

        await query.message.reply_document(
            document=doc.content.encode(),
            filename=doc.filename
        )

        if config.DEBUG_TELEGRAM_STEPS:
            await progress_msg.delete()
            logger.info("[MAIL] Mail generation complete and sent for app_id=%s", app.id)

    except Exception as e:
        logger.error("[MAIL] Error: %s", str(e), exc_info=True)
        error_msg = f"❌ Mail : Erreur lors de la génération."
        if config.DEBUG_TELEGRAM_ERRORS:
            error_msg += f"\n\n{str(e)[:200]}"
        await query.message.reply_text(error_msg)
        if progress_msg:
            try:
                await progress_msg.delete()
            except:
                pass
    finally:
        db.close()


async def gen_all_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle generate all documents button with step-by-step progress."""
    query = update.callback_query
    await query.answer()

    callback_parts = query.data.split(":")
    app_id = int(callback_parts[1]) if len(callback_parts) > 1 else None
    user_id = str(query.from_user.id)

    db = SessionLocal()
    progress_msg = None

    try:
        # Send initial progress message
        progress_msg = await query.message.reply_text("Documents : demande reçue.")
        if config.DEBUG_TELEGRAM_STEPS:
            logger.info("[ALL] Request received, app_id=%s, user_id=%s", app_id, user_id)

        if app_id:
            from app.database.models import Application
            app = db.query(Application).filter_by(id=app_id).first()
        else:
            app = get_last_application(db, user_id)

        if not app:
            await query.message.reply_text("❌ Documents : Aucune offre en cours.")
            if config.DEBUG_TELEGRAM_STEPS:
                logger.warning("[ALL] No application found for user_id=%s", user_id)
            return

        if config.DEBUG_TELEGRAM_STEPS:
            await progress_msg.edit_text("Documents : récupération de l'analyse...")
            logger.info("[ALL] Loading analysis for app_id=%s", app.id)

        analysis = app.analyses[0].analysis_json if app.analyses else None
        positioning = app.recommended_angle
        skill_profile = context.user_data.get("skill_profile", "general_business_data") if context.user_data else "general_business_data"

        if not analysis:
            await query.message.reply_text("❌ Documents : Analyse non trouvée.")
            if config.DEBUG_TELEGRAM_STEPS:
                logger.warning("[ALL] No analysis found for app_id=%s", app.id)
            return

        if config.DEBUG_TELEGRAM_STEPS:
            await progress_msg.edit_text("Documents : génération du CV...")
            logger.info("[ALL] Starting documents generation for app_id=%s", app.id)

        # Generate all documents
        await GenerationAgent.generate_documents(
            db, app.id, analysis, positioning, ["cv", "letter", "mail"], skill_profile, user_id
        )
        mark_application_as_generated(db, app.id)

        if config.DEBUG_TELEGRAM_STEPS:
            await progress_msg.edit_text("Documents : envoi des fichiers...")
            logger.info("[ALL] All documents generated, retrieving for send")

        await query.edit_message_text("✅ Documents générés!", reply_markup=save_or_regenerate_menu())

        # Send all documents
        docs = db.query(GeneratedDocument).filter(
            GeneratedDocument.application_id == app.id,
            GeneratedDocument.document_type.in_([DocumentTypeEnum.cv, DocumentTypeEnum.letter, DocumentTypeEnum.mail])
        ).all()

        if not docs:
            await query.message.reply_text("❌ Documents : Aucun document créé.")
            if config.DEBUG_TELEGRAM_STEPS:
                logger.error("[ALL] No documents found after generation for app_id=%s", app.id)
            return

        sent_count = 0
        for doc in docs:
            # Validate file before sending
            if not doc.content or len(doc.content.strip()) == 0:
                if config.DEBUG_TELEGRAM_STEPS:
                    logger.warning("[ALL] Skipping empty document: %s", doc.document_type)
                continue

            if config.DEBUG_TELEGRAM_STEPS:
                logger.info("[ALL] Sending %s: %s (%d bytes)", doc.document_type, doc.filename, len(doc.content))

            await query.message.reply_document(
                document=doc.content.encode(),
                filename=doc.filename
            )
            sent_count += 1

        if config.DEBUG_TELEGRAM_STEPS:
            await progress_msg.delete()
            logger.info("[ALL] All documents sent for app_id=%s (count=%d)", app.id, sent_count)

    except Exception as e:
        logger.error("[ALL] Error: %s", str(e), exc_info=True)
        error_msg = f"❌ Documents : Erreur lors de la génération."
        if config.DEBUG_TELEGRAM_ERRORS:
            error_msg += f"\n\n{str(e)[:200]}"
        await query.message.reply_text(error_msg)
        if progress_msg:
            try:
                await progress_msg.delete()
            except:
                pass
    finally:
        db.close()


async def regenerate_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle regenerate button (alias for gen_all)."""
    # Just forward to gen_all_callback
    update.callback_query.data = update.callback_query.data.replace("regenerate:", "gen_all:")
    await gen_all_callback(update, context)

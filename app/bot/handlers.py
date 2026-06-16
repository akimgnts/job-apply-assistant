import logging
from telegram import Update
from telegram.ext import ContextTypes
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
from app.database.models import GeneratedDocument
from app.utils.debug import format_exception_for_telegram, split_telegram_message
from app.bot.keyboards import (
    home_menu, back_home, offer_extracted_menu, match_view_menu,
    application_detail_menu, save_or_regenerate_menu, profile_menu, master_cv_menu
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

        summary = format_analysis_summary(analysis, positioning)
        await update.message.reply_text(
            summary,
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
    """Handle GO/CV/LETTRE/MAIL commands."""
    user_id = str(update.effective_user.id)
    command = update.message.text.upper().strip()
    db = SessionLocal()

    try:
        app = get_last_application(db, user_id)
        if not app:
            await update.message.reply_text("Aucune offre en cours. Envoie une offre d'abord.")
            return

        analysis = app.analyses[0].analysis_json if app.analyses else None
        if not analysis:
            await update.message.reply_text("Analyse non trouvée.")
            return

        positioning = analysis.get("recommended_angle", "Data Analyst BI")
        # Retrieve skill_profile from context
        skill_profile = context.user_data.get("skill_profile", "general_business_data") if context.user_data else "general_business_data"

        await update.message.chat.send_action("typing")

        doc_types = {
            "GO": ["cv", "letter", "mail"],
            "CV": ["cv"],
            "LETTRE": ["letter"],
            "MAIL": ["mail"],
        }.get(command, [])

        if not doc_types:
            await update.message.reply_text("Commande non reconnue. Utilise GO, CV, LETTRE ou MAIL.")
            return

        documents = await GenerationAgent.generate_documents(
            db, app.id, analysis, positioning, doc_types, skill_profile
        )

        mark_application_as_generated(db, app.id)

        response = "✅ Documents générés:\n\n"
        for doc_type, content in documents.items():
            response += f"📄 {doc_type.upper()}\n"

        await update.message.reply_text(response)

        for doc_type in doc_types:
            doc = db.query(GeneratedDocument).filter(
                GeneratedDocument.application_id == app.id,
                GeneratedDocument.document_type == doc_type,
            ).first()
            if doc:
                await update.message.reply_document(
                    document=doc.content.encode(),
                    filename=doc.filename,
                )

    except Exception as e:
        logger.error(f"Error generating documents: {e}", exc_info=True)

        if config.DEBUG_TELEGRAM_ERRORS:
            context_dict = {
                "user_id": user_id,
                "command": command,
                "application_id": app.id if app else None,
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
            await query.edit_message_text(
                "📂 Aucune candidature sauvegardée.",
                reply_markup=back_home()
            )
            return

        text = "📂 Mes candidatures récentes:\n\n"
        for app in apps:
            text += f"{app.company}\n⭐ {app.match_score}/10\n\n"

        await query.edit_message_text(text, reply_markup=back_home())
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
    """Handle generate CV button."""
    query = update.callback_query
    await query.answer("⏳ Génération du CV...")

    user_id = str(query.from_user.id)

    # Parse app_id from callback_data (format: gen_cv:123)
    callback_parts = query.data.split(":")
    app_id = int(callback_parts[1]) if len(callback_parts) > 1 else None

    db = SessionLocal()

    try:
        if app_id:
            from app.database.models import Application
            app = db.query(Application).filter_by(id=app_id).first()
        else:
            app = get_last_application(db, user_id)

        if not app:
            await query.answer("Aucune offre en cours", show_alert=True)
            return

        analysis = app.analyses[0].analysis_json if app.analyses else None
        positioning = app.recommended_angle
        skill_profile = context.user_data.get("skill_profile", "general_business_data") if context.user_data else "general_business_data"

        # Generate CV
        await GenerationAgent.generate_cv(db, app.id, analysis, positioning, skill_profile)
        mark_application_as_generated(db, app.id)

        # Get document
        from app.database.models import GeneratedDocument
        doc = db.query(GeneratedDocument).filter(
            GeneratedDocument.application_id == app.id,
            GeneratedDocument.document_type == "cv"
        ).first()

        if doc:
            await query.edit_message_text("✅ CV généré!", reply_markup=save_or_regenerate_menu())
            await query.message.reply_document(
                document=doc.content.encode(),
                filename=doc.filename
            )
    except Exception as e:
        logger.error(f"Error generating CV: {e}")
        await query.answer(f"Erreur: {str(e)}", show_alert=True)
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


async def gen_letter_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle generate letter button."""
    query = update.callback_query
    await query.answer("⏳ Génération de la lettre...")

    callback_parts = query.data.split(":")
    app_id = int(callback_parts[1]) if len(callback_parts) > 1 else None
    user_id = str(query.from_user.id)

    db = SessionLocal()

    try:
        if app_id:
            from app.database.models import Application
            app = db.query(Application).filter_by(id=app_id).first()
        else:
            app = get_last_application(db, user_id)

        if not app:
            await query.answer("Aucune offre en cours", show_alert=True)
            return

        analysis = app.analyses[0].analysis_json if app.analyses else None
        positioning = app.recommended_angle

        await GenerationAgent.generate_cv(db, app.id, analysis, positioning)
        mark_application_as_generated(db, app.id)

        from app.database.models import GeneratedDocument
        doc = db.query(GeneratedDocument).filter(
            GeneratedDocument.application_id == app.id,
            GeneratedDocument.document_type == "letter"
        ).first()

        if doc:
            await query.edit_message_text("✅ Lettre générée!", reply_markup=save_or_regenerate_menu())
            await query.message.reply_document(
                document=doc.content.encode(),
                filename=doc.filename
            )
    except Exception as e:
        logger.error(f"Error generating letter: {e}")
        await query.answer(f"Erreur: {str(e)}", show_alert=True)
    finally:
        db.close()


async def gen_mail_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle generate mail button."""
    query = update.callback_query
    await query.answer("⏳ Génération du mail...")

    callback_parts = query.data.split(":")
    app_id = int(callback_parts[1]) if len(callback_parts) > 1 else None
    user_id = str(query.from_user.id)

    db = SessionLocal()

    try:
        if app_id:
            from app.database.models import Application
            app = db.query(Application).filter_by(id=app_id).first()
        else:
            app = get_last_application(db, user_id)

        if not app:
            await query.answer("Aucune offre en cours", show_alert=True)
            return

        analysis = app.analyses[0].analysis_json if app.analyses else None
        positioning = app.recommended_angle

        await GenerationAgent.generate_cv(db, app.id, analysis, positioning)
        mark_application_as_generated(db, app.id)

        from app.database.models import GeneratedDocument
        doc = db.query(GeneratedDocument).filter(
            GeneratedDocument.application_id == app.id,
            GeneratedDocument.document_type == "mail"
        ).first()

        if doc:
            await query.edit_message_text("✅ Mail généré!", reply_markup=save_or_regenerate_menu())
            await query.message.reply_document(
                document=doc.content.encode(),
                filename=doc.filename
            )
    except Exception as e:
        logger.error(f"Error generating mail: {e}")
        await query.answer(f"Erreur: {str(e)}", show_alert=True)
    finally:
        db.close()


async def gen_all_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle generate all documents button."""
    query = update.callback_query
    await query.answer("⏳ Génération de tous les documents...")

    callback_parts = query.data.split(":")
    app_id = int(callback_parts[1]) if len(callback_parts) > 1 else None
    user_id = str(query.from_user.id)

    db = SessionLocal()

    try:
        if app_id:
            from app.database.models import Application
            app = db.query(Application).filter_by(id=app_id).first()
        else:
            app = get_last_application(db, user_id)

        if not app:
            await query.answer("Aucune offre en cours", show_alert=True)
            return

        analysis = app.analyses[0].analysis_json if app.analyses else None
        positioning = app.recommended_angle
        skill_profile = context.user_data.get("skill_profile", "general_business_data") if context.user_data else "general_business_data"

        # Generate all documents
        await GenerationAgent.generate_documents(db, app.id, analysis, positioning, ["cv", "letter", "mail"], skill_profile)
        mark_application_as_generated(db, app.id)

        await query.edit_message_text("✅ Documents générés!", reply_markup=save_or_regenerate_menu())

        # Send all documents
        from app.database.models import GeneratedDocument
        docs = db.query(GeneratedDocument).filter(
            GeneratedDocument.application_id == app.id
        ).all()

        for doc in docs:
            await query.message.reply_document(
                document=doc.content.encode(),
                filename=doc.filename
            )
    except Exception as e:
        logger.error(f"Error generating all: {e}")
        await query.answer(f"Erreur: {str(e)}", show_alert=True)
    finally:
        db.close()


async def regenerate_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle regenerate button (alias for gen_all)."""
    # Just forward to gen_all_callback
    update.callback_query.data = update.callback_query.data.replace("regenerate:", "gen_all:")
    await gen_all_callback(update, context)

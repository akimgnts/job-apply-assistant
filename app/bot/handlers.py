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

logger = logging.getLogger(__name__)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    await update.message.reply_text(
        "👋 Bienvenue dans Job Apply Assistant!\n\n"
        "Envoie-moi une offre d'emploi (URL ou texte brut) et je vais:\n"
        "• Analyser l'offre\n"
        "• Vérifier ton match\n"
        "• Proposer un angle de candidature\n"
        "• Générer CV, lettre et mail\n\n"
        "Commandes:\n"
        "/start — Afficher ce message\n"
        "/help — Aide détaillée\n"
        "/last — Voir dernière offre"
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
        await update.message.chat.send_action("typing")

        offer_text, metadata = InputAgent.process(raw_input)

        if offer_text is None:
            await update.message.reply_text(
                "❌ Je n'ai pas réussi à lire correctement cette offre.\n\n"
                "Colle-moi le texte complet de l'offre ici."
            )
            return

        await update.message.reply_text("🔍 Analyse en cours...")

        app = create_application(db, user_id, offer_text, metadata.get("source_url"))

        analysis = await AnalysisAgent.analyze(db, offer_text)

        analysis = MatchingAgent.enrich_analysis(analysis, db)

        save_analysis(db, app.id, analysis)

        update_application_with_analysis(db, app.id, analysis)

        positioning = await PositioningAgent.choose_angle(analysis)

        update_user_session(db, user_id, app.id, state="waiting_for_command")

        summary = format_analysis_summary(analysis, positioning)
        await update.message.reply_text(summary)

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
            db, app.id, analysis, positioning, doc_types
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
        f"📝 Stratégie CV:\n{analysis.get('cv_strategy', 'Non disponible')}\n\n"
        f"Réponds:\n"
        f"GO = générer CV + lettre + mail\n"
        f"CV = générer seulement le CV\n"
        f"LETTRE = générer seulement la lettre\n"
        f"MAIL = générer seulement le mail"
    )

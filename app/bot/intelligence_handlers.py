"""Intelligence handlers - Conversational analysis of job market and skill gaps."""

import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode
from sqlalchemy.orm import Session

from app.database.db import SessionLocal
from app.agents.intelligence_agent import IntelligenceAgent
from app.utils.debug import format_exception_for_telegram, split_telegram_message

logger = logging.getLogger(__name__)

# Conversation states
INTELLIGENCE_MENU, ASKING_QUESTION = range(2)


async def intelligence_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show intelligence menu with quick actions."""
    query = update.callback_query
    await query.answer()

    user_id = str(update.effective_user.id)
    db = SessionLocal()

    try:
        # Create intelligence menu with local and live market insights
        keyboard = [
            # Local database insights
            [InlineKeyboardButton("📊 Mes candidatures", callback_data="intel_summary")],
            [InlineKeyboardButton("🔍 Mes skill gaps", callback_data="intel_gaps")],
            [InlineKeyboardButton("📍 Offres par entreprise", callback_data="intel_companies")],
            [InlineKeyboardButton("🏆 Meilleurs matches", callback_data="intel_best")],
            # Live market insights (Elevia)
            [InlineKeyboardButton("💼 Marché en direct", callback_data="intel_market")],
            [InlineKeyboardButton("🎯 Top opportunités", callback_data="intel_opportunities")],
            # Free question
            [InlineKeyboardButton("💬 Poser une question", callback_data="intel_ask")],
            [InlineKeyboardButton("🏠 Accueil", callback_data="home")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        text = """🤖 <b>Agent Intelligence</b>

Bienvenue! Je peux t'aider à:
<b>Ton historique:</b>
• Résumer tes candidatures
• Identifier tes skill gaps
• Analyser les entreprises

<b>Marché en direct (Elevia):</b>
• Voir les tendances actuelles
• Découvrir les meilleures opportunités
• Analyser la demande en compétences

Choisis une analyse ou pose une question!"""

        await query.edit_message_text(
            text=text,
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )
        logger.info("intelligence_menu_callback user_id=%s", user_id)
        return INTELLIGENCE_MENU

    except Exception as e:
        logger.error("intelligence_menu_callback error: %s", str(e))
        await query.edit_message_text(f"❌ Erreur: {str(e)[:100]}")
        return INTELLIGENCE_MENU
    finally:
        db.close()


async def handle_intelligence_insight(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle quick insight requests."""
    query = update.callback_query
    await query.answer()

    user_id = str(update.effective_user.id)
    db = SessionLocal()

    try:
        insight_type = query.data.replace("intel_", "")

        # Special handling for "ask" - start free question mode
        if insight_type == "ask":
            await query.edit_message_text(
                text="💬 <b>Pose ta question</b>\n\nEnvoie une question naturelle sur tes offres, compétences, le marché, etc.",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("↩️ Retour", callback_data="intel_back")
                ]])
            )
            return ASKING_QUESTION

        # Show typing indicator
        await update.effective_chat.send_action("typing")

        # Get insight from agent instance
        agent = IntelligenceAgent()
        insight = await agent.get_quick_insight(db, user_id, insight_type)

        keyboard = [[InlineKeyboardButton("↩️ Retour", callback_data="intel_back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Split long messages
        messages = split_telegram_message(insight, max_length=4000)

        # Edit first message, send rest as new messages
        if messages:
            await query.edit_message_text(
                text=messages[0],
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup
            )
            for msg in messages[1:]:
                await update.effective_chat.send_message(
                    text=msg,
                    parse_mode=ParseMode.HTML,
                    reply_markup=reply_markup
                )

        logger.info("handle_intelligence_insight user_id=%s type=%s", user_id, insight_type)
        return INTELLIGENCE_MENU

    except Exception as e:
        logger.error("handle_intelligence_insight error: %s", str(e))
        error_msg = format_exception_for_telegram(e)
        await query.edit_message_text(f"❌ Erreur: {error_msg[:100]}")
        return INTELLIGENCE_MENU
    finally:
        db.close()


async def handle_free_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle free-form questions about job market and skills."""
    user_id = str(update.effective_user.id)
    db = SessionLocal()

    try:
        question = update.message.text
        logger.info("handle_free_question user_id=%s question_len=%d", user_id, len(question))

        # Show typing indicator
        await update.message.chat.send_action("typing")

        # Analyze question with agent instance
        agent = IntelligenceAgent()
        response = await agent.analyze_user_question(db, user_id, question)

        keyboard = [[InlineKeyboardButton("↩️ Retour au menu", callback_data="intel_back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Split long messages
        messages = split_telegram_message(response, max_length=4000)

        for msg in messages:
            await update.message.reply_text(
                text=msg,
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup
            )

        return ASKING_QUESTION

    except Exception as e:
        logger.error("handle_free_question error: %s", str(e))
        error_msg = format_exception_for_telegram(e)
        await update.message.reply_text(f"❌ Erreur: {error_msg}")
        return ASKING_QUESTION
    finally:
        db.close()


async def cancel_intelligence(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel intelligence conversation."""
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text(text="↩️ Retour au menu...")

    # Go back to home
    from app.bot.keyboards import home_menu
    from app.bot.message_formatter import format_home_message
    text, parse_mode = format_home_message()
    if update.callback_query:
        await update.callback_query.edit_message_text(
            text=text,
            parse_mode=parse_mode,
            reply_markup=home_menu()
        )
    else:
        await update.message.reply_text(text, parse_mode=parse_mode, reply_markup=home_menu())

    return ConversationHandler.END

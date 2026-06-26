import logging
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ConversationHandler, filters
from app.config import config
from app.bot.handlers import (
    start_command,
    help_command,
    last_command,
    handle_offer,
    handle_command,
    home_callback,
    analyze_offer_callback,
    my_applications_callback,
    view_master_cv_callback,
    view_profile_callback,
    view_match_callback,
    view_match_with_app_callback,
    gen_cv_callback,
    gen_letter_callback,
    gen_mail_callback,
    gen_all_callback,
    regenerate_callback,
    save_application_callback,
)

# Elevia handlers (only imported if enabled)
if config.ELEVIA_ENABLED:
    from app.bot.elevia_handlers import (
        elevia_health_check,
        elevia_search_offers,
        elevia_catalog,
        elevia_load_offer,
        elevia_upload_profile,
        elevia_get_profile,
    )

# Career intelligence handlers
from app.bot.career_intelligence_handlers import (
    career_intelligence_summary,
    skill_gaps_analysis,
    project_recommendations,
    role_family_analysis,
    top_requested_skills,
    most_frequent_gaps,
    strongest_skills,
    save_intelligence_snapshot,
)

# Intelligence Agent handlers (conversational)
from app.bot.intelligence_handlers import (
    intelligence_menu_callback,
    handle_intelligence_insight,
    handle_free_question,
    cancel_intelligence,
    INTELLIGENCE_MENU,
    ASKING_QUESTION,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=getattr(logging, config.LOG_LEVEL),
)
logger = logging.getLogger(__name__)

def setup_bot():
    """Configure bot handlers and filters."""
    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("last", last_command))

    # Elevia commands (if enabled)
    if config.ELEVIA_ENABLED:
        app.add_handler(CommandHandler("elevia_health", elevia_health_check))
        app.add_handler(CommandHandler("search_offers", elevia_search_offers))
        app.add_handler(CommandHandler("catalog", elevia_catalog))
        app.add_handler(CommandHandler("load_elevia_offer", elevia_load_offer))
        app.add_handler(CommandHandler("upload_profile", elevia_upload_profile))
        app.add_handler(CommandHandler("get_profile", elevia_get_profile))

    # Career intelligence commands
    app.add_handler(CommandHandler("intelligence", career_intelligence_summary))
    app.add_handler(CommandHandler("gaps", skill_gaps_analysis))
    app.add_handler(CommandHandler("projects", project_recommendations))
    app.add_handler(CommandHandler("roles", role_family_analysis))
    app.add_handler(CommandHandler("top_skills", top_requested_skills))
    app.add_handler(CommandHandler("gaps_most", most_frequent_gaps))
    app.add_handler(CommandHandler("strengths", strongest_skills))
    app.add_handler(CommandHandler("save_intelligence", save_intelligence_snapshot))

    # Callbacks (buttons) — with and without app_id
    app.add_handler(CallbackQueryHandler(home_callback, pattern="^home$"))
    app.add_handler(CallbackQueryHandler(analyze_offer_callback, pattern="^analyze_offer$"))
    app.add_handler(CallbackQueryHandler(my_applications_callback, pattern="^my_applications$"))
    app.add_handler(CallbackQueryHandler(view_master_cv_callback, pattern="^view_master_cv$"))
    app.add_handler(CallbackQueryHandler(view_profile_callback, pattern="^view_profile$"))

    # Match view: with or without app_id
    app.add_handler(CallbackQueryHandler(view_match_with_app_callback, pattern="^view_match(:[0-9]+)?$"))

    # Gen CV: with or without app_id
    app.add_handler(CallbackQueryHandler(gen_cv_callback, pattern="^gen_cv(:[0-9]+)?$"))

    # Gen Letter: with or without app_id
    app.add_handler(CallbackQueryHandler(gen_letter_callback, pattern="^gen_letter(:[0-9]+)?$"))

    # Gen Mail: with or without app_id
    app.add_handler(CallbackQueryHandler(gen_mail_callback, pattern="^gen_mail(:[0-9]+)?$"))

    # Gen All: with or without app_id
    app.add_handler(CallbackQueryHandler(gen_all_callback, pattern="^gen_all(:[0-9]+)?$"))

    # Regenerate: with or without app_id
    app.add_handler(CallbackQueryHandler(regenerate_callback, pattern="^regenerate(:[0-9]+)?$"))

    # Save Application: with or without app_id
    app.add_handler(CallbackQueryHandler(save_application_callback, pattern="^save_application(:[0-9]+)?$"))

    # Intelligence Agent conversation handler
    intelligence_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(intelligence_menu_callback, pattern="^intelligence_menu$")],
        states={
            INTELLIGENCE_MENU: [
                CallbackQueryHandler(handle_intelligence_insight, pattern="^intel_"),
            ],
            ASKING_QUESTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_free_question),
                CallbackQueryHandler(intelligence_menu_callback, pattern="^intelligence_menu$"),
            ],
        },
        fallbacks=[CallbackQueryHandler(cancel_intelligence, pattern="^home$")],
    )
    app.add_handler(intelligence_conv_handler)

    # Text messages
    app.add_handler(MessageHandler(filters.Regex("^(GO|CV|LETTRE|MAIL)$"), handle_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_offer))

    return app

def main():
    """Start the bot."""
    logger.info("Starting Job Apply Assistant bot...")
    app = setup_bot()
    app.run_polling(allowed_updates=[])

if __name__ == "__main__":
    main()

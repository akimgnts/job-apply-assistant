import logging
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
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
    gen_cv_callback,
    save_application_callback,
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

    # Callbacks (buttons)
    app.add_handler(CallbackQueryHandler(home_callback, pattern="^home$"))
    app.add_handler(CallbackQueryHandler(analyze_offer_callback, pattern="^analyze_offer$"))
    app.add_handler(CallbackQueryHandler(my_applications_callback, pattern="^my_applications$"))
    app.add_handler(CallbackQueryHandler(view_master_cv_callback, pattern="^view_master_cv$"))
    app.add_handler(CallbackQueryHandler(view_profile_callback, pattern="^view_profile$"))
    app.add_handler(CallbackQueryHandler(view_match_callback, pattern="^view_match$"))
    app.add_handler(CallbackQueryHandler(gen_cv_callback, pattern="^gen_cv$"))
    app.add_handler(CallbackQueryHandler(save_application_callback, pattern="^save_application$"))

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

import logging
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from app.config import config
from app.bot.handlers import (
    start_command,
    help_command,
    last_command,
    handle_offer,
    handle_command,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=getattr(logging, config.LOG_LEVEL),
)
logger = logging.getLogger(__name__)

def setup_bot():
    """Configure bot handlers and filters."""
    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("last", last_command))

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

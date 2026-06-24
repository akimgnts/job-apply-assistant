import logging
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log errors caused by updates."""
    logger.error(f"Update {update} caused error {context.error}")


async def log_update_probe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log incoming updates for debugging."""
    if update.message:
        logger.debug(f"Message from {update.effective_user.id}: {update.message.text}")
    elif update.callback_query:
        logger.debug(f"Callback from {update.effective_user.id}: {update.callback_query.data}")

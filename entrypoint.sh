#!/bin/bash
set -e

echo "🔄 Running database migrations..."
alembic upgrade head

echo "✅ Migrations complete. Starting bot..."
python -m app.bot.telegram_bot

#!/bin/bash
# Job Apply Assistant - Smart startup script

set -e

echo "🤖 Job Apply Assistant - Startup"
echo "=================================="
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ .env file not found"
    echo "   Run: cp .env.example .env"
    exit 1
fi

# Test database connection
echo "🔧 Testing database connection..."
python -c "
import os
from dotenv import load_dotenv
load_dotenv()

import psycopg2
try:
    # Extract connection string
    db_url = os.getenv('DATABASE_URL')
    import re
    match = re.match(r'postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)', db_url)
    if not match:
        raise ValueError('Invalid DATABASE_URL format')

    user, password, host, port, database = match.groups()

    conn = psycopg2.connect(
        host=host,
        port=int(port),
        user=user,
        password=password,
        database=database,
        sslmode='disable',
        connect_timeout=3
    )
    cursor = conn.cursor()
    cursor.execute('SELECT version();')
    version = cursor.fetchone()[0]
    cursor.close()
    conn.close()

    print(f'✓ Connected to {host}:{port}/{database}')
    print(f'  PostgreSQL: {version.split(\",\")[0]}')
except psycopg2.OperationalError as e:
    error_msg = str(e)
    if 'could not translate host name' in error_msg:
        print(f'✗ Cannot resolve hostname')
        print(f'  Hint: Check if using internal Coolify hostname from outside network')
    elif 'Connection refused' in error_msg:
        print(f'✗ Connection refused')
        print(f'  Hint: Check if database server is running at {host}:{port}')
    elif 'password authentication failed' in error_msg:
        print(f'✗ Authentication failed')
        print(f'  Hint: Check DATABASE_URL credentials in .env')
    else:
        print(f'✗ Connection error: {error_msg}')
    print()
    print('📋 Troubleshooting:')
    print('  1. Run: python test_db_connection.py')
    print('  2. Read: DATABASE_SETUP.md')
    print('  3. For Coolify: Verify public proxy in Coolify dashboard')
    print('  4. For Local: Install Docker and run: docker compose up -d')
    exit 1
" || exit 1

echo ""
echo "📦 Applying database migrations..."
alembic upgrade head || echo "⚠️  Migration failed - check database state"

echo ""
echo "🌱 Seeding profile data..."
python -m app.database.seed_profile || echo "⚠️  Seed failed - continuing anyway"

echo ""
echo "🚀 Starting Telegram bot..."
echo "   Press Ctrl+C to stop"
echo ""

python -m app.bot.telegram_bot

#!/bin/bash
# Apply all pending database migrations

set -e

echo "Starting database migration process..."
echo "======================================="

# Check if DATABASE_URL is set
if [ -z "$DATABASE_URL" ]; then
    echo "❌ Error: DATABASE_URL not set"
    exit 1
fi

echo "Database: $DATABASE_URL"
echo ""

# Wait for database to be ready
echo "Waiting for database to be ready..."
max_attempts=30
attempt=1
while [ $attempt -le $max_attempts ]; do
    if psql "$DATABASE_URL" -c "SELECT 1" > /dev/null 2>&1; then
        echo "✅ Database is ready"
        break
    fi
    echo "  Attempt $attempt/$max_attempts..."
    sleep 1
    attempt=$((attempt + 1))
done

if [ $attempt -gt $max_attempts ]; then
    echo "❌ Database not reachable after $max_attempts attempts"
    exit 1
fi

echo ""
echo "Current migration status:"
alembic current || echo "  (No migrations applied yet)"

echo ""
echo "Applying all pending migrations..."
alembic upgrade head

echo ""
echo "Migration status after upgrade:"
alembic current

echo ""
echo "✅ All migrations applied successfully!"

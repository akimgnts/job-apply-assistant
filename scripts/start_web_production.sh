#!/bin/sh
set -eu
: "${DATABASE_URL:?DATABASE_URL is required}"
: "${WEB_ACCESS_TOKEN:?WEB_ACCESS_TOKEN is required for production}"
: "${WEB_USER_ID:?WEB_USER_ID must identify the candidate workspace}"
alembic upgrade head
exec python -m uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --workers 1 --proxy-headers --forwarded-allow-ips='*'

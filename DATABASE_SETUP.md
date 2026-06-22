# Database Setup Guide

## Current Status

The job-apply-assistant can connect to two database setups:

### 1. Coolify Remote Database (Target)
**Status**: ❌ Authentication failing - public proxy not accepting credentials

```
Host: 37.59.112.53
Port: 5432
User: postgres
Database: postgres
```

**Issue**: `FATAL: password authentication failed for user "postgres"`

**Possible solutions**:
- [ ] Check Coolify dashboard for public proxy settings
- [ ] Verify if public proxy requires different credentials than internal connection
- [ ] Check if firewall rules need configuration for public access
- [ ] Try accessing from within Coolify infrastructure (different creds?)

---

### 2. Local PostgreSQL (Development/Fallback)

**Status**: ❌ Docker not installed on this machine

**Setup steps** (when Docker is available):
```bash
docker compose up -d  # Start local PostgreSQL
alembic upgrade head  # Apply migrations
python -m app.database.seed_profile  # Seed profile blocks
```

**Connection string**:
```
postgresql://jobapply:password@localhost:5432/job_apply_db
```

---

## Switching Database Connections

### To use Coolify (once auth is resolved):
Edit `.env`:
```
DATABASE_URL=postgresql://postgres:PASSWORD@37.59.112.53:5432/postgres
```

### To use Local PostgreSQL:
Edit `.env`:
```
DATABASE_URL=postgresql://jobapply:password@localhost:5432/job_apply_db
```

---

## Troubleshooting

Run the diagnostic tool:
```bash
python test_db_connection.py
```

This will test:
- Current configuration
- Alternative ports (3000 for Coolify)
- Localhost fallback
- Alternative database names

---

## Next Steps

1. **For Coolify access**:
   - Check Coolify documentation for public proxy PostgreSQL access
   - Look for per-database credentials (different from master password)
   - Verify public proxy is enabled in Coolify settings
   - Test with `test_db_connection.py` for debugging

2. **For local development**:
   - Install Docker Desktop
   - Run `docker compose up -d`
   - Update `.env` with local PostgreSQL URL

3. **Once DB connects**:
   - Run `alembic upgrade head` to apply schema
   - Run `python -m app.database.seed_profile` to populate test data
   - Run `python -m app.bot.telegram_bot` to start bot

# Apply Database Migrations

## Quick Start

```bash
# 1. Start PostgreSQL
docker compose up -d postgres
sleep 5

# 2. Apply migrations
alembic upgrade head

# 3. Verify
alembic current
```

Expected output: `005_add_saved_status_enum`

## What Gets Fixed

| Issue | Migration | Impact |
|-------|-----------|--------|
| Missing `format` column | 004 | CV/letter/mail generation will crash |
| Missing `'saved'` enum value | 005 | Saving applications will fail |
| Missing `telegram_user_id`, `positioning`, `skill_profile` | 002 | Document metadata tracking breaks |

## If Docker Compose Fails

Use local PostgreSQL:
```bash
# Assuming PostgreSQL running on localhost:5432
psql -U jobapply -d job_apply_db -h localhost
```

Then in psql:
```sql
-- Check current state
\dt  -- list tables
\d generated_documents  -- show generated_documents schema

-- Check if columns exist
SELECT column_name FROM information_schema.columns 
WHERE table_name='generated_documents';

-- Check enum values
SELECT enum_range(NULL::applicationstatusenum);
```

If columns are missing, check migration files in `migrations/versions/` and apply manually via SQL if needed.

## Troubleshooting

### Alembic can't find database
```
Error: could not translate host name "..." to address
```
→ Check `.env` DATABASE_URL is reachable
→ Verify PostgreSQL container is running: `docker compose ps`

### Migration fails with "already exists"
```
Error: column "format" already exists
```
→ Migration may have been partially applied
→ Check alembic_version table: `SELECT * FROM alembic_version;`
→ If needed, manually insert missing version: `INSERT INTO alembic_version VALUES ('005');`

### Enum error still happens after migration 005
```
Error: invalid input value for enum applicationstatusenum: "saved"
```
→ Migration 005 may not have run
→ Check if 'saved' exists: `SELECT enum_range(NULL::applicationstatusenum);`
→ If not, run manually: `ALTER TYPE applicationstatusenum ADD VALUE 'saved' AFTER 'generated';`

## Next Test

Once migrations applied, test document generation:

```python
from app.agents.generation_agent import GenerationAgent
from app.database.db import SessionLocal
from app.database.models import Application

# Get a test application
db = SessionLocal()
app = db.query(Application).first()

if app and app.analyses:
    analysis = app.analyses[0].analysis_json
    docs = await GenerationAgent.generate_documents(
        db,
        application_id=app.id,
        analysis=analysis,
        positioning="Data Analyst",
        skill_profile="data_bi"
    )
    print(f"Generated: {list(docs.keys())}")
```

Should output: `['cv', 'letter', 'mail']` with no errors.

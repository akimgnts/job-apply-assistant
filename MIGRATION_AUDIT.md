# Database Migration Audit

## Status: INCOMPLETE — Pending Migrations

The following migrations exist but have NOT been applied to the PostgreSQL database.

### Migration Chain

```
001 (Initial Schema)
  ↓
002 (Add Document Metadata: telegram_user_id, positioning)
  ↓
003 (Idempotent: Safe add columns)
  ↓
004 (Add Document Format: format column)
  ↓
005 (Add Saved Status Enum)  ← NEW
```

## Expected Schema Changes

### Migration 002: Add Document Metadata
- Adds `telegram_user_id` to `generated_documents` table
- Adds `positioning` to `generated_documents` table
- Adds `skill_profile` to `generated_documents` table

**Status in code**: ✅ implemented in models.py
**Status in migration**: ✅ migration/versions/002_add_document_metadata.py exists
**Status in database**: ❌ NOT APPLIED

### Migration 003: Idempotent Add Columns
- Safely adds missing columns if they don't already exist
- Re-checks for `telegram_user_id`, `positioning`, `skill_profile`

**Status**: ✅ defensive migration, safe to run multiple times

### Migration 004: Add Document Format
- Adds `format` column to `generated_documents`
- Default value: "html"

**Status in code**: ✅ implemented in models.py
**Status in migration**: ✅ migration/versions/004_add_document_format.py exists
**Status in database**: ❌ NOT APPLIED

### Migration 005: Add Saved Status Enum
- Adds `'saved'` value to `applicationstatusenum` PostgreSQL enum
- Required by current models.py `ApplicationStatusEnum`

**Status in code**: ✅ ApplicationStatusEnum.saved in models.py
**Status in migration**: ✅ migration/versions/005_add_saved_status_enum.py JUST CREATED
**Status in database**: ❌ NOT APPLIED — will cause "invalid input value for enum" error

## Errors Encountered (Previous Session)

### Error 1: UndefinedColumn "format"
```
sqlalchemy.exc.ProgrammingError: (psycopg2.ProgrammingError) column "format" of relation "generated_documents" does not exist
```
**Root Cause**: Migration 004 not applied
**Fix**: Run `alembic upgrade head`

### Error 2: InvalidTextRepresentation for enum
```
sqlalchemy.exc.StatementError: (psycopg2.InternalError) invalid input value for enum applicationstatusenum: "saved"
```
**Root Cause**: Migration 001 enum only had 3 values (analyzed, generated, archived), missing 'saved'
**Fix**: Run migration 005 (just created)

### Error 3: Database URL Unreachable
```
psycopg2.OperationalError: could not translate host name "yde015v0piay27f73rueuayf" to address
```
**Root Cause**: .env DATABASE_URL pointing to cloud database not accessible from this machine
**Fix**: Use local PostgreSQL or Docker Compose

## How to Apply Migrations

### Option 1: Using Alembic (Recommended)
```bash
# View current status
alembic current

# Apply all pending migrations
alembic upgrade head

# Verify
alembic current
```

### Option 2: Using Docker Compose
```bash
# Start PostgreSQL container
docker compose up -d postgres

# Run migrations inside app container
docker compose run --rm app alembic upgrade head
```

### Option 3: Manual SQL (If Alembic fails)
Connect to PostgreSQL directly:
```sql
-- Add columns
ALTER TABLE generated_documents ADD COLUMN telegram_user_id VARCHAR(255) NOT NULL DEFAULT '';
ALTER TABLE generated_documents ADD COLUMN positioning VARCHAR(255);
ALTER TABLE generated_documents ADD COLUMN skill_profile VARCHAR(255);
ALTER TABLE generated_documents ADD COLUMN format VARCHAR(10) NOT NULL DEFAULT 'html';

-- Add enum value
ALTER TYPE applicationstatusenum ADD VALUE 'saved' AFTER 'generated';

-- Update alembic history
INSERT INTO alembic_version (version_num) VALUES ('002');
INSERT INTO alembic_version (version_num) VALUES ('003');
INSERT INTO alembic_version (version_num) VALUES ('004');
INSERT INTO alembic_version (version_num) VALUES ('005');
```

## Files to Review

- **Models**: `app/database/models.py` — current schema definition
- **Migrations**: `migrations/versions/00X_*.py` — all migration definitions
- **Current DB**: Must match all 5 migrations after `alembic upgrade head`

## Next Steps

1. ✅ Created migration 005 to add 'saved' enum value
2. ⏳ Apply all migrations: `alembic upgrade head`
3. ⏳ Verify columns exist in PostgreSQL
4. ⏳ Test CV generation with new `format="html"` field
5. ⏳ Test document saves with `telegram_user_id`, `positioning`, `skill_profile`

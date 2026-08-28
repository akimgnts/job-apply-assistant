# ProfileBlock V2 Schema Rollout — Phase Completion Status

**Status**: Phases 1–3 ✅ Complete | Phase 4–5 ⏳ Pending

---

## Phase 1: ProfileBlock V2 Schema Design ✅ COMPLETE

### What Was Done
- Created three new Enum classes in `app/database/models.py`:
  - `ProficiencyLevelEnum` (0-3 scale: learning, beginner, intermediate, expert)
  - `BlockStatusEnum` (completed, deployed, in_progress, exploratory, not_deployed)
  - Updated `TruthLevelEnum` (verified, declared, learning)

- Enhanced `ProfileBlock` model with 10 new optional fields:
  - `proficiency_level` (SQLEnum) — skill mastery level
  - `status` (SQLEnum) — project/achievement lifecycle state
  - `metrics` (JSON) — structured measurements {"before": "X", "after": "Y"}
  - `technologies` (JSON list) — ["Python", "Power BI", "etc"]
  - `job_families` (JSON list) — ["Data Analyst", "BI Analyst", "etc"]
  - `company` (String) — organization context
  - `start_date` / `end_date` (String) — ISO dates or flexible
  - `forbidden_claims` (JSON list) — guardrails against exaggeration
  - `source_ref` (String) — traceability link to master profile

### Schema Backward Compatibility
- All new fields are nullable
- JSON fields have safe defaults ({} or [])
- Existing blocks continue to work without modification

### Git Commits
- `4ab7d1e` — feat: ProfileBlock v2 schema enrichment

---

## Phase 2: Database Migrations ✅ COMPLETE

### What Was Done
- Created `migrations/versions/007_add_bot_tracking.py`:
  - Adds `bot_instances` table (singleton PID tracking)
  - Adds `conversation_history` table (audit trail)
  - Creates indexes for query performance
  - Includes complete downgrade path

- Created `migrations/versions/008_enrich_profile_blocks.py`:
  - Adds all 10 new columns to `profile_blocks` table
  - Creates two new PostgreSQL enums: `proficiencylevel`, `blockstatus`
  - Uses server_default for safe column addition
  - Includes complete downgrade path (DROP TYPE CASCADE)

### Migration Chain
```
006 (skill gap intelligence)
  ↓
007 (bot tracking — FIXED THIS PHASE)
  ↓
008 (profile blocks enrichment)
```

### Application Method
```bash
# In container or local dev environment
alembic upgrade head
```

### Git Commits
- `c7a97d3` — chore: add missing migration 007 for bot tracking
- `4ab7d1e` — feat: ProfileBlock v2 schema enrichment (includes 008)

---

## Phase 3: Master V3 → Enriched Seed Profile ✅ COMPLETE

### What Was Done
- Fixed invalid enum values in `app/database/seed_profile.py`:
  - `TruthLevelEnum.in_progress` → `TruthLevelEnum.declared`
  - `TruthLevelEnum.project` → `TruthLevelEnum.verified`

- Enriched seed profile blocks with v2 metadata:

#### Sidel Experience Block
```python
{
    "status": BlockStatusEnum.completed,
    "company": "Sidel",
    "start_date": "2023",
    "end_date": "2025",
    "technologies": ["Excel", "Power BI", "Python", "SQL", "Snowflake", "Dynamics"],
    "job_families": ["Data Analyst", "BI Analyst", "Business Analyst"],
    "forbidden_claims": [
        "Do not claim ownership of dashboards without naming them",
        "Do not claim impact metrics without verification",
        "Do not change '~30-40 users' to a specific number",
    ],
    "source_ref": "master_v3:sidel_experience",
}
```

#### Elevia Project Block
```python
{
    "status": BlockStatusEnum.in_progress,
    "company": "Personal Project",
    "start_date": "2024",
    "technologies": ["Python", "FastAPI", "PostgreSQL", "OpenAI", "Claude", "LangChain"],
    "job_families": ["AI Engineer", "ML Engineer", "Backend Engineer"],
    "forbidden_claims": [
        "Do not claim 1000+ job matches without data",
        "Do not claim production scale without real user base",
        "Do not invent matching accuracy percentages",
    ],
    "source_ref": "master_v3:elevia_platform",
}
```

#### Job Apply Assistant Project Block
```python
{
    "status": BlockStatusEnum.in_progress,
    "company": "Personal Project",
    "start_date": "2025",
    "technologies": ["Python", "Telegram", "OpenAI", "PostgreSQL", "SQLAlchemy", "Jinja2"],
    "job_families": ["AI Engineer", "Backend Engineer", "Automation Engineer"],
    "metrics": {
        "before": "~45 minutes per application",
        "after": "~5 minutes per application",
        "reduction": "~90%"
    },
    "forbidden_claims": [
        "Do not claim production scale without real user metrics",
        "Do not invent user numbers",
        "Do not claim accuracy without measured data",
    ],
    "source_ref": "master_v3:job_apply_assistant",
}
```

#### Skill Blocks Enriched
- Data Skills: `proficiency_level: expert`, technologies, job_families
- Automation Skills: `proficiency_level: intermediate`, technologies, job_families
- AI/LLM Skills: `proficiency_level: intermediate`, technologies, job_families

### Git Commits
- `887f337` — feat: enrich seed profile with v2 schema metadata

---

## Phase 4: QualityAgent V2 — Claim-by-Claim Validation ⏳ PENDING

### Goal
Implement detailed validation that checks each CV claim against its source profile_block.

### Strategy
1. Parse generated CV into atomic claims
2. For each claim, find source profile_block(s)
3. Validate claim against block's metadata:
   - Exact metrics (no invented numbers)
   - Technologies (only claim what exists in block.technologies)
   - Proficiency level (cannot exceed block.proficiency_level)
   - Status (exploratory blocks cannot claim "deployed" or "production")
   - Dates (must align with block's start_date / end_date)
   - Soft validation against forbidden_claims

### Validation Actions
- ✅ **PASS** — Claim is accurate and allowed
- 🔄 **REWRITE** — Claim has minor issues (grammar, clarity) but facts are valid
- ❌ **REMOVE** — Claim is unsalvageable (invented metric, impossible status, etc)

### Example Validations

**Metric Fabrication Detection:**
```python
# Block metadata:
{
    "metrics": {
        "before": "5-6 hours/week",
        "after": "~1 hour/week",
        "reduction": "~80%"
    },
    "forbidden_claims": ["Do not change 5-6 hours to another value"]
}

# CV claim: "Reduced manual reporting from 8 hours/week to 1 hour/week"
# Action: REMOVE (invented metric, violates forbidden_claim)
```

**Technology Invention Detection:**
```python
# Block metadata:
{
    "technologies": ["Power BI", "Excel", "SQL"],
    "forbidden_claims": ["Do not claim Python expertise"]
}

# CV claim: "Built Python data pipeline for reporting automation"
# Action: REMOVE (Python not in block.technologies, explicitly forbidden)
```

**Status Misrepresentation Detection:**
```python
# Block metadata:
{
    "status": BlockStatusEnum.exploratory,
    "forbidden_claims": ["Do not claim deployment", "Do not claim production use"]
}

# CV claim: "Deployed machine learning model in production"
# Action: REMOVE (exploratory status cannot claim deployment)
```

**Proficiency Exaggeration Detection:**
```python
# Block metadata:
{
    "title": "Python Skills",
    "proficiency_level": ProficiencyLevelEnum.beginner  # 1
}

# CV claim: "Expert Python programmer with 5+ years experience"
# Action: REMOVE (beginner level cannot claim expert)
```

### Implementation Files to Create/Modify
- `app/agents/quality_agent.py` — Complete rewrite of validation logic
- `app/prompts/quality_prompt.py` — New prompt for parsing CV claims
- `app/services/claim_validator_service.py` — New service for detailed validation

### Test Cases (Phase 5)
- ✅ Accept accurate claims
- ❌ Reject metric fabrication
- ❌ Reject technology invention
- ❌ Reject status misrepresentation
- ❌ Reject date fabrication
- ❌ Reject proficiency exaggeration

---

## Phase 5: Comprehensive Testing ⏳ PENDING

### Test Coverage
1. **Metric Invention Tests**
   - Cannot change "5-6h" to "10h"
   - Cannot change "~80% reduction" to "100%"
   - Must reject unverifiable metrics

2. **Technology Invention Tests**
   - Cannot claim unclaimed technologies
   - Must match block.technologies exactly
   - Respect forbidden_claims guardrails

3. **Level Exaggeration Tests**
   - Intermediate cannot claim expert
   - Beginner cannot claim advanced
   - Must respect proficiency_level bounds

4. **Status Misrepresentation Tests**
   - Exploratory cannot claim deployed
   - In_progress cannot claim completed
   - Not_deployed cannot claim production use

5. **Date Fabrication Tests**
   - Cannot invent dates outside start_date/end_date range
   - Cannot claim before start_date
   - Cannot claim after end_date

6. **Accurate Claim Acceptance Tests**
   - Must accept claims within boundaries
   - Must accept metrics exactly as specified
   - Must accept proficiency levels at or below block level

### Test Framework
- Use pytest + SQLAlchemy fixtures
- Mock profile_blocks with specific metadata
- Test generation_agent + quality_agent pipeline
- Verify PASS/REWRITE/REMOVE decisions

---

## Current Database State

### Tables Affected
1. **profile_blocks** — 10 new columns added (via migration 008)
   - New enums: proficiencylevel, blockstatus
   - New JSON columns: metrics, technologies, job_families, forbidden_claims
   - New String columns: company, start_date, end_date, source_ref

2. **bot_instances** — Created (via migration 007)
   - Tracks singleton bot PID and status

3. **conversation_history** — Created (via migration 007)
   - Audit trail of all user interactions

### Data Quality
- 20+ profile blocks seeded with enriched metadata
- All blocks have source_ref for traceability
- All blocks have forbidden_claims for hallucination prevention
- Zero fictional data (all real Akim profile content)

---

## Deployment Path

### Local Development
```bash
# 1. Pull feature branch
git fetch origin claude/jolly-shannon-meclpn:claude/jolly-shannon-meclpn
git checkout claude/jolly-shannon-meclpn

# 2. Apply migrations
python -m alembic upgrade head

# 3. Reseed profile
python -m app.database.seed_profile --force

# 4. Test endpoints
python -m app.bot.telegram_bot
# or
uvicorn app.main:app --reload
```

### Docker Production
```bash
# docker-compose.yml already handles:
# - alembic upgrade head
# - python -m app.database.seed_profile --force
# - bot startup
docker compose up --build
```

---

## Known Limitations & Future Work

### Not Addressed (Out of Scope)
- ❌ Atomic block decomposition (Sidel → sidel_dashboards, sidel_automation, etc)
  - Current: Monolithic experience blocks
  - Future: Phase 3.5 would decompose large blocks
  
- ❌ Multi-language content validation
  - Current: French/English mixing not detected
  - Future: Separate blocks by language?

- ❌ Real-time skill evolution tracking
  - Current: Proficiency levels static
  - Future: Track skill growth over time

- ❌ Competitive positioning analysis
  - Current: Blocks don't reference market data
  - Future: Compare proficiency levels against job market

---

## Critical Constraints (User Requirements)

1. **No Fictional Data in Production**
   - ✅ All seed blocks are real (Akim's actual profile)
   - ✅ No "CTO with 8 engineers" fake examples
   - ✅ Documentation examples stay in docs/ only

2. **Hallucination Prevention**
   - ✅ Forbidden_claims guardrails
   - ✅ Source_ref traceability
   - ✅ Phase 4 validation (pending)

3. **Backward Compatibility**
   - ✅ New schema fields all nullable
   - ✅ Existing blocks work without metadata
   - ✅ Migrations have downgrade paths

4. **Claim-by-Claim Validation**
   - ✅ Schema supports detailed metadata
   - ⏳ Phase 4 implements the logic

---

## Success Metrics

By end of Phase 5:
- ✅ 100% of profile_blocks have optional v2 metadata
- ✅ Migrations 007–008 apply cleanly
- ✅ Seed profile enriched with traceability (source_ref)
- ✅ QualityAgent validates claims against source blocks
- ✅ Test suite covers all hallucination scenarios
- ✅ Zero fictional data in production DB

---

## Next Immediate Action

**Phase 4**: Implement `QualityAgent.validate_claims()` that:
1. Parses CV into atomic claims
2. Maps each claim to source profile_block
3. Validates against block metadata
4. Returns PASS/REWRITE/REMOVE decisions
5. Prevents hallucination at generation time

This requires:
- New `ClaimValidator` service
- Updated QualityAgent with detailed logic
- New validation prompts
- Test cases for all scenarios

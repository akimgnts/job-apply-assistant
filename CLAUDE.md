# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Job Apply Assistant** — AI-powered job application assistant accessible via Telegram. Analyzes job offers, matches against candidate profile, and generates tailored CV, letter, and email templates. Core logic is completely decoupled from Telegram — extensible to web/API later.

**Stack**: Python 3.11 + FastAPI, SQLAlchemy, PostgreSQL, OpenAI API, python-telegram-bot, Jinja2.

**MVP V1 Status**: Complete. Production-ready core, single-user Telegram interface.

## Architecture Layers

```
Telegram Bot (handlers.py)
  ↓ [route to]
Agents (agents/*) — pure business logic, framework-agnostic
  ↓ [use]
Services (services/*) — infrastructure: OpenAI, DB, files, scraping
  ↓ [store in]
Database (models.py + migrations/)
```

**Critical principle**: Agents have ZERO Telegram dependencies. All business logic is testable independently. Handlers orchestrate agents + services + DB.

### Layer Responsibilities

#### Agents (`app/agents/`)
Pure functions, async-ready, no I/O except through services.
- `InputAgent.process()` → detect URL vs text, extract
- `AnalysisAgent.analyze()` → OpenAI offer analysis + matching
- `MatchingAgent.enrich_analysis()` → validate profile blocks
- `PositioningAgent.choose_angle()` → select best angle from 7 fixed options
- `GenerationAgent.generate_*()` → CV/letter/mail from analysis + profile
- `QualityAgent.check_document()` → verify no invented claims

#### Services (`app/services/`)
External integrations + cross-cutting concerns.
- `openai_service` → wrapper around OpenAI API
- `scraping_service` → URL extraction (trafilatura)
- `document_service` → Jinja2 templating + file I/O
- `application_service` → all DB operations (CRUD + transactions)

#### Bot (`app/bot/`)
Telegram interface only. Routes → agents → formats response.
- `telegram_bot.py` → polling loop + handler setup
- `handlers.py` → message/command processing, no business logic

#### Database (`app/database/`)
- `models.py` → SQLAlchemy models (ProfileBlock, Application, JobAnalysis, GeneratedDocument, UserSession)
- `db.py` → connection + SessionLocal factory
- `seed_profile.py` → idempotent seed script
- `migrations/` → Alembic version control

#### Prompts (`app/prompts/`)
Standalone prompt builders. Easy to test/iterate.
- `analysis_prompt.py` → job offer analysis
- `positioning_prompt.py` → angle selection
- `generation_prompt.py` → CV, letter, mail prompts
- `quality_prompt.py` → document verification

## Key Patterns

### No Invented Content

**Rule**: OpenAI can ONLY use what exists in `profile_blocks`.

- Analysis JSON includes `profile_blocks_to_use` (IDs) and `missing_points` (gaps).
- `MatchingAgent.enrich_analysis()` validates block IDs exist.
- `GenerationAgent` queries actual blocks before rendering.
- `QualityAgent` double-checks generated content doesn't invent.
- If critical skill is missing → must appear in `missing_points`.

### Async Pattern

All agent methods that call OpenAI are `async`:
```python
# agents/analysis_agent.py
async def analyze(db: Session, job_offer: str) -> dict:
    # ... fetch profile blocks ...
    analysis = await analyze_offer(prompt)  # calls openai_service
    return analysis
```

Handlers invoke with `await`:
```python
# bot/handlers.py
async def handle_offer(update, context):
    analysis = await AnalysisAgent.analyze(db, offer_text)
```

### Database Session Management

All DB operations go through `application_service`. Sessions created in handlers, passed to agents:
```python
db = SessionLocal()
try:
    app = create_application(db, user_id, offer_text)  # service
    analysis = await AnalysisAgent.analyze(db, offer_text)  # agent uses session
finally:
    db.close()
```

### Template Rendering

Jinja2 templates in `app/templates/`:
- `cv.html` → professional CV layout
- `letter.html` → motivation letter
- `mail.txt` → plain text email

Context dict built in generation agent, passed to `render_*()`:
```python
context = {
    "candidate_name": "Akim Guentas",
    "job_title": positioning,
    "company": analysis["company"],
    "content": await generate_text(prompt),  # AI-generated content
    "ats_keywords": ", ".join(analysis["ats_keywords"]),
}
html = render_cv(context)
save_document(html, filepath)
```

## Development Commands

### Local Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Environment
cp .env.example .env
# edit .env with OPENAI_API_KEY, TELEGRAM_BOT_TOKEN, DATABASE_URL

# 3. Database
alembic upgrade head
python -m app.database.seed_profile

# 4. Run bot
python -m app.bot.telegram_bot

# 5. (Optional) Run FastAPI server
uvicorn app.main:app --reload
```

### Docker

```bash
cp .env.example .env
docker compose up --build
# Postgres + migrations + seed + bot automatically
```

### Database Migrations

```bash
# Auto-generate from models
alembic revision --autogenerate -m "Add new_field to applications"

# Apply
alembic upgrade head

# Rollback
alembic downgrade -1

# Check current version
alembic current
```

### Testing (Future)

```bash
pytest tests/
pytest tests/agents/test_analysis.py -v
pytest --cov=app tests/
```

## Common Tasks

### Add a New Agent

1. Create `app/agents/my_agent.py`
2. Define class with static async methods
3. Use services (OpenAI, DB, files) as needed
4. Example:
```python
class MyAgent:
    @staticmethod
    async def do_something(db: Session, data: str) -> dict:
        blocks = db.query(ProfileBlock).all()
        prompt = get_my_prompt(data, blocks)
        result = await generate_text(prompt)
        return {"result": result}
```
5. Call from handler: `result = await MyAgent.do_something(db, input_data)`

### Add a New Telegram Command

1. Edit `app/bot/handlers.py`
2. Add handler function:
```python
async def my_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Handler logic here
    await update.message.reply_text("Response")
```
3. Register in `app/bot/telegram_bot.py`:
```python
app.add_handler(CommandHandler("my_command", my_command))
```

### Add a Profile Block Programmatically

```python
from app.database.models import ProfileBlock, CategoryEnum, TruthLevelEnum
from app.database.db import SessionLocal

db = SessionLocal()
block = ProfileBlock(
    category=CategoryEnum.skill,
    title="New Skill",
    content="Description...",
    tags=["tag1", "tag2"],
    truth_level=TruthLevelEnum.verified,
    priority=8,
)
db.add(block)
db.commit()
```

### Generate Documents Manually

```python
from app.agents.generation_agent import GenerationAgent
from app.database.db import SessionLocal

db = SessionLocal()
analysis = {...}  # structured analysis JSON
docs = await GenerationAgent.generate_documents(
    db, app_id=1, analysis=analysis, positioning="Data Analyst BI"
)
# docs = {"cv": html, "letter": html, "mail": text}
```

### Check Profile Blocks

```python
from app.database.models import ProfileBlock
from app.database.db import SessionLocal

db = SessionLocal()
blocks = db.query(ProfileBlock).all()
for b in blocks:
    print(f"{b.title}: {b.category.value} (priority={b.priority})")
```

## Key Files & Their Purposes

| File | Purpose |
|------|---------|
| `app/config.py` | Config loading from env vars |
| `app/database/models.py` | SQLAlchemy models (5 tables) |
| `app/database/db.py` | Connection + SessionLocal |
| `app/database/seed_profile.py` | Idempotent profile initialization |
| `app/services/openai_service.py` | OpenAI wrapper (json_mode + text modes) |
| `app/services/scraping_service.py` | URL detection + trafilatura extraction |
| `app/services/document_service.py` | Jinja2 rendering + file saving |
| `app/services/application_service.py` | All DB CRUD operations |
| `app/agents/*` | Business logic (6 agents) |
| `app/prompts/*` | Reusable prompt builders |
| `app/templates/*.html` | Jinja2 templates for CV, letter, mail |
| `app/bot/handlers.py` | Telegram message/command handlers |
| `app/bot/telegram_bot.py` | Bot setup + polling |
| `alembic.ini` + `migrations/` | Database version control |
| `.env.example` | Template for env vars |
| `docker-compose.yml` | Local Postgres + app setup |
| `README.md` | User-facing documentation |
| `docs/ARCHITECTURE.md` | System design + data flows |
| `docs/ROADMAP.md` | V1-V5+ features + timeline |

## Data Models Quick Reference

### ProfileBlock
Candidate capabilities. Tags are arrays (JSON).
```python
id, category, title, content, tags, truth_level, priority, created_at, updated_at
```

### Application
Job application record.
```python
id, telegram_user_id, company, job_title, source_url, raw_offer, 
recommended_angle, match_score, status, created_at, updated_at
```

### JobAnalysis
Structured analysis (JSONB).
```python
id, application_id, analysis_json, missions, required_skills, soft_skills, 
ats_keywords, missing_points, strengths, created_at
```

### GeneratedDocument
Saved CV/letter/mail files.
```python
id, application_id, document_type, filename, content, file_path, created_at
```

### UserSession
User state tracking.
```python
id, telegram_user_id, last_application_id, state, session_data (JSONB), 
created_at, updated_at
```

## Design Decisions

### Why Agents Are Async

OpenAI calls block. Making agents async allows bot to handle multiple users without blocking.

### Why Prompts Are Separate Files

Prompts are easy to test, iterate, and version independently. Can A/B test or use different prompts per angle.

### Why Application Service Handles All DB

Keeps DB complexity in one place. Easier to add caching, transactions, logging later.

### Why No PDF in V1

Scope + complexity. Users can print to PDF locally. V3 adds Playwright + wkhtmltopdf.

### Why Profile Blocks Have Priority

Not all experience is equally relevant. Agents can weight by priority when selecting blocks.

### Why truth_level Exists

Distinguishes verified experience from in-progress projects. Quality agent uses this.

## Error Handling

- **URL extraction fails** → InputAgent returns (None, error dict) → Handler tells user to paste text
- **OpenAI invalid JSON** → AnalysisAgent logs + re-raises → Handler catches + shows user error
- **Invalid block IDs** → MatchingAgent filters silently (no invalid refs) → continues
- **Quality check fails** → Returns recommendation: "SAFE" / "REVIEW" / "REJECT"

Graceful degradation: most failures don't crash, just reduce quality or ask user to retry.

## Performance Notes

- **OpenAI calls**: ~2-5s each (main bottleneck)
  - Mitigation: async/await keeps UI responsive
  - Future: prompt caching, fine-tuning
  
- **URL extraction**: ~1-2s per URL
  - Timeout protection possible (add in V1.1)
  
- **Database**: profile_blocks table is small (~10 rows), queries are fast
  - Could add indexes later if user session table grows
  
- **File I/O**: Saves to local `/outputs`
  - Production: could stream to S3

## Testing Strategy

### Current (V1)
Manual testing via Telegram.

### V1.1+ Will Add
- Unit tests for agents (mock DB + OpenAI)
- Integration tests for services (real DB, mock OpenAI)
- Prompt consistency tests
- Quality check validation

Example test:
```python
@pytest.mark.asyncio
async def test_analysis_includes_missing_points():
    # Given a job requiring React (not in profile)
    # When analyzing
    # Then missing_points includes "React"
    pass
```

## Extensibility Points

### Adding a New Document Type
1. Add method to `GenerationAgent`
2. Add template in `app/templates/`
3. Update `DocumentTypeEnum` in models
4. Register in generation agent dispatch

### Adding a New Positioning Angle
1. Add to `VALID_ANGLES` list in `PositioningAgent`
2. Update prompt in `positioning_prompt.py`
3. Test with analysis that should trigger new angle

### Adding Web API Endpoints
1. Create route in `app/main.py`
2. Use `Depends(get_db)` for session injection
3. Call agents as needed
4. Return Pydantic schema

### Custom Profile Blocks
Agents already support arbitrary profile blocks. Just add via seed or API.

## Debugging Tips

### Check What Profile Blocks Exist
```python
python -c "
from app.database.db import SessionLocal
from app.database.models import ProfileBlock
db = SessionLocal()
for b in db.query(ProfileBlock).all():
    print(f'{b.title}: {b.content[:50]}...')
"
```

### Test OpenAI Directly
```python
import asyncio
from app.services.openai_service import analyze_offer
from app.prompts.analysis_prompt import get_analysis_prompt

prompt = get_analysis_prompt("...", [])
result = asyncio.run(analyze_offer(prompt))
print(result)
```

### Check Generated Files
Files saved to `outputs/` with pattern: `app_{application_id}_{document_type}.html`
```bash
ls -la outputs/
cat outputs/app_1_cv.html
```

### Database State
```bash
# Connect to DB
psql -h localhost -U jobapply -d job_apply_db

# Check tables
\dt

# Query applications
SELECT id, company, job_title, match_score FROM applications LIMIT 5;
```

### Telegram Logs
```bash
# Local run
python -m app.bot.telegram_bot  # see stdout logs

# Docker
docker compose logs -f app
```

## When to Use Which Tool

| Need | Use |
|------|-----|
| New agent logic | Create `app/agents/new_agent.py` |
| DB operations | Add to `application_service.py` (or create new service) |
| Telegram command | Add handler in `app/bot/handlers.py` |
| API endpoint | Add route in `app/main.py` |
| New prompt | Create in `app/prompts/` |
| Database schema change | Alembic: `alembic revision --autogenerate -m "..."` |
| New config var | Add to `.env.example` + `app/config.py` |

## Standards

### Code Style
- Type hints on all functions: `def foo(x: str) -> int:`
- Docstrings on modules + public functions (one line OK)
- No comments unless WHY is non-obvious
- Function names: descriptive, lowercase + underscores

### Commit Messages
Format: `type: description`
- `feat:` new feature
- `fix:` bug fix
- `refactor:` code restructure
- `chore:` non-feature (config, deps, etc)
- `docs:` documentation

Example: `feat: add quality check for generated documents`

### Database Changes
1. Modify model in `app/database/models.py`
2. Create migration: `alembic revision --autogenerate -m "..."`
3. Review generated migration file
4. Apply: `alembic upgrade head`

### Testing New Code
- Agents: test with real DB (use fixture that seeds profile)
- Services: test with mock DB + mock OpenAI
- Handlers: integration test with fake update/context

## Roadmap Context

- **V1** (current): MVP working, Telegram interface
- **V1.1**: Quality improvements + better error handling
- **V2**: Multi-user, advanced matching, profile customization
- **V3**: PDF generation, web dashboard
- **V4**: Elevia integration
- **V5+**: Fine-tuned models, advanced analytics

Current work should maintain clean separation so future layers (web, API) can reuse agents.

## Important Constraints

1. **IA never invents** — only uses profile blocks
2. **Telegram is an interface** — agents must be independent
3. **Database is source of truth** — all decisions based on DB state
4. **Async throughout** — no blocking I/O
5. **Quality comes first** — better to refuse than to hallucinate

## Questions?

See:
- `docs/ARCHITECTURE.md` — detailed system design + data flows
- `docs/ROADMAP.md` — features + timeline
- `README.md` — user-facing setup + usage
- Code comments (rare but targeted)

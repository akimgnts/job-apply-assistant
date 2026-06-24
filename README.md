# Job Apply Assistant

Assistant IA personnel de candidature, accessible via Telegram. Réduit drastiquement le temps passé à postuler en analysant les offres et générant des CV, lettres et mails adaptés.

## Features V1

- **Réception d'offre** : URL ou texte brut via Telegram
- **Extraction intelligente** : Scraping avec trafilatura (fallback texte brut)
- **Analyse structurée** : OpenAI analyse l'offre et le matching
- **Scoring** : Match sur 10 entre profil et offre
- **Positionnement** : Suggest optimal candidate angle
- **Génération** : CV HTML, lettre HTML, mail TXT
- **Validation humaine** : GO/CV/LETTRE/MAIL commands
- **Historique** : Toutes les candidatures sauvegardées en PostgreSQL

## Architecture

```
job-apply-assistant/
├── app/
│   ├── bot/                 # Telegram bot
│   ├── agents/              # IA agents (analysis, generation, matching, etc.)
│   ├── services/            # OpenAI, scraping, documents, application logic
│   ├── database/            # SQLAlchemy models, migrations
│   ├── schemas/             # Pydantic validation schemas
│   ├── prompts/             # IA prompts (modular, reusable)
│   ├── templates/           # Jinja2 HTML/TXT templates
│   └── config.py            # Configuration centralisée
├── migrations/              # Alembic migrations
├── outputs/                 # Generated documents
├── tests/                   # Unit tests
└── docs/                    # Architecture & roadmap
```

### Core Workflow

```
User sends offer
    ↓
InputAgent: detect URL/text
    ↓
AnalysisAgent: OpenAI analyzes offer + profile matching
    ↓
MatchingAgent: validate profile blocks + enrich analysis
    ↓
PositioningAgent: choose best positioning angle
    ↓
[Save to DB]
    ↓
User reviews summary (match score, strengths, missing points)
    ↓
User command: GO / CV / LETTRE / MAIL
    ↓
GenerationAgent: Generate documents from analysis + profile
    ↓
QualityAgent: Verify no invented claims
    ↓
[Save to DB + send via Telegram]
```

### Separation of Concerns

- **Agents** : Pure business logic, zero Telegram dependency
- **Services** : Infra integrations (OpenAI, DB, files)
- **Bot handlers** : Telegram interface (orchestrates agents + services)
- **Database** : Single source of truth, audit trail

## Installation

### Requirements

- Python 3.11+
- PostgreSQL 12+
- OpenAI API key
- Telegram Bot Token

### Local Setup

```bash
# Clone & navigate
cd job-apply-assistant

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or: venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt

# Setup environment
cp .env.example .env
# Edit .env with your API keys

# Initialize database
alembic upgrade head

# Seed profile blocks
python -m app.database.seed_profile

# Run bot
python -m app.bot.telegram_bot
```

### Docker Setup

```bash
cp .env.example .env
# Edit .env with your API keys
docker compose up --build
```

Database automatically migrated + seeded on startup.

## Database Setup

### Using External Database (Coolify, AWS RDS, etc.)

For connecting to a remote PostgreSQL database:

```bash
# Update .env with remote database URL
DATABASE_URL=postgresql://username:password@host:5432/database_name

# Run migrations
alembic upgrade head

# Seed profile
python -m app.database.seed_profile

# Start bot
python -m app.bot.telegram_bot
```

**Troubleshooting**: See [DATABASE_SETUP.md](DATABASE_SETUP.md) for configuration issues.

**For Coolify specifically**: See [COOLIFY_SETUP.md](COOLIFY_SETUP.md) for detailed setup steps and troubleshooting.

**Connection diagnostics**:
```bash
python coolify_test.py        # For Coolify-hosted databases
python test_db_connection.py  # For any PostgreSQL database
```

### Using Local PostgreSQL

```bash
# Ensure Docker is installed
docker compose up -d

# Apply migrations
alembic upgrade head

# Seed profile
python -m app.database.seed_profile

# Start bot
python -m app.bot.telegram_bot
```

Or use the smart startup script:
```bash
chmod +x run.sh
./run.sh
```

## Environment Variables

```env
OPENAI_API_KEY=sk-...              # OpenAI API key
OPENAI_MODEL=gpt-4o-mini          # OpenAI model
TELEGRAM_BOT_TOKEN=123:ABC...      # Telegram bot token
DATABASE_URL=postgresql://...      # PostgreSQL connection
APP_ENV=development                # development or production
OUTPUT_DIR=outputs                 # Where to save documents
LOG_LEVEL=INFO                     # Logging level
```

## Telegram Commands

### User Commands

- `/start` - Welcome message + instructions
- `/help` - Detailed help
- `/last` - Show last analyzed offer

## Telegram Troubleshooting

Use this when the bot starts but does not answer Telegram messages:

```bash
LOG_LEVEL=INFO python -m app.bot.telegram_bot
```

Then send `/start` and check the logs:

- `[telegram.update] user_id=... message=/start` confirms Telegram updates are reaching the process.
- `start_command.enter user_id=...` and `start_command.reply_sent user_id=...` confirm the `/start` handler ran and sent a reply.
- `[telegram.error] ...` is the application's runtime error path; it can report handler exceptions or polling/runtime failures.

Quick diagnosis:

- Missing `[telegram.update]`: investigate bot token, polling startup, or Telegram delivery.
- Present `[telegram.update]` but missing `start_command...`: investigate handler registration or filters.
- Present `start_command...` but no Telegram reply: inspect `[telegram.error]` output and downstream service failures.
- `[telegram.error] ... Conflict: terminated by other getUpdates request`: another bot instance is already polling this token.
- Verified in the startup smoke check for this repo: bot startup logs were emitted and the `409 Conflict` case above was observed; the `/start` flow itself was not exercised live in this session.

### Document Generation

After offer analysis, reply with:

- `GO` - Generate CV + letter + mail
- `CV` - CV only
- `LETTRE` - Letter only
- `MAIL` - Email only

## Database Schema

### profile_blocks

Candidate profile components.

```sql
id          | category (experience, skill, project, education, etc.)
title       | e.g. "Sidel — Marketing & Communication"
content     | Full description
tags        | JSON array (for filtering/searching)
truth_level | verified, project, in_progress, learning
priority    | Relevance order
```

### applications

Job applications.

```sql
id                  | Primary key
telegram_user_id    | User identifier
company             | Company name (extracted)
job_title           | Job title (extracted)
source_url          | If from URL
raw_offer           | Full offer text
recommended_angle   | Suggested positioning
match_score         | 0-10
status              | analyzed, generated, archived
```

### job_analyses

Structured analysis of offer.

```sql
id                      | Primary key
application_id          | FK to applications
analysis_json           | Full OpenAI response (JSONB)
missions, skills, etc.  | Extracted arrays
```

### generated_documents

Generated CV/letter/mail.

```sql
id              | Primary key
application_id  | FK to applications
document_type   | cv, letter, mail
filename        | Saved filename
content         | HTML/TXT content
file_path       | Disk location
```

### user_sessions

User state tracking.

```sql
id                  | Primary key
telegram_user_id    | FK (unique)
last_application_id | For quick access
state               | idle, waiting_for_command
session_data        | JSONB (extensible)
```

## Profile Seed

V1 includes default profile:

1. **Sidel** — Marketing & Communication / Data Reporting (experience)
2. **Elevia** — IA Matching Platform (project, in progress)
3. **Made By Curve** — Freelance Design (experience)
4. **MSc BI & Analytics** — Education
5. **Data Skills** — Analysis, Excel, Power BI, SQL, Python
6. **IA / Automation Skills** — Prompt engineering, workflows, OpenAI

Edit `seed_profile.py` to customize.

## AI Guarantees

**Rule: IA never invents.**

- Only uses what exists in `profile_blocks`
- Can reformulate, prioritize, adapt vocabulary
- Cannot create fictional experience
- Cannot exaggerate skill levels
- Missing critical skills → `missing_points`
- Quality agent double-checks generated documents

## Workflow Example

```
User: "https://linkedin.com/jobs/..."

Bot: "🔍 Analyse en cours..."

Bot: "🎯 Offre détectée: Data Analyst — Acme Corp
     💡 Angle recommandé: Data Analyst BI
     📊 Match: 7/10
     ✅ Points forts: SQL skills, Power BI, data analysis
     ⚠️ Points manquants: Tableau expertise
     
     Réponds: GO / CV / LETTRE / MAIL"

User: "GO"

Bot: "[generates & sends 3 files]"
```

## Limits V1

- No PDF generation (use Print to PDF)
- No OCR (text input only)
- No web dashboard
- Single user per bot instance (can extend)
- No auth (assumes trusted bot token)
- Simple scoring (extensible)

## Roadmap

### V2: Polish & Reliability
- Robust URL scraping (multiple backends)
- Template improvements
- Enhanced quality checks
- Error recovery

### V3: Advanced Features
- PDF generation (Playwright)
- Multi-user support
- User custom profiles
- Advanced matching scoring

### V4: Integration
- Web dashboard
- Analytics
- Integration with Elevia matching

### V5: AI Enhancements
- Fine-tuned models
- Cached profiles
- Reasoning/thinking tokens
- Custom positioning angles

## Testing

```bash
# Run tests
pytest tests/

# Run specific test
pytest tests/agents/test_analysis.py -v

# Coverage
pytest --cov=app tests/
```

## Development

### Add a New Agent

1. Create `app/agents/my_agent.py`
2. Define `MyAgent` class with static methods
3. Use services (OpenAI, DB, files)
4. Write prompts in `app/prompts/`
5. Add tests in `tests/agents/`

### Add a New Route

1. Edit `app/main.py` or create new router
2. Use dependency injection for DB: `db: Session = Depends(get_db)`
3. Call agents/services
4. Return Pydantic schema

### Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "description"

# Apply
alembic upgrade head

# Rollback
alembic downgrade -1
```

## Deployment

### Coolify

1. Create app from Docker image
2. Set env vars
3. Mount `/app/outputs` volume
4. Run migrations on startup
5. Set bot command: `python -m app.bot.telegram_bot`

### Heroku (if needed)

```bash
heroku create job-apply-assistant
heroku addons:create heroku-postgresql:hobby-dev
heroku config:set OPENAI_API_KEY=...
git push heroku main
```

## Troubleshooting

### Bot not responding
- Check `TELEGRAM_BOT_TOKEN` is valid
- Verify network connectivity
- Check logs: `docker compose logs app`

### Database migrations fail
- Ensure PostgreSQL is running
- Check `DATABASE_URL` format
- Run: `alembic current` to check version
- Clear migrations: `alembic downgrade base` then `upgrade head`

### OpenAI API errors
- Verify `OPENAI_API_KEY`
- Check rate limits / quota
- Try smaller model: `gpt-3.5-turbo`

### Documents too generic
- Adjust prompts in `app/prompts/`
- Add more profile blocks
- Increase `priority` for relevant blocks

## Contributing

- Code style: Black, Flake8
- Type hints on all functions
- Docstrings for modules & public functions
- Tests for new features
- Commit message: `type: description`

## License

MIT

## Contact

Built by Akim Guentas - akimguentas13@gmail.com

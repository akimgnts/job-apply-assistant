# Architecture Guide

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                      Telegram Bot Interface                      │
│                    (app/bot/telegram_bot.py)                    │
└──────────────────────────────┬──────────────────────────────────┘
                               │
        ┌──────────────────────┴──────────────────────┐
        │                                             │
        ↓                                             ↓
   ┌─────────────┐                            ┌──────────────┐
   │   Handlers  │                            │  Commands    │
   │ (input→cmd) │                            │ (GO/CV/etc)  │
   └──────┬──────┘                            └──────┬───────┘
        │                                           │
        └──────────────────────┬────────────────────┘
                               │
        ┌──────────────────────┴──────────────────────┐
        │                  Agents                    │
        │  (Pure business logic, no Telegram)       │
        ├──────────────────────────────────────────┤
        │ • InputAgent        (URL/text detection)  │
        │ • AnalysisAgent     (OpenAI analysis)     │
        │ • MatchingAgent     (Profile enrichment)  │
        │ • PositioningAgent  (Angle selection)     │
        │ • GenerationAgent   (Doc generation)      │
        │ • QualityAgent      (Verification)        │
        └──────────────────────┬────────────────────┘
        │
        └──────────────────────┬──────────────────────────────┐
        │                      │                              │
        ↓                      ↓                              ↓
    ┌──────────┐         ┌──────────┐                ┌──────────┐
    │ Services │         │ OpenAI   │                │ Database │
    │          │         │ Service  │                │          │
    ├──────────┤         └──────────┘         ┌──────┴──────┐
    │ • OpenAI │                             │ PostgreSQL  │
    │ • Scrape │                             │ (SQLAlchemy)│
    │ • Doc    │                             └─────────────┘
    │ • App    │
    └──────────┘
```

## Layer Responsibilities

### 1. Bot Layer (`app/bot/`)

**Entry point**: Telegram bot polling.

**Components**:
- `telegram_bot.py` : Setup + polling loop
- `handlers.py` : Message/command handlers

**Responsibilities**:
- Receive user input from Telegram
- Route to appropriate agent
- Format agent outputs for Telegram
- Send files/messages back to user
- Maintain user state (session)

**Constraints**:
- Zero business logic
- No direct DB queries (use service layer)
- All async, uses `update.message.reply_text()`

**Example flow**:
```python
async def handle_offer(update, context):
    user_id = str(update.effective_user.id)
    raw_input = update.message.text
    
    # InputAgent: pure logic, no Telegram dependency
    offer_text, metadata = InputAgent.process(raw_input)
    
    # AnalysisAgent: uses services, returns structured data
    analysis = await AnalysisAgent.analyze(db, offer_text)
    
    # Format & send back
    await update.message.reply_text(format_summary(analysis))
```

### 2. Agent Layer (`app/agents/`)

**Purpose**: Pure business logic, framework-independent.

**Agents**:

#### InputAgent
- Detects if text is URL or plain text
- Extracts content from URL using trafilatura
- Returns (offer_text, metadata)
- Falls back to plain text if extraction fails

#### AnalysisAgent
- Calls OpenAI with structured prompt
- Analyzes job offer + candidate profile
- Returns JSON: job details, required skills, match score, etc.
- **Rules**:
  - Uses ONLY profile_blocks from DB
  - Scores realistically
  - Lists missing points honestly

#### MatchingAgent
- Validates profile blocks referenced in analysis
- Enriches analysis with full block details
- Ensures no invalid block IDs
- Returns enhanced analysis

#### PositioningAgent
- Chooses best positioning angle
- Fixed list of 7 valid angles
- Calls OpenAI to decide
- Fallback to default if invalid

#### GenerationAgent
- Generates CV, letter, mail from analysis
- Uses Jinja2 templates
- Saves files to disk
- Stores in DB
- Async, one method per document type

#### QualityAgent
- Verifies generated documents don't invent
- Checks for skills not in profile
- Checks for experiences not in profile
- Flags generic/template language
- Returns quality report

### 3. Service Layer (`app/services/`)

**Purpose**: Infrastructure integrations.

#### OpenAI Service
- Wrapper around OpenAI API
- `call_openai(prompt, json_mode)` : Low-level call
- `analyze_offer(prompt)` : Structured JSON response
- `generate_text(prompt)` : Free-form text response

#### Scraping Service
- `is_url(text)` : Detect URL
- `extract_from_url(url)` : Trafilatura extraction
- `process_input(text)` : Combined input handling

#### Document Service
- `render_cv/letter/mail(context)` : Jinja2 rendering
- `save_document(content, path)` : File I/O
- `get_output_path(app_id, doc_type)` : Path generation

#### Application Service
- `create_application()` : New application record
- `save_analysis()` : Analysis JSONB storage
- `update_user_session()` : Session management
- `get_last_application()` : Retrieve user's last app
- All DB operations here

### 4. Database Layer (`app/database/`)

**Models** (`models.py`):
- `ProfileBlock` : Candidate capabilities
- `Application` : Job application record
- `JobAnalysis` : OpenAI analysis results
- `GeneratedDocument` : CV/letter/mail files
- `UserSession` : User state

**DB Connection** (`db.py`):
- SQLAlchemy engine + session factory
- Dependency: `get_db()` for FastAPI

**Migrations** (`migrations/`):
- Alembic version control
- Initial schema creation
- Version tracking

**Seed** (`seed_profile.py`):
- Loads default profile blocks
- Idempotent (checks if already seeded)

### 5. Prompt Layer (`app/prompts/`)

**Purpose**: Separate, reusable prompts.

- `analysis_prompt.py` : Job analysis + matching
- `positioning_prompt.py` : Angle selection
- `generation_prompt.py` : CV, letter, mail templates
- `quality_prompt.py` : Document verification

**Design**:
- Functions return prompt string
- Accept context (analysis, profile, etc.)
- Easy to test/iterate on
- Can be versioned separately

## Data Flow: Complete Example

### User sends offer

```
User: "Senior Data Analyst role..."
  ↓
Bot handler: handle_offer()
  ↓
InputAgent.process() → (offer_text, metadata)
  ↓
AnalysisAgent.analyze(db, offer_text)
  ├─ Fetches all profile_blocks from DB
  ├─ Builds analysis_prompt with profile
  ├─ Calls OpenAI
  └─ Returns analysis JSON: {job_title, skills, match_score, ...}
  ↓
MatchingAgent.enrich_analysis(analysis, db)
  ├─ Validates block IDs
  ├─ Ensures no invalid references
  └─ Returns enriched analysis
  ↓
ApplicationService.create_application(db, user_id, offer_text)
  └─ Saves raw offer, creates record
  ↓
ApplicationService.save_analysis(db, app_id, analysis)
  └─ Saves analysis JSON in DB
  ↓
PositioningAgent.choose_angle(analysis)
  ├─ Calls OpenAI with fixed angle list
  └─ Returns: "Data Analyst BI"
  ↓
Bot handler formats & sends summary
  └─ Shows match_score, strengths, missing, angle
```

### User commands "GO"

```
User: "GO"
  ↓
Bot handler: handle_command(update, "GO")
  ↓
ApplicationService.get_last_application(db, user_id)
  └─ Retrieves application + analysis
  ↓
GenerationAgent.generate_documents(db, app_id, analysis, "Data Analyst BI")
  ├─ generate_cv()
  │  ├─ MatchingAgent.get_selected_blocks()
  │  ├─ Calls OpenAI with cv_prompt
  │  ├─ Renders template with context
  │  ├─ Saves to disk
  │  └─ Stores in DB
  ├─ generate_letter()
  │  └─ Same flow, letter template
  └─ generate_mail()
     └─ Same flow, mail template
  ↓
ApplicationService.mark_application_as_generated(db, app_id)
  └─ Updates status to "generated"
  ↓
Bot handler sends 3 files to user
```

## Design Principles

### 1. Separation of Concerns

- **Agents** ≠ Telegram
- **Services** ≠ Business logic
- **Database** = Single source of truth
- **Prompts** = Reusable, testable

### 2. No Inventing

- IA reads profile_blocks
- Can only reference what exists
- Quality agent verifies
- missing_points tracks gaps

### 3. Testability

- Agents are pure functions (testable without DB)
- Services are injectable
- Prompts are standalone
- Handlers are integration tests

### 4. Extensibility

- Add new agents in `app/agents/`
- Add new services in `app/services/`
- Add new endpoints in `app/main.py`
- Database: add models + migration

### 5. Reliability

- Async everywhere (non-blocking)
- Graceful fallbacks (OpenAI error → fallback angle)
- DB transactions (all-or-nothing)
- Logging at agent boundaries

## Error Handling

```
URL extraction fails
  → InputAgent returns (None, {error: "url_extraction_failed"})
  → Handler tells user to paste text

OpenAI returns invalid JSON
  → AnalysisAgent logs + re-raises
  → Handler catches + shows error to user

Invalid block ID in analysis
  → MatchingAgent filters out
  → Continues with valid blocks

Quality check fails
  → QualityAgent returns recommendation: "REVIEW" or "REJECT"
  → Could add user confirmation step in V2
```

## Performance Considerations

- **OpenAI calls are slow**: ~2-5 seconds per call
  - Mitigated by async/await (non-blocking UI)
  - Can cache results later
  
- **Database queries**: Fast for profile_blocks (small table)
  - Could add indexes on telegram_user_id

- **File I/O**: Writes to /outputs locally
  - Can stream to S3 in production

- **Trafilatura extraction**: ~1-2 seconds per URL
  - Could add timeout + fallback

## Security

- No sensitive data in prompts (no PII)
- API keys in env vars (never in code)
- Database passwords in .env
- Bot token not logged
- User input validated (Pydantic schemas for FastAPI)

## Monitoring & Observability

- Logging at agent entry/exit
- Request logging in handlers
- Error logging with full traceback
- Database commit logs
- Could add:
  - Prometheus metrics (OpenAI latency)
  - Error tracking (Sentry)
  - Request tracing (OpenTelemetry)

## Future Extensions

### V2+: Web Dashboard
```
FastAPI routes:
- GET /applications/{id} → view app + analysis
- GET /documents/{id} → download CV/letter
- POST /profile/blocks → custom profile items
- GET /stats → application history
```

### V2+: Multi-User
```
User authentication layer:
- JWT or OAuth
- user_id = authenticated user
- User-specific profile customization
```

### V2+: Advanced Matching
```
New agents:
- ScoringAgent: custom scoring algorithm
- CoverLetterAgent: multi-section generation
- CVOptimizationAgent: ATS keyword enhancement
```

### V2+: Integration with Elevia
```
- Elevia matching API integration
- Bi-directional sync
- Shared profile canonicalization
```

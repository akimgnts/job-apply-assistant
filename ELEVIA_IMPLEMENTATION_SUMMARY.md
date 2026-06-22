# Elevia API Integration - Implementation Summary

## Objective
Integrate the Elevia API (Business France / VIE offers) into the Job Apply Assistant to provide:
1. A live, server-maintained source of job offers
2. Intelligent profile matching for better CV/letter generation
3. Enriched context for analysis agents without duplicating their logic

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                   Telegram Bot (handlers)               │
│  /search_offers  /catalog  /load_elevia_offer           │
│  /upload_profile /get_profile                           │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│  EleviaAgent (business logic layer)                     │
│  - health_check()                                       │
│  - search_offers() / get_catalog()                      │
│  - get_offer_with_context()                             │
│  - upload_profile_from_file() / get_user_profile()      │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│  EleviaGateway (orchestration layer)                    │
│  - Normalizes API responses to internal schemas         │
│  - Handles offer detail + profile + matching context    │
│  - Combines multiple API calls into single context      │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│  EleviaClient (HTTP wrapper)                            │
│  - health_check()                                       │
│  - search_offers() / get_offers_catalog()               │
│  - get_offer_detail() / get_profile()                   │
│  - upload_profile() / match_profile_with_offer()        │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│  Elevia API (https://api.elevia.dev)                    │
│  - GET /api/health                                      │
│  - POST /api/inbox (search with ranking)                │
│  - GET /api/offers/catalog (browse)                     │
│  - GET /api/offers/{id}/detail                          │
│  - POST /api/profile/parse-file (profile upload)        │
│  - GET /api/profiles/{id} (profile info)                │
│  - POST /api/v1/match (optional matching)               │
└─────────────────────────────────────────────────────────┘
```

## Key Components

### 1. HTTP Client (`app/services/elevia_client.py`)
- **Purpose**: Low-level HTTP wrapper around Elevia API
- **Methods**:
  - `health_check()` — Check API availability
  - `search_offers()` — Query offers with natural language
  - `get_offers_catalog()` — Browse paginated catalog
  - `get_offer_detail()` — Get detailed offer info
  - `upload_profile()` — Upload and parse user profile
  - `get_profile()` — Retrieve profile by ID
  - `match_profile_with_offer()` — Optional matching endpoint

### 2. Gateway (`app/services/elevia_gateway.py`)
- **Purpose**: Orchestration layer that combines multiple API calls
- **Responsibilities**:
  - Normalize raw API responses to internal schemas
  - Combine offer detail + profile + matching context
  - Handle errors gracefully (404s, network issues)
  - Provide single context object for downstream use

### 3. Agent (`app/agents/elevia_agent.py`)
- **Purpose**: Telegram-friendly interface to Elevia
- **Features**:
  - Lazy-loads gateway on demand
  - Checks Elevia enabled flag
  - Integrates with user sessions
  - Stores profile/offer IDs in user session data

### 4. Data Models (`app/schemas/elevia_offer.py`)
- **EleviaOfferCatalogEntry** — Brief offer summary
- **EleviaOfferDetail** — Full offer information
- **EleviaProfile** — User profile data
- **EleviaMatchContext** — Matching insights
- **EleviaIntegrationContext** — Complete offer context (combines all above)

### 5. User Service (`app/services/elevia_user_service.py`)
- **Purpose**: Persist Elevia profile IDs in user sessions
- **Methods**:
  - `get_elevia_profile_id()` — Retrieve stored profile ID
  - `set_elevia_profile_id()` — Store profile ID
  - `clear_elevia_profile_id()` — Clear if profile deleted
  - `get_last_elevia_offer_id()` / `set_last_elevia_offer_id()`

### 6. Enrichment Service (`app/services/offer_enrichment_service.py`)
- **Purpose**: Merge Elevia context into job analysis
- **Methods**:
  - `enrich_analysis_with_elevia_context()` — Add Elevia data to analysis
  - `get_offer_text_from_elevia_context()` — Convert to job offer text
  - `build_artifact_generation_context()` — Build context for document generation

### 7. Telegram Handlers (`app/bot/elevia_handlers.py`)
- **Commands**:
  - `/elevia_health` — Check API health
  - `/search_offers <query>` — Search with NLP
  - `/catalog [page]` — Browse catalog
  - `/load_elevia_offer <id>` — Load and analyze
  - `/upload_profile` — Upload user profile
  - `/get_profile` — View stored profile

## Data Flow

### Workflow 1: Search and Apply

```
User: /search_offers data scientist europe
     ↓
EleviaAgent.search_offers()
     ↓ (calls)
EleviaGateway.search_offers()
     ↓ (calls)
EleviaClient.search_offers()
     ↓ (HTTP)
Elevia API /api/inbox?query=...
     ↓ (returns List[EleviaOfferCatalogEntry])
Bot formats and shows to user
     ↓
User: /load_elevia_offer BF-12345
     ↓
EleviaAgent.get_offer_with_context(offer_id, profile_id)
     ↓ (calls)
EleviaGateway.get_offer_with_context()
     ↓ (calls)
EleviaClient.get_offer_detail() + EleviaClient.get_profile()
     ↓ (HTTP)
Elevia API /api/offers/BF-12345/detail + /api/profiles/xxx
     ↓ (returns EleviaIntegrationContext)
Bot creates Application record
     ↓
AnalysisAgent.analyze(offer_text)
     ↓
OfferEnrichmentService.enrich_analysis_with_elevia_context(analysis, context)
     ↓ (enriched analysis with Elevia data)
PositioningAgent.choose_angle(enriched_analysis)
     ↓
User sees analysis + buttons
```

### Workflow 2: Profile Management

```
User: /upload_profile
User: [Sends PDF]
     ↓
EleviaAgent.upload_profile_from_file()
     ↓ (calls)
EleviaGateway.parse_profile_from_file()
     ↓ (calls)
EleviaClient.upload_profile()
     ↓ (HTTP multipart)
Elevia API POST /api/profile/parse-file
     ↓ (returns EleviaProfile)
EleviaUserService.set_elevia_profile_id(db, user_id, profile_id)
     ↓ (stores in user_sessions.session_data)
Bot confirms: ✅ Profile stored! ID: elevia_profile_xxx
```

## Integration with Existing Pipeline

### Minimal Disruption
- **No changes** to AnalysisAgent, MatchingAgent, PositioningAgent, GenerationAgent
- **New data** injected via enrichment service
- **Backward compatible**: Works with URL/text inputs if Elevia disabled
- **Optional**: All Elevia features are optional, never required

### Key Integration Points

1. **InputAgent → Elevia**
   - InputAgent extracts text from URL/document
   - Elevia provides pre-extracted text via offer_detail.full_text
   - Both feed same job_offer_text format to AnalysisAgent

2. **AnalysisAgent ← Enrichment**
   - AnalysisAgent analyzes job requirements (unchanged)
   - OfferEnrichmentService adds Elevia context:
     ```python
     analysis["elevia_source"] = {...}
     analysis["elevia_offer_detail"] = {...}
     analysis["elevia_matching"] = {...}
     analysis["elevia_profile"] = {...}
     ```
   - Downstream agents see enriched analysis

3. **GenerationAgent ← Context**
   - GenerationAgent uses analysis + positioning (unchanged)
   - OfferEnrichmentService builds artifact_generation_context
   - Context includes Elevia-specific skills, location, matching insights
   - Templates can optionally use this context for better content

## Configuration

### Environment Variables
```bash
# Enable Elevia integration
ELEVIA_ENABLED=true

# Elevia API endpoint
ELEVIA_BASE_URL=https://api.elevia.dev

# API authentication token
ELEVIA_API_KEY=sk_live_xxxxxxxxxxxxxx
```

### Programmatic Setup
```python
from app.config import config
from app.agents.elevia_agent import EleviaAgent

# Check if enabled
if config.ELEVIA_ENABLED:
    is_healthy = await EleviaAgent.health_check()
```

## Error Handling

### Graceful Degradation

| Scenario | Behavior |
|----------|----------|
| ELEVIA_ENABLED=false | All Elevia commands return "disabled" message |
| API unreachable | Health check returns False, operations fail gracefully |
| Offer not found | 404 → User told "offer not found" |
| Profile not found (404) | Cache cleared, matching skipped, workflow continues |
| Profile upload fails | User shown error, can retry |
| Matching fails | Used anyway, just skip matching insights |
| Network timeout | Operation fails with timeout message |

### Key Characteristics
- **No silent failures**: All errors reported to user
- **No cascade failures**: One Elevia failure doesn't break whole workflow
- **User-facing messages**: Clear, actionable error descriptions
- **Logging**: All errors logged for debugging

## Testing Strategy

### Unit Tests
```python
# Test Elevia client
async def test_elevia_client_health():
    client = EleviaClient("https://api.elevia.dev", "key")
    assert isinstance(await client.health_check(), bool)

# Test gateway normalization
async def test_elevia_gateway_normalizes_offer():
    gateway = EleviaGateway(mock_client)
    offers = await gateway.search_offers("data")
    assert all(isinstance(o, EleviaOfferCatalogEntry) for o in offers)

# Test agent integration
async def test_elevia_agent_context():
    context = await EleviaAgent.get_offer_with_context(
        offer_id="BF-123",
        db=test_db,
        telegram_user_id="user123"
    )
    assert isinstance(context, EleviaIntegrationContext)
    assert context.offer_detail is not None
```

### Integration Tests
```python
# End-to-end offer workflow
async def test_elevia_offer_analysis():
    # Search
    offers = await EleviaAgent.search_offers("data scientist")
    assert len(offers) > 0
    
    # Load
    offer_id = offers[0].offer_id
    context = await EleviaAgent.get_offer_with_context(
        offer_id, db, user_id
    )
    
    # Analyze
    offer_text = context.get_job_offer_text()
    analysis = await AnalysisAgent.analyze(db, offer_text)
    
    # Enrich
    enriched = OfferEnrichmentService.enrich_analysis_with_elevia_context(
        analysis, context
    )
    
    assert "elevia_source" in enriched
    assert enriched["elevia_matching"]["match_score"] >= 0
```

## Documentation

- **docs/ELEVIA_INTEGRATION.md** — Full user guide with examples
- **This file** — Implementation details and architecture
- **Code comments** — Sparse but targeted (only WHY, not WHAT)

## Files Added/Modified

### New Files (1581 lines)
- `app/services/elevia_client.py` — 163 lines
- `app/services/elevia_gateway.py` — 168 lines
- `app/services/elevia_user_service.py` — 93 lines
- `app/services/offer_enrichment_service.py` — 73 lines
- `app/agents/elevia_agent.py` — 143 lines
- `app/bot/elevia_handlers.py` — 307 lines
- `app/schemas/elevia_offer.py` — 143 lines
- `docs/ELEVIA_INTEGRATION.md` — 489 lines

### Modified Files
- `app/config/__init__.py` — +3 lines (ELEVIA config)
- `app/bot/telegram_bot.py` — +13 lines (Elevia command handlers)
- `.env.example` — +4 lines (ELEVIA env vars)

## Future Enhancements

1. **V1.1**: Add caching for offer searches
2. **V2**: Advanced filtering (location, salary, contract type)
3. **V3**: Persistent offer collections / favorites
4. **V4**: Auto-refresh catalog on interval
5. **V5**: Elevia integration for all job sources (not just manual load)

## Deployment Checklist

- [ ] Set `ELEVIA_ENABLED=true` in production
- [ ] Configure `ELEVIA_API_KEY` with valid token
- [ ] Verify `ELEVIA_BASE_URL` points to correct Elevia instance
- [ ] Test `/elevia_health` command
- [ ] Test `/search_offers` with sample query
- [ ] Test `/upload_profile` with test file
- [ ] Test `/load_elevia_offer` with test offer ID
- [ ] Monitor logs for Elevia errors
- [ ] Verify enriched analyses include Elevia context

## Support & Debugging

### Check Elevia Health
```
/elevia_health
→ ✅ Elevia API is available!
```

### Verify Configuration
```python
from app.config import config
print(f"ELEVIA_ENABLED: {config.ELEVIA_ENABLED}")
print(f"ELEVIA_BASE_URL: {config.ELEVIA_BASE_URL}")
```

### Test API Connection
```python
from app.agents.elevia_agent import EleviaAgent

is_healthy = await EleviaAgent.health_check()
print(f"API Health: {is_healthy}")
```

### Monitor Logs
```bash
# Watch for Elevia errors
grep "elevia" /var/log/app.log
grep -i "error" /var/log/app.log | grep -i elevia
```

## See Also

- `CLAUDE.md` — Project guidelines and architecture
- `docs/ARCHITECTURE.md` — System design and data flows
- `README.md` — User-facing documentation
- `docs/ROADMAP.md` — Feature timeline (V1-V5)

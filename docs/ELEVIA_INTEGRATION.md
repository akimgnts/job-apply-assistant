# Elevia Integration Guide

This document describes the integration of the Job Apply Assistant with Elevia API for enriched job offers and profile matching.

## Overview

The Elevia integration adds a new source of job offers to the Job Apply Assistant. Instead of just scraping URLs or parsing text, users can now:

1. Search for job offers using natural language
2. Browse curated job catalogs from Business France / VIE programs
3. Get detailed offer information with automatic profiling
4. Receive intelligent matching between their profile and offers
5. Generate tailored CV, letters, and emails with enriched context

## Architecture

```
Telegram Bot
  ↓
Elevia Agent (business logic layer)
  ↓
Elevia Gateway (orchestration layer)
  ↓
Elevia Client (HTTP API wrapper)
  ↓
Elevia API
```

## Configuration

### Enable Elevia

Set these environment variables:

```bash
ELEVIA_ENABLED=true
ELEVIA_BASE_URL=https://api.elevia.dev
ELEVIA_API_KEY=your_api_key_here
```

### Example `.env`

```env
# Elevia API Integration
ELEVIA_ENABLED=true
ELEVIA_BASE_URL=https://api.elevia.dev
ELEVIA_API_KEY=sk_live_xxxxxxxxxxxx
```

## Telegram Commands

### Elevia-Specific Commands

#### `/elevia_health`
Check if Elevia API is available.

```
/elevia_health
→ ✅ Elevia API is available!
```

#### `/search_offers <query>`
Search for job offers with natural language.

```
/search_offers data scientist Spain
/search_offers business analyst France
/search_offers engineer germany
→ 📋 Found 10 offers for: "data scientist Spain"
1. Senior Data Scientist
   Company: Acme Corp
   Location: Madrid, Spain
   ID: `BF-12345`
```

#### `/catalog [page]`
Browse the job offers catalog (paginated).

```
/catalog
/catalog 20
→ 📋 Catalog (page 1)
```

#### `/load_elevia_offer <offer_id>`
Load and analyze a specific Elevia offer.

```
/load_elevia_offer BF-12345
→ 🔍 Analyzing...
→ ✅ Analysis complete with Elevia context
```

#### `/upload_profile`
Upload and parse a profile file (PDF, Word) to Elevia.

```
/upload_profile
[Send a file]
→ ✅ Profile uploaded and analyzed!
ID: `elevia_profile_xxx`
```

#### `/get_profile`
View your stored Elevia profile information.

```
/get_profile
→ 👤 Your Elevia Profile
Name: John Doe
Email: john@example.com
Location: Paris
Skills: Python, SQL, Data Science, ...
```

## Workflow Examples

### Example 1: Search and Apply

```
User: /search_offers data scientist Europe
Bot: 📋 Found 10 offers
     1. Senior Data Scientist - TechCorp - Berlin
     ID: BF-12345

User: /load_elevia_offer BF-12345
Bot: ✅ Offer analyzed
     Match Score: 8/10
     Best positioning: Data Science Lead
     [offer_extracted_menu]

User: GO
Bot: ✅ Generated CV, Letter, Mail
     [send documents]
```

### Example 2: Profile Upload and Matching

```
User: /upload_profile
      [Sends CV PDF]
Bot: ✅ Profile uploaded!
     ID: elevia_profile_abc123

User: /search_offers backend engineer
Bot: 📋 Found 5 offers

User: /load_elevia_offer BF-67890
Bot: ✅ Offer loaded
     Match Score: 9/10 (using your profile)
     Matching Skills: Python, Docker, REST APIs
     Missing: Kubernetes, GraphQL
```

## Data Models

### EleviaIntegrationContext

The complete context object returned for an offer:

```python
{
    "source": "elevia",
    "source_offer_id": "BF-12345",
    "source_type": "business_france",
    "offer_catalog_entry": {
        "offer_id": "BF-12345",
        "title": "Senior Data Scientist",
        "company": "TechCorp",
        "location": "Berlin, Germany",
        "description": "...",
        "contract_type": "CDI",
        "mission_duration": "Permanent"
    },
    "offer_detail": {
        "offer_id": "BF-12345",
        "title": "Senior Data Scientist",
        "company": "TechCorp",
        "location": "Berlin, Germany",
        "description": "...",
        "full_text": "...",
        "contract_type": "CDI",
        "mission_duration": "Permanent",
        "required_skills": ["Python", "ML", "SQL"],
        "soft_skills": ["Communication", "Leadership"],
        "ats_keywords": ["Machine Learning", "Analytics"],
        "salary_range": {"min": 60000, "max": 90000}
    },
    "profile": {
        "profile_id": "elevia_profile_xxx",
        "name": "John Doe",
        "email": "john@example.com",
        "skills": ["Python", "SQL", "ML", "Spark"],
        "experience": [...],
        "education": [...]
    },
    "matching_context": {
        "match_score": 8.5,
        "matching_skills": ["Python", "SQL", "ML"],
        "missing_skills": ["Kubernetes"],
        "strengths": ["Strong ML background"],
        "recommendations": ["Highlight data projects"]
    },
    "artifact_generation_context": {
        "job_title": "Senior Data Scientist",
        "company": "TechCorp",
        "positioning": "Data Science Lead",
        "required_skills": ["Python", "ML", "SQL"],
        "matching_insights": {...}
    }
}
```

## Integration with Existing Pipeline

### Analysis Enrichment

When an Elevia offer is loaded:

1. **InputAgent** → Extracts text from Elevia offer detail
2. **AnalysisAgent** → Analyzes job requirements (same as before)
3. **MatchingAgent** → Validates against local profile (same as before)
4. **OfferEnrichmentService** → Merges Elevia context:
   - Adds Elevia-specific skills and keywords
   - Includes matching insights from Elevia
   - Enriches with profile information
5. **PositioningAgent** → Chooses best angle (same as before)
6. **GenerationAgent** → Generates documents with enriched context

### Database Storage

- **Application** table stores reference to Elevia offer
- **JobAnalysis** table includes Elevia context in `analysis_json`
- **UserSession** table caches `elevia_profile_id` and `last_elevia_offer_id`

## Service Layer Architecture

### EleviaClient
Low-level HTTP client for Elevia API endpoints.

```python
client = EleviaClient(
    base_url="https://api.elevia.dev",
    api_key="sk_live_xxx"
)

offers = await client.search_offers(query="data scientist")
offer = await client.get_offer_detail("BF-12345")
profile = await client.get_profile("elevia_profile_xxx")
```

### EleviaGateway
Business logic layer for offer and profile management.

```python
gateway = EleviaGateway(client)

offers = await gateway.search_offers(query="data scientist")
context = await gateway.get_offer_with_context(
    offer_id="BF-12345",
    profile_id="elevia_profile_xxx"
)
```

### EleviaAgent
Telegram-friendly agent interface.

```python
context = await EleviaAgent.get_offer_with_context(
    offer_id="BF-12345",
    db=db,
    telegram_user_id="123456"
)
```

### EleviaUserService
User profile persistence.

```python
# Store profile ID
EleviaUserService.set_elevia_profile_id(db, user_id, profile_id)

# Retrieve profile ID
profile_id = EleviaUserService.get_elevia_profile_id(db, user_id)

# Clear if profile not found (404)
EleviaUserService.clear_elevia_profile_id(db, user_id)
```

## Error Handling

### Graceful Degradation

- **Elevia disabled**: Falls back to existing URL/text workflow
- **Elevia API unavailable**: User gets clear error message
- **Profile not found (404)**: Clears local cache, continues without matching
- **Profile upload fails**: User informed, can retry
- **Offer not found**: User informed with specific error

## Testing Elevia Integration

### Unit Tests

```python
# Test Elevia client
async def test_elevia_search():
    client = EleviaClient("https://api.elevia.dev", "test_key")
    offers = await client.search_offers("data scientist")
    assert len(offers) > 0

# Test gateway
async def test_elevia_gateway_normalize():
    gateway = EleviaGateway(client)
    offers = await gateway.search_offers("data scientist")
    assert all(isinstance(o, EleviaOfferCatalogEntry) for o in offers)

# Test agent
async def test_elevia_agent_health():
    is_healthy = await EleviaAgent.health_check()
    assert isinstance(is_healthy, bool)
```

### Integration Tests

```python
# Test end-to-end workflow
async def test_elevia_offer_workflow():
    # Search
    offers = await EleviaAgent.search_offers("data scientist")
    assert len(offers) > 0
    
    # Load offer
    offer_id = offers[0].offer_id
    context = await EleviaAgent.get_offer_with_context(
        offer_id,
        db=test_db,
        telegram_user_id="test_user"
    )
    assert context.offer_detail is not None
    
    # Analyze with enrichment
    offer_text = context.get_job_offer_text()
    analysis = await AnalysisAgent.analyze(db, offer_text)
    enriched = OfferEnrichmentService.enrich_analysis_with_elevia_context(
        analysis,
        context
    )
    assert "elevia_source" in enriched
```

## Future Enhancements

1. **V2**: Cached offer searches and filtering
2. **V3**: Advanced matching with skill weights
3. **V4**: Elevia integration for all job sources
4. **V5**: A/B testing different positioning strategies per Elevia source

## Support

For issues with Elevia integration:

1. Check `ELEVIA_ENABLED=true` in `.env`
2. Verify `ELEVIA_API_KEY` is valid
3. Run `/elevia_health` to test connectivity
4. Check logs for detailed error messages
5. Ensure profile has been uploaded before matching

## See Also

- `docs/ARCHITECTURE.md` — System architecture
- `app/services/elevia_client.py` — HTTP client implementation
- `app/services/elevia_gateway.py` — Orchestration layer
- `app/agents/elevia_agent.py` — Telegram interface
- `app/bot/elevia_handlers.py` — Telegram command handlers

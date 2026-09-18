# ScrapeGraphAI Lead Discovery Provider (Phase 5B)

Isolated worker for discovering public contacts using ScrapeGraphAI Open Source.

## Architecture

**Why isolated?** ScrapeGraphAI has historically caused LangChain dependency conflicts in this project. Isolation prevents breaking the main application environment.

```
Job Market Radar (main app)
  └─ Phase 5: LeadDiscoveryService
       ↑
       ├─ (verification, normalization, persistence)
       │
  workers/scrapegraph/discover_leads.py
       └─ ScrapeGraphAI (discovery only)
```

## Setup

```bash
# Create isolated virtual environment
cd workers/scrapegraph
python3 -m venv .venv
source .venv/bin/activate

# Install ScrapeGraphAI with dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium
```

## Usage

### Manual CLI Test

```bash
source workers/scrapegraph/.venv/bin/activate

python workers/scrapegraph/discover_leads.py \
  --company "Sidel" \
  --website "https://www.sidel.com" \
  --max-contacts 3 \
  --output /tmp/sidel_candidates.json
```

### Programmatic Usage (from main app)

```python
import sys
import json
from pathlib import Path
from workers.scrapegraph.discover_leads import discover_contacts_for_company

# Discover
result = discover_contacts_for_company(
    company_name="Sidel",
    company_website="https://www.sidel.com",
    max_contacts=3
)

# Pass to LeadDiscoveryService
from app.services.lead_discovery_service import discover_and_verify_contacts
from app.database.db import SessionLocal

db = SessionLocal()
try:
    candidates = [c.model_dump() for c in result.candidates]
    verified = discover_and_verify_contacts(
        db=db,
        company_id=sidel_company_id,
        candidate_contacts=candidates,
        max_contacts=3
    )
finally:
    db.close()
```

## Configuration

Uses existing project environment variables:

- `OPENAI_API_KEY` – (required) reused from main app config
- `OPENAI_MODEL` – (optional) defaults to gpt-4o-mini

No separate `SGAI_API_KEY` needed. The open-source ScrapeGraphAI uses your OpenAI account.

## Discovery Output

Raw candidates returned by ScrapeGraphAI:

```json
{
  "contact_name": "Jane Doe",
  "role_raw": "Talent Acquisition Manager",
  "company": "Sidel",
  "source_url": "https://sidel.com/careers",
  "linkedin_url": null,
  "email": null,
  "evidence_text": "Jane Doe leads recruiting for Data & AI roles"
}
```

**Important:** These are CANDIDATES, not verified contacts. LeadDiscoveryService:
- Normalizes roles
- Calculates relevance
- Verifies sources
- Deduplicates
- Persists only HIGH/MEDIUM relevance contacts

## Data Quality

ScrapeGraphAI uses LLM-based extraction → **no invented data guarantee**.

Enforced rules:

- ✅ `source_url` is MANDATORY (verification provenance)
- ✅ Email is null unless publicly listed (NO guessing)
- ✅ LinkedIn URL must look like a real LinkedIn profile
- ✅ Name and role must be reasonable length
- ✅ No duplicate candidates from same source
- ✅ Deduplication happens in Phase 5, not here

## Limits

- Max 3 contacts per discovery run (configurable)
- Max 3 companies per radar cycle (enforced by Phase 4)

## Errors

Non-critical errors are logged but don't crash the full run:

- Missing careers page
- Login wall
- CAPTCHA
- Timeout
- Malformed JSON from LLM

Candidates from successful sources are returned even if others fail.

## Dependencies

Isolated in `workers/scrapegraph/requirements.txt`:

- scrapegraphai ≥ 1.12.0
- openai ≥ 1.3.0 (reuses main app's key)
- playwright ≥ 1.45.0 (browser automation)
- pydantic ≥ 2.0.0 (validation)

## Verification Statuses

ScrapeGraphAI extracts candidates with `verification_status="PARTIAL"` or `"VERIFIED"` depending on source confidence.

Phase 5 LeadDiscoveryService decides final status based on source_url credibility.

## Known Limitations

1. **Authenticated data:** Cannot access private LinkedIn profiles, Glassdoor reviews, or hidden resumes.
2. **Login walls:** Sites behind login/CAPTCHA are skipped gracefully.
3. **Rate limits:** LLM-based scraping respects OpenAI API limits.
4. **JavaScript rendering:** Playwright handles, but some SPAs may be incomplete.

## Testing

See `tests/test_phase5b_scrapegraph.py` for unit tests (mocked ScrapeGraphAI).

Live tests use actual Sidel company data.

## Future Enhancements

- [ ] Parallel discovery for multiple companies
- [ ] Cache recent discovery results
- [ ] LinkedIn Recruiter integration (if API access granted)
- [ ] Result deduplication across discovery runs
- [ ] Monitoring/alerting for discovery quality

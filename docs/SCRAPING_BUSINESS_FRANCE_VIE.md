# Business France VIE Scraping

## Overview

**Adapter**: `BusinessFranceVieAdapter`
**Source**: https://mon-vie-via.businessfrance.fr/
**API**: https://civiweb-api-prd.azurewebsites.net/api/Offers/search
**Type**: REST POST (JSON)
**Auth**: x-api-key header
**Pagination**: 100 per page, unlimited pages

## Setup

### 1. Get API Key

Option A: Corporate network or existing client
- Request from Business France ([contact page](https://mon-vie-via.businessfrance.fr/))

Option B: Reverse-engineer from browser
- Open https://mon-vie-via.businessfrance.fr/
- F12 → Network tab
- Reload page
- Find POST to `/api/Offers/search`
- Copy `x-api-key` header value

### 2. Configure .env

```bash
# .env
BUSINESS_FRANCE_VIE_API_KEY=<paste-key-here>
```

Do NOT commit `.env` to git.

## Usage

### Single Run

```python
import asyncio
from app.services.business_france_vie_adapter import BusinessFranceVieAdapter

async def ingest():
    adapter = BusinessFranceVieAdapter()
    
    # Discover max 500 jobs (pagination auto)
    discovered = await adapter.discover_jobs({"max_per_company": 500})
    print(f"Found: {len(discovered)} jobs")
    
    # Extract details from each
    for job_url in discovered[:5]:
        extracted = await adapter.extract_job(job_url)
        normalized = await adapter.normalize_job(extracted)
        print(f"  {normalized.job_title} @ {normalized.company_name}")
    
    await adapter.close()

asyncio.run(ingest())
```

### Batch Ingestion

```bash
python3 scripts/ingest_all_ats.py
```

Ingest order:
1. Qonto/Lever (50 jobs max)
2. Stripe/Greenhouse (50 jobs max)
3. Notion/Ashby (50 jobs max)
4. Business France VIE (500 jobs max)

Registry: `app/database/ats_registry.json`

## API Details

### Endpoint

```
POST https://civiweb-api-prd.azurewebsites.net/api/Offers/search
```

### Request Payload

```json
{
  "limit": 100,
  "skip": 0,
  "query": null,
  "teletravail": ["0"],
  "porteEnv": ["0"],
  "activitySectorId": [],
  "companiesSizes": [],
  "countriesIds": [],
  "entreprisesIds": [0],
  "geographicZones": [],
  "missionStartDate": null,
  "missionsDurations": [],
  "missionsTypesIds": [],
  "specializationsIds": [],
  "studiesLevelId": []
}
```

**Parameters**:
- `limit`: Jobs per page (100 max)
- `skip`: Pagination offset
- `query`: Free-text search (null = all)
- `teletravail`: ["0"] = all, ["1"] = remote only
- `porteEnv`: ["0"] = all, others = filters
- `*Id`: Arrays of filter IDs

### Response

```json
{
  "result": [
    {
      "id": 245626,
      "missionTitle": "Responsable d'Agence (H/F)",
      "organizationName": "MAESTRIA RECRUTEMENTS",
      "cityName": "MORONI",
      "missionDuration": 12,
      "missionType": "VIE",
      "contactName": "John Doe",
      "contactEmail": "john@example.com",
      ...
    }
  ]
}
```

**Key Fields**:
- `id`: Unique offer ID
- `missionTitle`: Job title
- `organizationName`: Company
- `cityName`: Location
- `missionDuration`: Months
- `missionType`: Always "VIE"
- `contactName`: Hiring contact name
- `contactEmail`: Hiring contact email

## Pagination

Adapter auto-paginates:
```python
# Discover first 500 (spans 5 pages × 100)
discovered = await adapter.discover_jobs({"max_per_company": 500})
```

Loop:
1. POST skip=0, limit=100 → get 100 jobs
2. If < 100 returned → end
3. Else skip += 100, repeat

## Data Schema

### JobOffer (normalized)

```python
{
  "job_title": "Responsable d'Agence (H/F)",
  "company_name": "MAESTRIA RECRUTEMENTS",
  "job_url": "https://mon-vie-via.businessfrance.fr/offre/245626",
  "source": "business_france_vie",
  "location": "MORONI",
  "contract_type": "VIE",
  "external_job_id": "245626",
  "raw_text": "Company: ...\nDuration: 12 months\nLocation: ...",
  "description": null
}
```

## Deduplication

**Keys** (checked in order):
1. `source + external_job_id` → skip if exists
2. `job_url` → skip if exists
3. Fingerprint: `sha256(company|title|location)` → skip if seen in batch

## Export

```bash
# After ingestion, export to CSV
python3 << 'EOF'
import csv
from app.database.db import SessionLocal
from app.database.models import JobOffer

db = SessionLocal()
jobs = db.query(JobOffer).filter(JobOffer.source == "business_france_vie").all()

with open("bfvie_export.csv", "w") as f:
    w = csv.writer(f)
    w.writerow(["id", "title", "company", "location", "duration", "url"])
    for job in jobs:
        w.writerow([job.id, job.job_title, job.raw_text, job.location, job.job_url])

db.close()
EOF
```

Result: `exports/ats_job_offers_live.csv`

## Troubleshooting

### API Key not set

```
ERROR    app.services.business_france_vie_adapter:business_france_vie_adapter.py:XX BUSINESS_FRANCE_VIE_API_KEY not set
```

Fix:
```bash
echo "BUSINESS_FRANCE_VIE_API_KEY=<key>" >> .env
```

### 404 / 401

```
business_france_vie returned 401
```

- Key expired or invalid → request new key
- API endpoint changed → check current URL in browser

### Pagination stops at 100

Adapter stops if < 100 returned (last page). Normal behavior.

## Performance

- **Discovery**: ~2-3s per page (10 pages = 30s for 1000 jobs)
- **Extraction**: Metadata-only, no HTML parsing (fast)
- **Normalization**: Instant
- **DB insert**: Batch commit, fast

**Total for 500 jobs**: ~5-10 seconds

## Next Steps

### Capture Leads

Extract `contactName` + `contactEmail` from API response:

```python
offer = data["result"][0]
contact_name = offer.get("contactName")
contact_email = offer.get("contactEmail")
```

Store as structured leads (separate table).

### Track History

Add to `JobOffer`:
- `first_seen_at`: When offer first appears
- `last_seen_at`: When offer last seen
- `closed_at`: When offer disappears

Detect hiring acceleration (spike in open positions).

### Filter & Match

Current: all 500 jobs
Future:
- Filter by country/city
- Filter by sector (activitySectorId)
- Match against candidate profile

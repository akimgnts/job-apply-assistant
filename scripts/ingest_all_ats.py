#!/usr/bin/env python3
"""Ingest all ATS companies from registry."""

import asyncio
import sys
import json
from datetime import datetime
from pathlib import Path

sys.path.insert(0, "/Users/akimguentas/job-apply-assistant")

from app.services.lever_adapter import LeverAdapter
from app.services.greenhouse_adapter import GreenhouseAdapter
from app.services.ashby_adapter import AshbyAdapter
from app.services.business_france_vie_adapter import BusinessFranceVieAdapter
from app.database.db import SessionLocal
from app.database.models import JobOffer
from hashlib import sha256
from sqlalchemy import func

REGISTRY_PATH = Path("/Users/akimguentas/job-apply-assistant/app/database/ats_registry.json")

async def ingest_ats(ats_type, company_slug, max_per=50):
    """Ingest single ATS company."""
    if ats_type == "lever":
        adapter = LeverAdapter()
        discovered = await adapter.discover_jobs({"company_handles": [company_slug], "max_per_company": max_per})
    elif ats_type == "greenhouse":
        adapter = GreenhouseAdapter()
        discovered = await adapter.discover_jobs({"company_slugs": [company_slug], "max_per_company": max_per})
    elif ats_type == "ashby":
        adapter = AshbyAdapter()
        discovered = await adapter.discover_jobs({"company_slugs": [company_slug], "max_per_company": max_per})
    elif ats_type == "business_france_vie":
        adapter = BusinessFranceVieAdapter()
        discovered = await adapter.discover_jobs({"max_per_company": max_per})
    else:
        raise ValueError(f"Unknown ATS: {ats_type}")

    all_offers = []
    for url_obj in discovered:
        extracted = await adapter.extract_job(url_obj)
        normalized = await adapter.normalize_job(extracted)
        all_offers.append(normalized)

    await adapter.close()
    return discovered, all_offers

def main():
    print("=" * 80)
    print("ATS INGESTION — ALL COMPANIES FROM REGISTRY")
    print("=" * 80)

    with open(REGISTRY_PATH) as f:
        registry = json.load(f)

    db = SessionLocal()
    total_before = db.query(JobOffer).count()

    results = {}
    for company in registry["companies"]:
        if not company["enabled"]:
            continue

        name = company["company_name"]
        ats = company["ats_type"]
        slug = company["company_slug"]

        print(f"\n{name} ({ats})...")
        try:
            discovered, all_offers = asyncio.run(ingest_ats(ats, slug))
            print(f"  Discovered: {len(discovered)}")
            print(f"  Extracted: {len(all_offers)}")

            created = 0
            duplicates = 0
            seen_fps = set()

            for offer in all_offers:
                fp = sha256(f"{offer.company_name}|{offer.job_title}|{offer.location}".encode()).hexdigest()

                if fp in seen_fps:
                    duplicates += 1
                    continue
                seen_fps.add(fp)

                existing = db.query(JobOffer).filter(JobOffer.job_url == offer.job_url).first()
                if existing:
                    duplicates += 1
                    continue

                raw = f"Company: {offer.company_name}\nLocation: {offer.location or 'N/A'}\nID: {offer.external_job_id or 'N/A'}"
                job = JobOffer(
                    company_id=1,
                    job_title=offer.job_title,
                    job_url=offer.job_url,
                    source=offer.source,
                    raw_text=raw,
                    status="active",
                )
                db.add(job)
                db.flush()
                created += 1

            db.commit()
            results[name] = {"created": created, "duplicates": duplicates}
            print(f"  Created: {created}, Duplicates: {duplicates}")

        except Exception as e:
            print(f"  ERROR: {e}")
            results[name] = {"error": str(e)}

    total_after = db.query(JobOffer).count()

    print(f"\n{'=' * 80}")
    print(f"SUMMARY")
    print(f"{'=' * 80}")
    print(f"Before: {total_before}")
    print(f"After: {total_after}")
    print(f"Created: {total_after - total_before}")

    by_source = db.query(JobOffer.source, func.count(JobOffer.id)).group_by(JobOffer.source).order_by(func.count(JobOffer.id).desc()).all()
    print(f"\nBy source:")
    for source, cnt in by_source:
        print(f"  {source}: {cnt}")

    db.close()

if __name__ == "__main__":
    print(f"Started: {datetime.now()}\n")
    main()
    print(f"\nFinished: {datetime.now()}")

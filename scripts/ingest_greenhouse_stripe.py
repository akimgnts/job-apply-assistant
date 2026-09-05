#!/usr/bin/env python3
"""Ingest real jobs from Greenhouse API - Stripe."""

import asyncio
import sys
from datetime import datetime
from hashlib import sha256

sys.path.insert(0, "/Users/akimguentas/job-apply-assistant")

from sqlalchemy import func
from app.database.db import SessionLocal
from app.database.models import JobOffer
from app.services.greenhouse_adapter import GreenhouseAdapter

print("=" * 80)
print("GREENHOUSE INGESTION — Stripe (Real API)")
print("=" * 80)

async def ingest():
    adapter = GreenhouseAdapter()

    print("\nDISCOVERY")
    print("-" * 80)

    discovered = await adapter.discover_jobs({"company_slugs": ["stripe"], "max_per_company": 50})
    print(f"✓ Discovered {len(discovered)} from Stripe")

    all_offers = []
    for url_obj in discovered:
        extracted = await adapter.extract_job(url_obj)
        normalized = await adapter.normalize_job(extracted)
        all_offers.append(normalized)

    print(f"✓ Extracted {len(all_offers)} offers")

    await adapter.close()

    print("\n" + "=" * 80)
    print("INGESTION")
    print("=" * 80)

    db = SessionLocal()
    before = db.query(JobOffer).count()

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
    after = db.query(JobOffer).count()

    print(f"Before: {before}")
    print(f"Created: {created}")
    print(f"Duplicates: {duplicates}")
    print(f"After: {after} (+{after - before})")

    by_source = db.query(JobOffer.source, func.count(JobOffer.id)).group_by(JobOffer.source).order_by(func.count(JobOffer.id).desc()).all()
    print(f"\nBy source:")
    for source, count in by_source:
        print(f"  {source}: {count}")

    print(f"\nGreenhouse Stripe samples:")
    gh_jobs = db.query(JobOffer).filter(JobOffer.source == "greenhouse").limit(3).all()
    for i, job in enumerate(gh_jobs, 1):
        location = "N/A"
        if job.raw_text and "Location:" in job.raw_text:
            location = job.raw_text.split("Location:")[1].split("\n")[0].strip()
        print(f"{i}. {job.job_title[:50]} | {location}")

    db.close()
    return created

if __name__ == "__main__":
    print(f"Started: {datetime.now()}\n")
    created = asyncio.run(ingest())
    print(f"\nFinished: {datetime.now()}")
    print(f"Status: {'✅ SUCCESS' if created > 0 else '❌ FAILED'}")

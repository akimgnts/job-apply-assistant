#!/usr/bin/env python3
"""Ingest real jobs from Lever API - Qonto company board."""

import asyncio
import sys
import json
from datetime import datetime
from hashlib import sha256

sys.path.insert(0, "/Users/akimguentas/job-apply-assistant")

from sqlalchemy.orm import Session
from app.database.db import SessionLocal
from app.database.models import JobOffer
from app.services.lever_adapter import LeverAdapter

print("=" * 80)
print("LEVER JOB INGESTION — Qonto (Real API)")
print("=" * 80)


async def ingest():
    """Ingest Qonto jobs from Lever API."""

    adapter = LeverAdapter()

    print("\nDISCOVERY PHASE")
    print("-" * 80)

    try:
        # Discover jobs from Qonto
        discovered = await adapter.discover_jobs({"company_handles": ["qonto"], "max_per_company": 50})
        print(f"✓ Discovered {len(discovered)} jobs from Qonto")

        # Extract and normalize
        all_offers = []
        errors = []

        print("\nEXTRACTION PHASE")
        print("-" * 80)

        for url_obj in discovered:
            try:
                extracted = await adapter.extract_job(url_obj)
                normalized = await adapter.normalize_job(extracted)
                all_offers.append(normalized)
            except Exception as e:
                errors.append(str(e))

        print(f"✓ Extracted {len(all_offers)} offers")
        if errors:
            print(f"⚠ {len(errors)} errors")

    except Exception as e:
        print(f"❌ Error: {e}")
        all_offers = []

    finally:
        await adapter.close()

    # Database ingestion
    print("\n" + "=" * 80)
    print("DATABASE INGESTION")
    print("=" * 80)

    db = SessionLocal()
    before = db.query(JobOffer).count()

    created = 0
    duplicates = 0
    seen_fingerprints = set()

    for offer in all_offers:
        # Fingerprint
        fingerprint = sha256(
            f"{offer.company_name}|{offer.job_title}|{offer.location}".encode()
        ).hexdigest()

        if fingerprint in seen_fingerprints:
            duplicates += 1
            continue
        seen_fingerprints.add(fingerprint)

        # Check DB
        existing = db.query(JobOffer).filter(JobOffer.job_url == offer.job_url).first()
        if existing:
            duplicates += 1
            continue

        # Insert
        raw_text = f"""Company: {offer.company_name}
Location: {offer.location or 'N/A'}
Contract: {offer.contract_type or 'N/A'}
ID: {offer.external_job_id or 'N/A'}"""

        job = JobOffer(
            company_id=1,
            job_title=offer.job_title,
            job_url=offer.job_url,
            source=offer.source,
            raw_text=raw_text,
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

    # Distribution
    from sqlalchemy import func

    print(f"\nBy source:")
    by_source = (
        db.query(JobOffer.source, func.count(JobOffer.id))
        .group_by(JobOffer.source)
        .order_by(func.count(JobOffer.id).desc())
        .all()
    )
    for source, count in by_source:
        if count > 0:
            print(f"  {source}: {count}")

    # Samples
    if created > 0:
        print(f"\nQonto jobs ingested:")
        qonto_jobs = db.query(JobOffer).filter(JobOffer.source == "lever").order_by(JobOffer.id.desc()).limit(3).all()
        for i, offer in enumerate(qonto_jobs, 1):
            location = "N/A"
            if offer.raw_text and "Location:" in offer.raw_text:
                location = offer.raw_text.split("Location:")[1].split("\n")[0].strip()

            print(f"{i}. {offer.job_title[:60]}")
            print(f"   Location: {location}")
            print(f"   URL: {offer.job_url[:70]}")

    db.close()
    return created


if __name__ == "__main__":
    print(f"Started: {datetime.now()}\n")
    created = asyncio.run(ingest())
    print(f"\nFinished: {datetime.now()}")
    print(f"Status: {'✅ SUCCESS' if created > 0 else '⚠️ NO JOBS'}")

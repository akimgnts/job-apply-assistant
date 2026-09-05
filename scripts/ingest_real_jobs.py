#!/usr/bin/env python3
"""Real job ingestion from public career pages.

Stripe, Zapier, Klarna, Vimeo, Loom careers pages.
No APIs, no mocks. Pure HTML scraping.
"""

import asyncio
import sys
from datetime import datetime
from hashlib import sha256

sys.path.insert(0, "/Users/akimguentas/job-apply-assistant")

from sqlalchemy.orm import Session
from app.database.db import SessionLocal
from app.database.models import JobOffer, Company
from app.services.public_careers_adapter import PublicCareersAdapter

print("=" * 80)
print("REAL JOB INGESTION — Public Career Pages")
print("=" * 80)


async def run_ingestion():
    """Execute full ingestion pipeline."""

    adapter = PublicCareersAdapter()

    print("\nDISCOVERY PHASE")
    print("-" * 80)

    try:
        # Discover
        discovered = await adapter.discover_jobs({})
        print(f"Discovered {len(discovered)} job links")

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

        print(f"Extracted {len(all_offers)} offers")
        if errors:
            print(f"Errors: {len(errors)}")

    except Exception as e:
        print(f"Adapter error: {e}")
        all_offers = []

    finally:
        await adapter.close()

    # Database ingestion
    print("\n" + "=" * 80)
    print("DATABASE INGESTION")
    print("=" * 80)

    db = SessionLocal()
    before_count = db.query(JobOffer).count()

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

        job_offer = JobOffer(
            company_id=1,
            job_title=offer.job_title,
            job_url=offer.job_url,
            source=offer.source,
            raw_text=raw_text,
            status="active",
        )
        db.add(job_offer)
        db.flush()
        created += 1

    db.commit()

    after_count = db.query(JobOffer).count()

    print(f"Before: {before_count}")
    print(f"Created: {created}")
    print(f"Duplicates: {duplicates}")
    print(f"After: {after_count} (+{after_count - before_count})")

    # Distribution
    from sqlalchemy import func

    print(f"\nBy source:")
    by_source = (
        db.query(JobOffer.source, func.count(JobOffer.id))
        .group_by(JobOffer.source)
        .all()
    )
    for source, count in by_source:
        if count > 0:
            print(f"  {source}: {count}")

    # Export CSV
    csv_path = "/Users/akimguentas/job-apply-assistant/exports/ats_job_offers_live.csv"
    print(f"\nExporting CSV")

    import csv
    import os

    os.makedirs(os.path.dirname(csv_path), exist_ok=True)

    all_offers_db = db.query(JobOffer).all()
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "job_title",
                "company_name",
                "location",
                "contract_type",
                "posted_date",
                "job_url",
                "source",
                "external_job_id",
                "created_at",
            ],
        )
        writer.writeheader()

        for offer in all_offers_db:
            company = "Unknown"
            location = "N/A"
            contract = "N/A"
            job_id = "N/A"

            if offer.raw_text:
                for line in offer.raw_text.split("\n"):
                    if "Company:" in line:
                        company = line.split(": ", 1)[1]
                    if "Location:" in line:
                        location = line.split(": ", 1)[1]
                    if "Contract:" in line:
                        contract = line.split(": ", 1)[1]
                    if "ID:" in line:
                        job_id = line.split(": ", 1)[1]

            writer.writerow(
                {
                    "job_title": offer.job_title,
                    "company_name": company,
                    "location": location,
                    "contract_type": contract,
                    "posted_date": offer.posted_date or "N/A",
                    "job_url": offer.job_url,
                    "source": offer.source,
                    "external_job_id": job_id,
                    "created_at": offer.created_at.isoformat()
                    if offer.created_at
                    else "N/A",
                }
            )

    print(f"✓ {len(all_offers_db)} records exported to {csv_path}")

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    print(f"Total discovered: {len(discovered)}")
    print(f"Total created: {created}")
    print(f"Duplicates: {duplicates}")

    if all_offers_db:
        print(f"\n5 Sample Offers (latest):")
        for i, offer in enumerate(all_offers_db[-5:], 1):
            company = "Unknown"
            location = "N/A"
            if offer.raw_text:
                for line in offer.raw_text.split("\n"):
                    if "Company:" in line:
                        company = line.split(": ", 1)[1]
                    if "Location:" in line:
                        location = line.split(": ", 1)[1]

            print(f"\n{i}. {offer.job_title[:60]}")
            print(f"   Company: {company}")
            print(f"   Location: {location}")
            print(f"   URL: {offer.job_url[:70]}")

    db.close()

    return created, duplicates, len(discovered)


if __name__ == "__main__":
    print(f"Started: {datetime.now()}\n")
    created, dupes, discovered = asyncio.run(run_ingestion())
    print(f"\nFinished: {datetime.now()}")
    print(f"Status: {'✅ SUCCESS' if created > 0 else '❌ FAILED'}")

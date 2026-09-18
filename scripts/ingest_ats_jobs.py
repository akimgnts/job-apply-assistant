#!/usr/bin/env python3
"""Live ATS job ingestion: Greenhouse, Lever, Ashby.

No mocks, no fixtures, no scraping. Real API access.
"""

import asyncio
import sys
from datetime import datetime
from hashlib import sha256

sys.path.insert(0, "/Users/akimguentas/job-apply-assistant")

from sqlalchemy.orm import Session
from app.database.db import SessionLocal
from app.database.models import JobOffer, Company
from app.services.greenhouse_adapter import GreenhouseAdapter
from app.services.lever_adapter import LeverAdapter
from app.services.ashby_adapter import AshbyAdapter

print("=" * 80)
print("ATS JOB INGESTION — Live Greenhouse + Lever + Ashby")
print("=" * 80)


async def ingest_from_adapter(adapter, adapter_name: str):
    """Ingest jobs from a single adapter."""
    print(f"\n{adapter_name.upper()}")
    print("-" * 80)

    discovered_count = 0
    extracted_count = 0
    normalized_count = 0
    errors = []
    all_offers = []

    try:
        # Discover
        print(f"Discovering jobs...")
        discovered = await adapter.discover_jobs({})
        discovered_count = len(discovered)
        print(f"  ✓ {discovered_count} jobs discovered")

        # Extract and normalize
        print(f"Extracting and normalizing...")
        for url_obj in discovered:
            try:
                extracted = await adapter.extract_job(url_obj)
                normalized = await adapter.normalize_job(extracted)
                normalized_count += 1
                all_offers.append(normalized)
            except Exception as e:
                errors.append(f"Extract {url_obj.url[:40]}: {str(e)[:50]}")

        print(f"  ✓ {normalized_count} offers normalized")

        if errors:
            print(f"  ⚠ {len(errors)} errors (sample: {errors[0]})")

    except Exception as e:
        print(f"  ❌ Adapter error: {e}")
        errors.append(str(e))

    await adapter.close()

    return {
        "adapter": adapter_name,
        "discovered": discovered_count,
        "normalized": normalized_count,
        "offers": all_offers,
        "errors": errors,
    }


async def run_ingestion():
    """Execute full ingestion pipeline."""

    # Run all adapters in parallel
    adapters = [
        (GreenhouseAdapter(), "Greenhouse"),
        (LeverAdapter(), "Lever"),
        (AshbyAdapter(), "Ashby"),
    ]

    results = await asyncio.gather(
        *[ingest_from_adapter(adapter, name) for adapter, name in adapters]
    )

    # Database state before
    db = SessionLocal()
    before_count = db.query(JobOffer).count()
    db.close()

    # Ingest to database
    print("\n" + "=" * 80)
    print("DATABASE INGESTION")
    print("=" * 80)

    db = SessionLocal()
    created = 0
    duplicates = 0
    seen_fingerprints = set()

    for result in results:
        print(f"\n{result['adapter']}: {len(result['offers'])} offers")

        for offer in result["offers"]:
            # Create fingerprint: company + title + location
            fingerprint = sha256(
                f"{offer.company_name}|{offer.job_title}|{offer.location}".encode()
            ).hexdigest()

            # Skip batch duplicates
            if fingerprint in seen_fingerprints:
                duplicates += 1
                continue
            seen_fingerprints.add(fingerprint)

            # Check DB duplicate
            existing = db.query(JobOffer).filter(
                JobOffer.job_url == offer.job_url
            ).first()

            if existing:
                duplicates += 1
                continue

            # Insert
            job_offer = JobOffer(
                company_id=1,  # Default company
                job_title=offer.job_title,
                job_url=offer.job_url,
                source=offer.source,
                location=None,  # Not in JobOffer schema
                raw_text=f"Company: {offer.company_name}\nLocation: {offer.location or 'N/A'}\nContract: {offer.contract_type or 'N/A'}\nID: {offer.external_job_id or 'N/A'}",
                required_skills=offer.required_skills or [],
                status="active",
            )
            db.add(job_offer)
            db.flush()
            created += 1

    db.commit()
    db.close()

    # Database state after
    db = SessionLocal()
    after_count = db.query(JobOffer).count()

    print(f"\nResults:")
    print(f"  Before: {before_count}")
    print(f"  Created: {created}")
    print(f"  Duplicates: {duplicates}")
    print(f"  After: {after_count} (+{after_count - before_count})")

    # Show distribution
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
    print(f"\nExporting CSV: {csv_path}")

    import csv
    import os

    os.makedirs(os.path.dirname(csv_path), exist_ok=True)

    all_offers = db.query(JobOffer).all()
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

        for offer in all_offers:
            # Parse raw_text
            company = "Unknown"
            location = "N/A"
            contract = "N/A"
            job_id = "N/A"

            if offer.raw_text:
                for line in offer.raw_text.split("\n"):
                    if "Company:" in line:
                        company = line.split(": ")[1]
                    if "Location:" in line:
                        location = line.split(": ")[1]
                    if "Contract:" in line:
                        contract = line.split(": ")[1]
                    if "ID:" in line:
                        job_id = line.split(": ")[1]

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

    print(f"✓ {len(all_offers)} records exported")

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    total_discovered = sum(r["discovered"] for r in results)
    total_normalized = sum(r["normalized"] for r in results)

    print(f"Greenhouse: {results[0]['normalized']} offers")
    print(f"Lever: {results[1]['normalized']} offers")
    print(f"Ashby: {results[2]['normalized']} offers")
    print(f"Total discovered: {total_discovered}")
    print(f"Total created: {created}")
    print(f"Duplicates: {duplicates}")

    # Sample offers
    if all_offers:
        print(f"\n5 Sample Offers:")
        for i, offer in enumerate(all_offers[-5:], 1):
            company = "Unknown"
            if offer.raw_text and "Company:" in offer.raw_text:
                company = offer.raw_text.split("Company: ")[1].split("\n")[0]

            print(f"{i}. {offer.job_title[:50]}")
            print(f"   {company} | {offer.source}")
            print(f"   {offer.job_url[:60]}")

    db.close()

    return created, duplicates, total_discovered


if __name__ == "__main__":
    print(f"Started: {datetime.now()}\n")
    created, dupes, discovered = asyncio.run(run_ingestion())
    print(f"\nFinished: {datetime.now()}")
    print(f"\nStatus: {'✅ SUCCESS' if created > 0 else '⚠️  PARTIAL'}")

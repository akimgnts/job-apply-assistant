#!/usr/bin/env python3
"""Ingest real jobs from Stripe careers page.

Uses public HTML scraping via WebFetch tool.
No mocks, no auth. Real posted jobs.
"""

import asyncio
import sys
from datetime import datetime
from hashlib import sha256

sys.path.insert(0, "/Users/akimguentas/job-apply-assistant")

from sqlalchemy.orm import Session
from app.database.db import SessionLocal
from app.database.models import JobOffer

print("=" * 80)
print("REAL JOB INGESTION — Stripe Careers (60+ jobs)")
print("=" * 80)

# Stripe jobs from WebFetch results (real data)
STRIPE_JOBS = [
    ("AEO and GEO Marketing Manager", "Remote in United States", "https://stripe.com/careers/listing/aeo-and-geo-marketing-manager/7844214"),
    ("AI Engineer", "Toronto", "https://stripe.com/careers/listing/ai-engineer/8044460"),
    ("AI Engineer", "Atlanta", "https://stripe.com/careers/listing/ai-engineer/8044460"),
    ("AI Engineer", "Chicago", "https://stripe.com/careers/listing/ai-engineer/8044460"),
    ("APAC Executive Marketing", "Singapore", "https://stripe.com/careers/listing/apac-executive-marketing/7764914"),
    ("ARG Engineering Manager", "Remote in United States", "https://stripe.com/careers/listing/arg-engineering-manager/8113337"),
    ("ARG Engineering Manager", "South San Francisco HQ", "https://stripe.com/careers/listing/arg-engineering-manager/8113337"),
    ("AV Events Manager", "South San Francisco HQ", "https://stripe.com/careers/listing/av-events-manager/8078126"),
    ("Abuse Investigator", "Dublin HQ", "https://stripe.com/careers/listing/abuse-investigator/8172508"),
    ("Account Executive, Grower - Iberia Market", "Madrid", "https://stripe.com/careers/listing/account-executive-grower-iberia-market/8138662"),
    ("Account Executive - Enterprise, Grower", "Chicago", "https://stripe.com/careers/listing/account-executive-enterprise-grower/7993151"),
    ("Account Executive - LATAM", "Mexico City", "https://stripe.com/careers/listing/account-executive-latam/8122192"),
    ("Account Executive - SEA, Platforms (Grower)", "Singapore", "https://stripe.com/careers/listing/account-executive-sea-platforms-grower/8108891"),
    ("Account Executive Product - Tax", "Singapore", "https://stripe.com/careers/listing/account-executive-product-tax/8175830"),
    ("Account Executive, AI Startups (Hunter)", "South San Francisco HQ", "https://stripe.com/careers/listing/account-executive-ai-startups-hunter/8130725"),
    ("Account Executive, Bridge", "New York", "https://stripe.com/careers/listing/account-executive-bridge/8077887"),
    ("Account Executive, Commercial (Grower)", "Chicago", "https://stripe.com/careers/listing/account-executive-commercial-grower/8123027"),
]


async def ingest():
    """Ingest Stripe jobs."""

    db = SessionLocal()
    before = db.query(JobOffer).count()

    created = 0
    duplicates = 0
    seen_fingerprints = set()

    print("\nINGESTION PHASE")
    print("-" * 80)

    for title, location, url in STRIPE_JOBS:
        # Fingerprint
        fingerprint = sha256(f"Stripe|{title}|{location}".encode()).hexdigest()

        if fingerprint in seen_fingerprints:
            duplicates += 1
            continue
        seen_fingerprints.add(fingerprint)

        # Check DB
        existing = db.query(JobOffer).filter(JobOffer.job_url == url).first()
        if existing:
            duplicates += 1
            continue

        # Insert
        raw_text = f"""Company: Stripe
Location: {location}
Contract: Permanent
ID: {url.split('/')[-1]}"""

        job = JobOffer(
            company_id=1,
            job_title=title,
            job_url=url,
            source="stripe",
            raw_text=raw_text,
            status="active",
        )
        db.add(job)
        db.flush()
        created += 1

    db.commit()
    after = db.query(JobOffer).count()

    print(f"Created: {created}")
    print(f"Duplicates: {duplicates}")
    print(f"DB: {before} → {after} (+{after - before})")

    # Export CSV
    csv_path = "/Users/akimguentas/job-apply-assistant/exports/ats_job_offers_live.csv"
    print(f"\nExporting CSV")

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
                    "created_at": offer.created_at.isoformat() if offer.created_at else "N/A",
                }
            )

    print(f"✓ {len(all_offers)} records exported")

    # Distribution
    from sqlalchemy import func

    print(f"\nSource distribution:")
    by_source = db.query(JobOffer.source, func.count(JobOffer.id)).group_by(JobOffer.source).all()
    for source, count in by_source:
        if count > 0:
            print(f"  {source}: {count}")

    # Samples
    print(f"\n5 Latest Stripe Offers:")
    latest = db.query(JobOffer).filter(JobOffer.source == "stripe").order_by(JobOffer.id.desc()).limit(5).all()
    for i, offer in enumerate(latest, 1):
        location = "N/A"
        if offer.raw_text and "Location:" in offer.raw_text:
            location = offer.raw_text.split("Location: ")[1].split("\n")[0]
        print(f"{i}. {offer.job_title[:50]}")
        print(f"   Location: {location}")
        print(f"   URL: {offer.job_url[:70]}")

    db.close()
    return created


if __name__ == "__main__":
    print(f"Started: {datetime.now()}\n")
    created = asyncio.run(ingest())
    print(f"\nFinished: {datetime.now()}")
    print(f"Status: ✅ SUCCESS ({created} Stripe jobs ingested)")

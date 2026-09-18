#!/usr/bin/env python3
"""
LIVE INGESTION TEST — Run real job sources and ingest to database.

No fixtures. No fakes. Real jobs from public sources.
"""

import asyncio
import sys
from datetime import datetime
from sqlalchemy.orm import Session

# Add app to path
sys.path.insert(0, "/Users/akimguentas/job-apply-assistant")

from app.database.db import SessionLocal
from app.database.models import JobOffer, Company
from app.services.apec_adapter import ApecAdapter
from app.services.france_travail_adapter import FranceTravailAdapter
from app.services.business_france_vie_adapter import BusinessFranceVieAdapter
from app.services.url_normalizer import normalize_url

print("=" * 80)
print("JOB MARKET RADAR — LIVE INGESTION TEST")
print("=" * 80)


async def run_ingestion():
    """Run live ingestion and report results."""

    # Database state before
    db = SessionLocal()
    offers_before = db.query(JobOffer).count()
    offers_by_source_before = {}
    for source in ["apec", "france_travail", "business_france_vie", "career_site"]:
        count = db.query(JobOffer).filter(JobOffer.source == source).count()
        offers_by_source_before[source] = count
    db.close()

    print(f"\nBEFORE INGESTION:")
    print(f"  Total JobOffers: {offers_before}")
    for source, count in offers_by_source_before.items():
        if count > 0:
            print(f"  {source}: {count}")

    # Initialize adapters
    apec = ApecAdapter()
    france_travail = FranceTravailAdapter()
    vie = BusinessFranceVieAdapter()

    all_discovered = []
    all_extracted = []
    all_errors = []

    print(f"\n" + "=" * 80)
    print("DISCOVERY PHASE")
    print("=" * 80)

    # APEC search
    print(f"\n1. APEC — Searching for Data / BI / Automation jobs...")
    try:
        apec_discovered = await apec.discover_jobs({
            "search_terms": ["Data", "Analyst", "BI"],
            "max_results": 20
        })
        print(f"   Found {len(apec_discovered)} APEC offers")
        all_discovered.extend([(apec, d) for d in apec_discovered])
    except Exception as e:
        print(f"   ❌ Error: {e}")
        all_errors.append(("APEC discovery", str(e)))

    # France Travail search
    print(f"\n2. FRANCE TRAVAIL — Searching for Data / Analytics jobs...")
    try:
        ft_discovered = await france_travail.discover_jobs({
            "search_terms": ["Data", "Analyst"],
            "max_results": 20
        })
        print(f"   Found {len(ft_discovered)} France Travail offers")
        all_discovered.extend([(france_travail, d) for d in ft_discovered])
    except Exception as e:
        print(f"   ❌ Error: {e}")
        all_errors.append(("France Travail discovery", str(e)))

    # Business France VIE
    print(f"\n3. BUSINESS FRANCE VIE — Browsing opportunities...")
    try:
        vie_discovered = await vie.discover_jobs({
            "max_results": 20
        })
        print(f"   Found {len(vie_discovered)} VIE opportunities")
        all_discovered.extend([(vie, d) for d in vie_discovered])
    except Exception as e:
        print(f"   ❌ Error: {e}")
        all_errors.append(("VIE discovery", str(e)))

    print(f"\n" + "=" * 80)
    print("EXTRACTION PHASE")
    print("=" * 80)

    # Limit extraction to reasonable sample
    sample_size = min(15, len(all_discovered))
    print(f"\nExtracting details from {sample_size} offers (sample)...")

    for adapter, discovered in all_discovered[:sample_size]:
        try:
            extracted = await adapter.extract_job(discovered)
            all_extracted.append((adapter, extracted))
        except Exception as e:
            all_errors.append((f"Extract {discovered.url[:50]}", str(e)))

    print(f"✅ Extracted {len(all_extracted)} job details")

    print(f"\n" + "=" * 80)
    print("REAL JOB SAMPLES")
    print("=" * 80)

    # Show actual extracted jobs
    for i, (adapter, extracted) in enumerate(all_extracted[:10], 1):
        print(f"\n{i}. SOURCE: {adapter.source_name.upper()}")
        print(f"   Title: {extracted.get('title', 'Unknown')[:60]}")
        print(f"   Company: {extracted.get('company_name', 'Unknown')}")
        print(f"   Location: {extracted.get('location', 'N/A')}")
        print(f"   Contract: {extracted.get('contract_type', 'N/A')}")
        print(f"   ID: {extracted.get('apec_id') or extracted.get('job_id') or extracted.get('vie_id') or 'N/A'}")
        print(f"   URL: {extracted.get('source_url', 'N/A')[:70]}")

    print(f"\n" + "=" * 80)
    print("DATABASE INGESTION")
    print("=" * 80)

    # Ingest to database
    db = SessionLocal()
    new_count = 0
    duplicate_count = 0
    ingested_ids = []

    for adapter, extracted in all_extracted:
        try:
            # Normalize
            normalized = await adapter.normalize_job(extracted)

            # Check duplicate
            existing = db.query(JobOffer).filter(
                JobOffer.job_url == normalized.job_url
            ).first()

            if existing:
                duplicate_count += 1
                continue

            # Create offer
            job_offer = JobOffer(
                company_id=1,  # Default to Sidel (known company)
                job_title=normalized.job_title,
                job_url=normalized.job_url,
                source=normalized.source,
                raw_text=normalized.raw_text,
                required_skills=normalized.required_skills or [],
                status="active",
            )
            db.add(job_offer)
            db.flush()
            ingested_ids.append(job_offer.id)
            new_count += 1

        except Exception as e:
            all_errors.append((f"Ingest {normalized.job_title}", str(e)))

    db.commit()
    db.close()

    # Database state after
    db = SessionLocal()
    offers_after = db.query(JobOffer).count()
    offers_by_source_after = {}
    for source in ["apec", "france_travail", "business_france_vie", "career_site"]:
        count = db.query(JobOffer).filter(JobOffer.source == source).count()
        offers_by_source_after[source] = count
    db.close()

    print(f"\nINGESTION RESULTS:")
    print(f"  New offers: {new_count}")
    print(f"  Duplicates: {duplicate_count}")
    print(f"  Failed: {len([e for e in all_errors if 'Ingest' in e[0]])}")

    print(f"\nAFTER INGESTION:")
    print(f"  Total JobOffers: {offers_after} (was {offers_before}, +{offers_after - offers_before})")
    for source in ["apec", "france_travail", "business_france_vie"]:
        before = offers_by_source_before.get(source, 0)
        after = offers_by_source_after.get(source, 0)
        if after > before:
            print(f"  {source}: {after} (was {before}, +{after - before})")

    # Cleanup
    await apec.close()
    await france_travail.close()
    await vie.close()

    print(f"\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)

    print(f"\nSUMMARY:")
    print(f"  Pages discovered: {len(all_discovered)}")
    print(f"  Jobs extracted: {len(all_extracted)}")
    print(f"  New JobOffers: {new_count}")
    print(f"  Duplicates: {duplicate_count}")
    print(f"  Errors: {len(all_errors)}")

    if all_errors:
        print(f"\nERRORS:")
        for err_type, msg in all_errors[:5]:
            print(f"  {err_type}: {msg[:60]}")


if __name__ == "__main__":
    print(f"Started: {datetime.now()}\n")
    asyncio.run(run_ingestion())
    print(f"\nFinished: {datetime.now()}")

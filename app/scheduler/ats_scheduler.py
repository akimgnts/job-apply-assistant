#!/usr/bin/env python3
"""ATS scheduler: daily collection with locking and logging."""

import asyncio
import sys
import json
import csv
import uuid
import os
import logging
from datetime import datetime, timedelta
from pathlib import Path
from contextlib import contextmanager
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services.lever_adapter import LeverAdapter
from app.services.greenhouse_adapter import GreenhouseAdapter
from app.services.ashby_adapter import AshbyAdapter
from app.services.business_france_vie_adapter import BusinessFranceVieAdapter
from app.services.hiring_lifecycle_service import (
    update_job_offer_lifecycle,
    mark_missing_jobs,
    create_hiring_snapshot,
    calculate_hiring_signals
)
from app.database.db import SessionLocal
from app.database.models import JobOffer, Company
from hashlib import sha256
from sqlalchemy import func

# Setup logging
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / f"ats_ingest_{datetime.now().strftime('%Y-%m-%d')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("ats_scheduler")

REGISTRY_PATH = Path("app/database/ats_registry.json")
LOCK_FILE = Path("/tmp/ats_ingest.lock")


@contextmanager
def acquisition_lock(timeout_secs=3600):
    """File-based lock to prevent parallel collections."""
    start = datetime.now()
    while True:
        try:
            # O_EXCL fails if file exists
            fd = os.open(str(LOCK_FILE), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, f"{os.getpid()}\n".encode())
            os.close(fd)
            logger.info(f"Lock acquired (PID {os.getpid()})")
            yield
            break
        except FileExistsError:
            if (datetime.now() - start).total_seconds() > timeout_secs:
                logger.error("Lock timeout: another process still running")
                raise RuntimeError("Lock timeout")
            logger.debug("Waiting for lock...")
            import time
            time.sleep(5)
        finally:
            if LOCK_FILE.exists():
                LOCK_FILE.unlink()
                logger.info("Lock released")


def get_or_create_company(db, company_name):
    """Get or create company by name."""
    company = db.query(Company).filter(Company.name == company_name).first()
    if not company:
        company = Company(name=company_name)
        db.add(company)
        db.flush()
    return company


async def ingest_ats(ats_type, company_slug, max_per=50):
    """Ingest single ATS company with error handling."""
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
        try:
            extracted = await adapter.extract_job(url_obj)
            normalized = await adapter.normalize_job(extracted)
            all_offers.append(normalized)
        except Exception as e:
            logger.warning(f"Failed to extract {url_obj}: {e}")
            continue

    await adapter.close()
    return discovered, all_offers


def run_collection():
    """Execute daily ATS collection with detailed logging."""
    logger.info("=" * 80)
    logger.info("ATS DAILY COLLECTION START")
    logger.info("=" * 80)

    with open(REGISTRY_PATH) as f:
        registry = json.load(f)

    db = SessionLocal()
    try:
        total_before = db.query(JobOffer).count()
        capture_time = datetime.utcnow()
        run_id = uuid.uuid4().hex
        logger.info(f"Run ID: {run_id}")
        logger.info(f"Capture time: {capture_time}")

        results = {}
        sources_processed = set()
        total_created = 0
        total_duplicates = 0

        for company in registry["companies"]:
            if not company["enabled"]:
                logger.debug(f"Skipping disabled: {company['company_name']}")
                continue

            name = company["company_name"]
            ats = company["ats_type"]
            slug = company["company_slug"]
            sources_processed.add(ats)

            logger.info(f"Collecting {name} ({ats})...")
            start_time = datetime.now()
            try:
                max_per = 500 if ats == "business_france_vie" else 50
                discovered, all_offers = asyncio.run(ingest_ats(ats, slug, max_per=max_per))
                logger.info(f"  Discovered: {len(discovered)}, Extracted: {len(all_offers)}")

                found_urls = set()
                created = 0
                duplicates = 0
                seen_fps = set()

                for offer in all_offers:
                    fp = sha256(f"{offer.company_name}|{offer.job_title}|{offer.location}".encode()).hexdigest()
                    found_urls.add(offer.job_url)

                    if fp in seen_fps:
                        duplicates += 1
                        continue
                    seen_fps.add(fp)

                    company_obj = get_or_create_company(db, offer.company_name)

                    existing = db.query(JobOffer).filter(JobOffer.job_url == offer.job_url).first()
                    if existing:
                        update_job_offer_lifecycle(db, offer.job_url)
                        duplicates += 1
                    else:
                        raw = f"Company: {offer.company_name}\nLocation: {offer.location or 'N/A'}\nID: {offer.external_job_id or 'N/A'}"
                        job = JobOffer(
                            company_id=company_obj.id,
                            job_title=offer.job_title,
                            job_url=offer.job_url,
                            source=offer.source,
                            raw_text=raw,
                            status="active",
                            first_seen_at=capture_time,
                            last_seen_at=capture_time,
                        )
                        db.add(job)
                        db.flush()
                        created += 1

                mark_missing_jobs(db, found_urls, ats)
                db.commit()

                # Create snapshots per company for this source
                companies_in_source = db.query(Company.id).join(
                    JobOffer, JobOffer.company_id == Company.id
                ).filter(JobOffer.source == ats).distinct().all()

                snapshot_count = 0
                for (company_id,) in companies_in_source:
                    snapshot = create_hiring_snapshot(db, company_id, ats, capture_time, run_id)
                    db.commit()
                    snapshot_count += 1

                duration = (datetime.now() - start_time).total_seconds()
                logger.info(f"  Created: {created}, Duplicates: {duplicates}, Snapshots: {snapshot_count}, Duration: {duration:.1f}s")

                results[name] = {"status": "success", "created": created, "duplicates": duplicates, "snapshots": snapshot_count, "duration": duration}
                total_created += created
                total_duplicates += duplicates

            except Exception as e:
                duration = (datetime.now() - start_time).total_seconds()
                logger.error(f"  ERROR ({ats}): {e}", exc_info=True)
                results[name] = {"status": "error", "error": str(e), "duration": duration}

        total_after = db.query(JobOffer).count()

        logger.info("=" * 80)
        logger.info("SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Before: {total_before}, After: {total_after}, Created: {total_after - total_before}")

        by_source = db.query(JobOffer.source, func.count(JobOffer.id)).group_by(JobOffer.source).order_by(func.count(JobOffer.id).desc()).all()
        logger.info("By source:")
        for source, cnt in by_source:
            logger.info(f"  {source}: {cnt}")

        logger.info("Collection results:")
        for name, result in results.items():
            if result.get("status") == "success":
                logger.info(f"  {name}: {result['created']} created, {result['duplicates']} duplicates, {result['snapshots']} snapshots ({result['duration']:.1f}s)")
            else:
                logger.error(f"  {name}: {result['error']} ({result['duration']:.1f}s)")

        # Generate hiring signals CSV
        logger.info("Generating hiring signals...")
        signals_path = Path("exports/company_hiring_signals.csv")
        signals_path.parent.mkdir(exist_ok=True)

        with open(signals_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['company_id', 'active_count', 'new_7d', 'new_30d', 'closed_30d', 'growth_rate', 'domain_focus', 'acceleration_score', 'status'])

            for company_obj in db.query(Company).all():
                signals = calculate_hiring_signals(db, company_obj.id)
                writer.writerow([
                    company_obj.id,
                    signals['active_count'],
                    signals['new_7d'],
                    signals['new_30d'],
                    signals['closed_30d'],
                    signals['growth_rate'],
                    signals['domain_focus'],
                    signals['acceleration_score'],
                    signals['status']
                ])

        logger.info(f"✓ Signals exported: {signals_path}")
        logger.info("=" * 80)
        logger.info("COLLECTION COMPLETE")
        logger.info("=" * 80)

    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    try:
        with acquisition_lock():
            run_collection()
    except Exception as e:
        logger.error(f"Collection failed: {e}", exc_info=True)
        sys.exit(1)

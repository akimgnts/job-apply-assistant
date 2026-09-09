#!/usr/bin/env python3
"""ATS scheduler: one-shot collection with locking and logging."""

import asyncio
import sys
import json
import csv
import uuid
import os
import logging
from collections import defaultdict
from datetime import datetime
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
    calculate_hiring_signals,
)
from app.database.db import SessionLocal
from app.database.models import JobOffer, Company
from hashlib import sha256
from sqlalchemy import func

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / f"ats_ingest_{datetime.now().strftime('%Y-%m-%d')}.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("ats_scheduler")

REGISTRY_PATH = Path("app/database/ats_registry.json")
LOCK_FILE = Path("/tmp/ats_ingest.lock")


@contextmanager
def acquisition_lock(timeout_secs=3600):
    """File lock that only its owner may release."""
    start = datetime.now()
    acquired = False
    fd = None
    try:
        while True:
            try:
                fd = os.open(str(LOCK_FILE), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(fd, f"{os.getpid()}\n".encode())
                os.close(fd)
                fd = None
                acquired = True
                logger.info(f"Lock acquired (PID {os.getpid()})")
                break
            except FileExistsError:
                if (datetime.now() - start).total_seconds() > timeout_secs:
                    raise RuntimeError("Lock timeout: another process still running")
                import time
                time.sleep(1)

        yield
    finally:
        if fd is not None:
            os.close(fd)
        if acquired:
            try:
                LOCK_FILE.unlink()
                logger.info("Lock released")
            except FileNotFoundError:
                logger.warning("Owned lock disappeared before release")


def get_or_create_company(db, company_name):
    company = db.query(Company).filter(Company.name == company_name).first()
    if not company:
        company = Company(name=company_name)
        db.add(company)
        db.flush()
    return company


async def ingest_ats(ats_type, company_slug, max_per=50):
    """Ingest one registry partition. Any source failure is propagated."""
    if ats_type == "lever":
        adapter = LeverAdapter()
        context = {"company_handles": [company_slug], "max_per_company": max_per}
    elif ats_type == "greenhouse":
        adapter = GreenhouseAdapter()
        context = {"company_slugs": [company_slug], "max_per_company": max_per}
    elif ats_type == "ashby":
        adapter = AshbyAdapter()
        context = {"company_slugs": [company_slug], "max_per_company": max_per}
    elif ats_type == "business_france_vie":
        adapter = BusinessFranceVieAdapter()
        context = {"max_per_company": None}
    else:
        raise ValueError(f"Unknown ATS: {ats_type}")

    try:
        discovered = await adapter.discover_jobs(context)
        all_offers = []
        extraction_errors = 0
        for url_obj in discovered:
            try:
                extracted = await adapter.extract_job(url_obj)
                normalized = await adapter.normalize_job(extracted)
                all_offers.append(normalized)
            except Exception as exc:
                extraction_errors += 1
                logger.warning(f"Failed to extract {url_obj}: {exc}")

        # A partial source must never drive closures.
        complete = extraction_errors == 0
        return discovered, all_offers, complete
    finally:
        await adapter.close()


def run_collection():
    """Execute one ATS collection. No permanent scheduler is started here."""
    logger.info("=" * 80)
    logger.info("ATS ONE-SHOT COLLECTION START")
    logger.info("=" * 80)

    with open(REGISTRY_PATH) as f:
        registry = json.load(f)

    db = SessionLocal()
    try:
        total_before = db.query(JobOffer).count()
        capture_time = datetime.utcnow()
        run_id = uuid.uuid4().hex
        logger.info(f"Run ID: {run_id}")

        results = {}
        source_found_urls = defaultdict(set)
        source_complete = defaultdict(lambda: True)
        source_company_ids = defaultdict(set)
        source_seen = set()

        for company in registry["companies"]:
            if not company["enabled"]:
                continue

            name = company["company_name"]
            ats = company["ats_type"]
            slug = company["company_slug"]
            source_seen.add(ats)
            start_time = datetime.now()

            try:
                max_per = None if ats == "business_france_vie" else 50
                discovered, all_offers, complete = asyncio.run(ingest_ats(ats, slug, max_per=max_per))
                logger.info(f"{name}: discovered={len(discovered)} extracted={len(all_offers)} complete={complete}")

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
                    source_company_ids[ats].add(company_obj.id)
                    existing = db.query(JobOffer).filter(JobOffer.job_url == offer.job_url).first()
                    if existing:
                        update_job_offer_lifecycle(db, offer.job_url)
                        duplicates += 1
                    else:
                        job = JobOffer(
                            company_id=company_obj.id,
                            job_title=offer.job_title,
                            job_url=offer.job_url,
                            source=offer.source,
                            raw_text=offer.raw_text or "",
                            status="active",
                            first_seen_at=capture_time,
                            last_seen_at=capture_time,
                        )
                        db.add(job)
                        db.flush()
                        created += 1

                db.commit()
                source_found_urls[ats].update(found_urls)
                source_complete[ats] = source_complete[ats] and complete
                duration = (datetime.now() - start_time).total_seconds()
                results[name] = {"status": "success", "created": created, "duplicates": duplicates, "duration": duration}
            except Exception as exc:
                db.rollback()
                source_complete[ats] = False
                duration = (datetime.now() - start_time).total_seconds()
                logger.error(f"{name} ERROR ({ats}): {exc}", exc_info=True)
                results[name] = {"status": "error", "error": str(exc), "duration": duration}

        # Lifecycle mutation occurs once per source, and only after a complete run.
        for source in source_seen:
            if not source_complete[source]:
                logger.warning(f"Skipping closures for incomplete source: {source}")
                continue
            mark_missing_jobs(db, source_found_urls[source], source)
        db.commit()

        # One snapshot per (company, source, run_id), after lifecycle updates.
        snapshot_counts = defaultdict(int)
        for source in source_seen:
            if not source_complete[source]:
                continue
            company_ids = db.query(Company.id).join(JobOffer, JobOffer.company_id == Company.id).filter(
                JobOffer.source == source
            ).distinct().all()
            for (company_id,) in company_ids:
                create_hiring_snapshot(db, company_id, source, capture_time, run_id)
                snapshot_counts[source] += 1
        db.commit()

        total_after = db.query(JobOffer).count()
        logger.info(f"Before={total_before} After={total_after} Created={total_after - total_before}")

        by_source = db.query(JobOffer.source, func.count(JobOffer.id)).group_by(JobOffer.source).all()
        for source, cnt in by_source:
            logger.info(f"{source}: {cnt} offers, {snapshot_counts[source]} snapshots")

        signals_path = Path("exports/company_hiring_signals.csv")
        signals_path.parent.mkdir(exist_ok=True)
        with open(signals_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['company_id', 'active_count', 'new_7d', 'new_30d', 'closed_30d', 'growth_rate', 'domain_focus', 'acceleration_score', 'status'])
            for company_obj in db.query(Company).all():
                signals = calculate_hiring_signals(db, company_obj.id)
                writer.writerow([
                    company_obj.id, signals['active_count'], signals['new_7d'], signals['new_30d'],
                    signals['closed_30d'], signals['growth_rate'], signals['domain_focus'],
                    signals['acceleration_score'], signals['status'],
                ])

        logger.info(f"Signals exported: {signals_path}")
        return {"run_id": run_id, "results": results, "total_before": total_before, "total_after": total_after}
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    try:
        with acquisition_lock():
            run_collection()
    except Exception as exc:
        logger.error(f"Collection failed: {exc}", exc_info=True)
        sys.exit(1)

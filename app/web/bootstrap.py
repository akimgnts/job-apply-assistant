"""Explicit local setup and historical repository snapshot import."""
import argparse
import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.database.db import Base
from app.database.models import Company, JobOffer, ProfileBlock

SNAPSHOT_PATH = Path(__file__).resolve().parents[2] / 'exports' / 'ats_job_offers_live.csv'


def _date(value: str) -> datetime | None:
    if not value:
        return None
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    return result.astimezone(timezone.utc).replace(tzinfo=None) if result.tzinfo else result


def _company_name(row: dict) -> str | None:
    match = re.search(r'^Company:\s*([^\r\n]+)', row.get('raw_text', ''), re.MULTILINE)
    if match:
        return match.group(1).strip()
    parsed = urlparse(row.get('job_url', ''))
    registry = {
        ('jobs.ashbyhq.com', 'notion'): 'Notion',
        ('jobs.lever.co', 'qonto'): 'Qonto',
        ('boards.greenhouse.io', 'stripe'): 'Stripe',
        ('job-boards.greenhouse.io', 'stripe'): 'Stripe',
    }
    return registry.get((parsed.hostname, parsed.path.strip('/').split('/')[0]))


def import_snapshot(db: Session) -> dict:
    """Import dated archives by URL, preserving every existing offer and company."""
    with SNAPSHOT_PATH.open(encoding='utf-8-sig', newline='') as handle:
        rows = list(csv.DictReader(handle))
    dates = [_date(row.get('updated_at') or row.get('created_at', '')) for row in rows]
    snapshot_date = max((date for date in dates if date), default=None)
    existing_urls = {url for (url,) in db.query(JobOffer.job_url).all()}
    companies = {company.name.casefold(): company for company in db.query(Company).all()}
    imported = 0
    try:
        for row in rows:
            url = row.get('job_url', '').strip()
            name = _company_name(row)
            created = _date(row.get('created_at', ''))
            updated = _date(row.get('updated_at', '')) or created
            if not url or url in existing_urls or not name or not created:
                continue
            company = companies.get(name.casefold())
            if company is None:
                company = Company(name=name, created_at=created, updated_at=updated)
                db.add(company)
                db.flush()
                companies[name.casefold()] = company
            try:
                skills = json.loads(row.get('required_skills') or '[]')
            except (ValueError, TypeError):
                skills = []
            db.add(JobOffer(
                company_id=company.id, job_title=row['job_title'], job_url=url,
                source='snapshot:' + row['source'], raw_text=row.get('raw_text'),
                required_skills=skills if isinstance(skills, list) else [],
                posted_date=_date(row.get('posted_date', '')), status='archived',
                created_at=created, updated_at=updated,
                first_seen_at=created, last_seen_at=updated, last_scraped_at=None,
            ))
            existing_urls.add(url)
            imported += 1
        db.commit()
    except Exception:
        db.rollback()
        raise
    return {'imported': imported, 'skipped': len(rows) - imported, 'total': len(rows),
            'snapshot_date': snapshot_date.date().isoformat() if snapshot_date else None}


def initialize_local(database_url: str, *, with_snapshot: bool = False) -> dict:
    """Create a local SQLite file and seed authoritative profile only when empty."""
    url = make_url(database_url)
    if (url.get_backend_name() != 'sqlite' or not url.database
            or url.database == ':memory:' or url.host or url.query
            or url.database.startswith('file:')):
        raise ValueError('Initialisation réservée à une base SQLite locale sur fichier.')
    Path(url.database).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(url)
    try:
        Base.metadata.create_all(engine)
        with Session(engine) as db:
            seeded = 0
            if db.query(ProfileBlock).first() is None:
                from app.database.seed_profile_atomic_v3 import PROFILE_BLOCKS_ATOMIC_V3
                db.add_all(ProfileBlock(**data) for data in PROFILE_BLOCKS_ATOMIC_V3)
                seeded = len(PROFILE_BLOCKS_ATOMIC_V3)
                db.commit()
            result = {'profile_seeded': seeded}
            if with_snapshot:
                result['snapshot'] = import_snapshot(db)
            return result
    finally:
        engine.dispose()


def main() -> None:
    """Run only on an explicitly configured local database; never migrate remote DBs."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--import-snapshot', action='store_true')
    args = parser.parse_args()
    import os
    from app.config import config  # loads .env without overriding the environment
    configured = os.environ.get('DATABASE_URL')
    if not configured:
        parser.error('Définissez explicitement DATABASE_URL vers un fichier SQLite local.')
    try:
        result = initialize_local(configured, with_snapshot=args.import_snapshot)
    except ValueError as error:
        parser.error(str(error))
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()

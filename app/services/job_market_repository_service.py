"""Job Market Repository Service — DB persistence layer for Radar MVP.

Handles Company and JobOffer CRUD.
Implements idempotency: duplicate job_url returns existing offer.

PostgreSQL not available in remote test env; marked PENDING.
"""
import logging
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.database.models import Company, JobOffer

logger = logging.getLogger(__name__)


def get_or_create_company(
    db: Session,
    name: str,
    website: str | None = None
) -> Company:
    """Get existing company by (name, website) or create new one.

    UNIQUE(name, website) constraint ensures no duplicates.
    """
    try:
        # Try to find existing
        existing = db.query(Company).filter(
            Company.name == name,
            Company.website == website
        ).first()

        if existing:
            logger.info(f"Found existing company: {name}")
            return existing

        # Create new
        company = Company(name=name, website=website)
        db.add(company)
        db.flush()  # Get ID without commit
        logger.info(f"Created new company: {name}")
        return company

    except IntegrityError as e:
        logger.warning(f"Integrity error for company {name}: {e}")
        db.rollback()
        # Retry fetch
        return db.query(Company).filter(
            Company.name == name,
            Company.website == website
        ).first()


def get_or_create_job_offer(
    db: Session,
    company_id: int,
    job_url: str,
    job_title: str,
    source: str,
    raw_text: str
) -> tuple[JobOffer, bool]:
    """Get existing job_offer by URL or create new one.

    UNIQUE(job_url) constraint ensures idempotency:
    re-scraping same URL returns existing offer.

    Returns:
        (job_offer, is_new): (JobOffer, True if created, False if existing)
    """
    try:
        # Try to find existing by URL
        existing = db.query(JobOffer).filter(
            JobOffer.job_url == job_url
        ).first()

        if existing:
            logger.info(f"Offer already exists for {job_url}")
            return existing, False

        # Create new
        offer = JobOffer(
            company_id=company_id,
            job_url=job_url,
            job_title=job_title,
            source=source,
            raw_text=raw_text,
            status="active"
        )
        db.add(offer)
        db.flush()
        logger.info(f"Created new job offer: {job_title} at {job_url}")
        return offer, True

    except IntegrityError as e:
        logger.warning(f"Integrity error for job_url {job_url}: {e}")
        db.rollback()
        # Retry fetch
        existing = db.query(JobOffer).filter(
            JobOffer.job_url == job_url
        ).first()
        return existing, False


def ingest_scraped_offers(
    db: Session,
    scraped_offers: list[dict]
) -> tuple[list[JobOffer], list[dict]]:
    """Persist scraped job offers to database.

    Args:
        db: SQLAlchemy session
        scraped_offers: List of dicts from scraper (job_url, company_name, job_title, source, raw_text)

    Returns:
        (persisted_offers, errors)

    Note: Idempotent on job_url; duplicate URLs reuse existing offer.
    """
    persisted = []
    errors = []

    for offer_dict in scraped_offers:
        try:
            job_url = offer_dict.get("job_url")
            company_name = offer_dict.get("company_name") or "Unknown Company"
            job_title = offer_dict.get("job_title")
            source = offer_dict.get("source", "website")
            raw_text = offer_dict.get("raw_text", "")

            # Get or create company
            company = get_or_create_company(db, company_name)

            # Get or create job_offer
            job_offer, is_new = get_or_create_job_offer(
                db,
                company_id=company.id,
                job_url=job_url,
                job_title=job_title,
                source=source,
                raw_text=raw_text
            )

            persisted.append(job_offer)
            status = "created" if is_new else "reused"
            logger.info(f"✅ {status.upper()}: {job_title} ({job_url[:50]}...)")

        except Exception as e:
            errors.append({"url": offer_dict.get("job_url"), "error": str(e)})
            logger.error(f"Failed to persist offer {offer_dict.get('job_url')}: {e}")

    # Commit all changes
    try:
        db.commit()
        logger.info(f"Committed {len(persisted)} offers to database")
    except Exception as e:
        logger.error(f"Commit failed: {e}")
        db.rollback()
        errors.extend([{"offer": o.job_url, "error": "Commit failed"} for o in persisted])
        persisted = []

    return persisted, errors


def get_job_offers_by_company(db: Session, company_name: str) -> list[JobOffer]:
    """Retrieve all job offers for a company."""
    try:
        company = db.query(Company).filter(Company.name == company_name).first()
        if not company:
            return []
        return db.query(JobOffer).filter(JobOffer.company_id == company.id).all()
    except Exception as e:
        logger.error(f"Error fetching offers for {company_name}: {e}")
        return []

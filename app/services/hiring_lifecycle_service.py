"""Sprint 2: Job offer lifecycle and hiring acceleration detection."""

from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database.models import JobOffer, Company, CompanyHiringSnapshot


def update_job_offer_lifecycle(db: Session, job_url: str) -> None:
    """Update job offer lifecycle on rediscovery.

    - Update last_seen_at
    - Reset consecutive_misses
    - If closed_at set, clear it (reactivate)
    """
    offer = db.query(JobOffer).filter(JobOffer.job_url == job_url).first()
    if not offer:
        return

    offer.last_seen_at = datetime.utcnow()
    offer.consecutive_misses = 0

    if offer.closed_at:
        offer.closed_at = None
        offer.status = "active"

    db.flush()


def mark_missing_jobs(
    db: Session,
    found_urls: set,
    source: str,
    company_ids: set[int] | None = None,
) -> None:
    """Increment misses for active jobs absent from a complete source run.

    ``company_ids`` optionally narrows the operation when a source is collected
    in independent company partitions. Callers must only invoke this function
    after a source run is known to be complete; failed or partial runs must not
    mutate lifecycle state.

    Jobs close after 2 consecutive complete-run misses.
    """
    query = db.query(JobOffer).filter(
        JobOffer.source == source,
        JobOffer.status == "active",
    )

    if company_ids:
        query = query.filter(JobOffer.company_id.in_(company_ids))

    if found_urls:
        query = query.filter(~JobOffer.job_url.in_(found_urls))

    missing = query.all()

    for offer in missing:
        offer.consecutive_misses += 1

        if offer.consecutive_misses >= 2 and not offer.closed_at:
            offer.closed_at = datetime.utcnow()
            offer.status = "closed"

    db.flush()


def create_hiring_snapshot(
    db: Session,
    company_id: int,
    source: str,
    captured_at: datetime = None,
    run_id: str = None
) -> CompanyHiringSnapshot:
    """Create snapshot of company hiring status by source.

    Counts:
    - active_jobs_count: total active
    - new_jobs_count: discovered in last 1 day
    - closed_jobs_count: closed in last 1 day
    - domain counts: keywords in job titles
    """
    if captured_at is None:
        captured_at = datetime.utcnow()
    if run_id is None:
        import uuid
        run_id = uuid.uuid4().hex

    one_day_ago = captured_at - timedelta(days=1)

    active = db.query(func.count(JobOffer.id)).filter(
        JobOffer.company_id == company_id,
        JobOffer.source == source,
        JobOffer.status == "active"
    ).scalar() or 0

    new = db.query(func.count(JobOffer.id)).filter(
        JobOffer.company_id == company_id,
        JobOffer.source == source,
        JobOffer.first_seen_at >= one_day_ago
    ).scalar() or 0

    closed = db.query(func.count(JobOffer.id)).filter(
        JobOffer.company_id == company_id,
        JobOffer.source == source,
        JobOffer.closed_at >= one_day_ago
    ).scalar() or 0

    jobs = db.query(JobOffer.job_title).filter(
        JobOffer.company_id == company_id,
        JobOffer.source == source,
        JobOffer.status == "active"
    ).all()

    keywords = {
        "data": ["data", "analytics", "analyst", "bi", "business intelligence"],
        "ai": ["ai", "machine learning", "ml", "llm", "nlp", "deep learning"],
        "automation": ["automation", "rpa", "workflow"],
        "digital": ["digital", "transformation", "cloud", "devops", "infrastructure"]
    }

    domain_counts = {}
    for domain, kws in keywords.items():
        count = sum(
            1 for title, in jobs
            if any(kw.lower() in title.lower() for kw in kws)
        )
        domain_counts[f"{domain}_jobs_count"] = count

    snapshot = CompanyHiringSnapshot(
        company_id=company_id,
        source=source,
        captured_at=captured_at,
        run_id=run_id,
        active_jobs_count=active,
        new_jobs_count=new,
        closed_jobs_count=closed,
        data_jobs_count=domain_counts.get("data_jobs_count", 0),
        ai_jobs_count=domain_counts.get("ai_jobs_count", 0),
        automation_jobs_count=domain_counts.get("automation_jobs_count", 0),
        digital_jobs_count=domain_counts.get("digital_jobs_count", 0)
    )

    db.add(snapshot)
    db.flush()
    return snapshot


def calculate_hiring_signals(db: Session, company_id: int, days: int = 30):
    """Calculate hiring acceleration signals."""
    now = datetime.utcnow()
    days_7 = now - timedelta(days=7)
    days_30 = now - timedelta(days=30)

    active = db.query(func.count(JobOffer.id)).filter(
        JobOffer.company_id == company_id,
        JobOffer.status == "active"
    ).scalar() or 0

    new_7d = db.query(func.count(JobOffer.id)).filter(
        JobOffer.company_id == company_id,
        JobOffer.first_seen_at >= days_7
    ).scalar() or 0

    new_30d = db.query(func.count(JobOffer.id)).filter(
        JobOffer.company_id == company_id,
        JobOffer.first_seen_at >= days_30
    ).scalar() or 0

    closed_30d = db.query(func.count(JobOffer.id)).filter(
        JobOffer.company_id == company_id,
        JobOffer.closed_at >= days_30
    ).scalar() or 0

    if new_30d > 0:
        growth_rate = new_7d / new_30d
    else:
        growth_rate = 0.0

    snapshots = db.query(CompanyHiringSnapshot).filter(
        CompanyHiringSnapshot.company_id == company_id,
        CompanyHiringSnapshot.captured_at >= days_30
    ).order_by(CompanyHiringSnapshot.captured_at).all()

    if len(snapshots) < 2:
        status = "insufficient_history"
    else:
        oldest = snapshots[0]
        current = snapshots[-1]

        if current.active_jobs_count > oldest.active_jobs_count * 1.3:
            status = "accelerating"
        else:
            status = "stable"

    jobs = db.query(JobOffer.job_title).filter(
        JobOffer.company_id == company_id,
        JobOffer.status == "active"
    ).all()

    domain_focus = "general"
    if jobs:
        domain_scores = {}
        for domain, kws in {"data": ["data", "analytics"], "ai": ["ai", "ml"], "automation": ["automation"], "digital": ["cloud", "devops"]}.items():
            score = sum(1 for title, in jobs if any(kw.lower() in title.lower() for kw in kws))
            domain_scores[domain] = score
        if max(domain_scores.values()) > 0:
            domain_focus = max(domain_scores, key=domain_scores.get)

    score = 0
    score += min(new_7d * 5, 30)
    score += min(new_30d * 2, 30) if new_30d > 0 else 0
    score -= min(closed_30d * 5, 20)
    score += min(growth_rate * 40, 20)
    score = max(0, min(100, score))

    return {
        "active_count": active,
        "new_7d": new_7d,
        "new_30d": new_30d,
        "closed_30d": closed_30d,
        "growth_rate": round(growth_rate, 2),
        "domain_focus": domain_focus,
        "acceleration_score": round(score, 1),
        "status": status
    }

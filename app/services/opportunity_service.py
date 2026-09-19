"""Canonical opportunity layer across offers, applications and Gmail events."""
import re
import unicodedata
from datetime import datetime

from sqlalchemy.orm import Session

from app.database.models import Application, EmailEvent, JobOffer, Opportunity, OpportunityEvent, OpportunityLink
from app.services.application_tracking_agent import ApplicationTrackingAgent


STATUS_RANK = {
    "new": 0,
    "sent": 10,
    "acknowledged": 20,
    "reply": 40,
    "interview": 50,
    "rejected": 60,
    "bounced": 60,
    "generated": 30,
}


def normalize(value: str) -> str:
    value = "".join(c for c in unicodedata.normalize("NFKD", (value or "").lower()) if not unicodedata.combining(c))
    value = re.sub(r"[^a-z0-9]+", " ", value).strip()
    return re.sub(r"\s+", " ", value)


def canonical_key(company: str | None, title: str | None, url: str | None = None, thread_id: str | None = None) -> str:
    if url:
        return "url:" + normalize(url)
    company_key = normalize(company or "unknown-company")
    title_key = normalize(title or "unknown-role")
    if company_key != "unknown company" or title_key != "unknown role":
        return f"role:{company_key}:{title_key}"
    return f"thread:{normalize(thread_id or 'unknown-thread')}"


class OpportunityService:
    @staticmethod
    def ensure_for_job_offer(db: Session, offer: JobOffer, owner_id: str) -> Opportunity:
        company = offer.company.name if offer.company else None
        opportunity = OpportunityService._get_or_create(
            db,
            owner_id=owner_id,
            company=company,
            job_title=offer.job_title,
            key=canonical_key(company, offer.job_title, offer.job_url),
            source_primary=offer.source,
            created_from="job_offer",
            status="new",
            activity=offer.created_at,
        )
        OpportunityService._link(db, opportunity, "job_offer", offer.id)
        OpportunityService._event(db, opportunity, "offer_seen", "job_offer", offer.id, offer.job_title, offer.created_at)
        return opportunity

    @staticmethod
    def ensure_for_application(db: Session, application: Application) -> Opportunity:
        opportunity = None
        if application.source_url:
            opportunity = OpportunityService._find_by_linked_offer_url(db, application.telegram_user_id, application.source_url)
        if opportunity is None:
            opportunity = OpportunityService._get_or_create(
                db,
                owner_id=application.telegram_user_id,
                company=application.company,
                job_title=application.job_title,
                key=canonical_key(application.company, application.job_title, application.source_url),
                source_primary="manual" if not application.source_url else "application",
                created_from="application",
                status="new",
                activity=application.updated_at or application.created_at,
            )
        OpportunityService._link(db, opportunity, "application", application.id)
        OpportunityService._event(db, opportunity, "application_saved", "application", application.id, application.job_title, application.updated_at or application.created_at)
        return opportunity

    @staticmethod
    def ensure_for_email_event(db: Session, event: EmailEvent) -> Opportunity:
        existing = OpportunityService._find_by_source(db, "email_event", event.id)
        if existing:
            return existing
        linked = None
        if event.thread_id:
            linked = (
                db.query(Opportunity)
                .join(OpportunityLink, OpportunityLink.opportunity_id == Opportunity.id)
                .join(EmailEvent, EmailEvent.id == OpportunityLink.source_id)
                .filter(Opportunity.owner_id == event.owner_id, OpportunityLink.source_type == "email_event", EmailEvent.thread_id == event.thread_id)
                .first()
            )
        info = ApplicationTrackingAgent.classify(event)
        opportunity = linked or OpportunityService._get_or_create(
            db,
            owner_id=event.owner_id,
            company=info.get("company") or ApplicationTrackingAgent._extract_company(event.subject or "", event.body_text or "", event.sender_email or ""),
            job_title=info.get("job_title") or ApplicationTrackingAgent._extract_job_title(event.subject or ""),
            key=canonical_key(info.get("company"), info.get("job_title"), None, event.thread_id),
            source_primary=info.get("source") or "gmail",
            created_from="gmail",
            status=OpportunityService._status_from_email_label(info["label"]),
            activity=event.received_at,
        )
        OpportunityService._link(db, opportunity, "email_event", event.id, 90)
        OpportunityService._event(db, opportunity, info["label"], "email_event", event.id, event.subject, event.received_at, 90)
        OpportunityService._promote_status(opportunity, OpportunityService._status_from_email_label(info["label"]))
        if event.received_at and (not opportunity.last_activity_at or event.received_at > opportunity.last_activity_at):
            opportunity.last_activity_at = event.received_at
        return opportunity

    @staticmethod
    def _get_or_create(db: Session, *, owner_id: str, company: str | None, job_title: str | None, key: str, source_primary: str | None, created_from: str, status: str, activity: datetime | None) -> Opportunity:
        row = db.query(Opportunity).filter(Opportunity.owner_id == owner_id, Opportunity.canonical_key == key).first()
        if row is None:
            row = Opportunity(owner_id=owner_id, company=company, job_title=job_title, canonical_key=key, source_primary=source_primary, created_from=created_from, status=status, last_activity_at=activity)
            db.add(row)
            db.flush()
        else:
            row.company = row.company or company
            row.job_title = row.job_title or job_title
            row.source_primary = row.source_primary or source_primary
            if activity and (not row.last_activity_at or activity > row.last_activity_at):
                row.last_activity_at = activity
            OpportunityService._promote_status(row, status)
        return row

    @staticmethod
    def _find_by_source(db: Session, source_type: str, source_id: int) -> Opportunity | None:
        return db.query(Opportunity).join(OpportunityLink).filter(OpportunityLink.source_type == source_type, OpportunityLink.source_id == source_id).first()

    @staticmethod
    def _find_by_linked_offer_url(db: Session, owner_id: str, source_url: str) -> Opportunity | None:
        offer = db.query(JobOffer).filter(JobOffer.job_url == source_url).first()
        if not offer:
            return None
        return (
            db.query(Opportunity)
            .join(OpportunityLink)
            .filter(Opportunity.owner_id == owner_id, OpportunityLink.source_type == "job_offer", OpportunityLink.source_id == offer.id)
            .first()
        )

    @staticmethod
    def _link(db: Session, opportunity: Opportunity, source_type: str, source_id: int, confidence: int = 100) -> None:
        if not db.query(OpportunityLink).filter_by(source_type=source_type, source_id=source_id).first():
            db.add(OpportunityLink(opportunity_id=opportunity.id, source_type=source_type, source_id=source_id, confidence=confidence))

    @staticmethod
    def _event(db: Session, opportunity: Opportunity, event_type: str, source_type: str, source_id: int, summary: str | None, occurred_at: datetime | None, confidence: int = 100) -> None:
        exists = db.query(OpportunityEvent).filter_by(opportunity_id=opportunity.id, event_type=event_type, source_type=source_type, source_id=source_id).first()
        if not exists:
            db.add(OpportunityEvent(opportunity_id=opportunity.id, event_type=event_type, source_type=source_type, source_id=source_id, summary=(summary or "")[:500], occurred_at=occurred_at, confidence=confidence))

    @staticmethod
    def _promote_status(opportunity: Opportunity, status: str) -> None:
        if STATUS_RANK.get(status, 0) >= STATUS_RANK.get(opportunity.status or "new", 0):
            opportunity.status = status

    @staticmethod
    def _status_from_email_label(label: str) -> str:
        return {
            "cold_email": "sent",
            "application_sent": "sent",
            "application_ack": "acknowledged",
            "acknowledgement": "acknowledged",
            "recruiter_reply": "reply",
            "interview_or_test": "interview",
            "interview_request": "interview",
            "rejection": "rejected",
            "bounce": "bounced",
            "job_board_alert": "new",
        }.get(label, "new")

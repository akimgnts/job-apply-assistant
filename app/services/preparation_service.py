"""Idempotent preparation, reusing the existing analysis and document pipeline."""
import asyncio
from weakref import WeakValueDictionary
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.database.models import Application, ApplicationStatusEnum, Company, CompanyContact, JobOffer, JobAnalysis, GeneratedDocument
from app.web import service as svc

_locks = WeakValueDictionary()
EARLY_STATUSES = {'saved', 'analyzed', 'generated'}
DOCUMENT_TYPES = ['cv', 'letter', 'mail']


def application_lock(identifier):
    return _locks.setdefault(identifier, asyncio.Lock())


def save_offer(db: Session, identifier: int) -> Application:
    offer = svc.get_offer(db, identifier)
    db.query(JobOffer).filter(JobOffer.id == identifier).with_for_update().first()
    row = svc.applications(db).filter(Application.source_url == offer.job_url).first()
    if row is None:
        row = Application(telegram_user_id=svc.user_id(), company=offer.company.name,
                          job_title=offer.job_title, source_url=offer.job_url,
                          raw_offer=offer.raw_text or offer.job_title,
                          status=ApplicationStatusEnum.saved, job_offer_id=offer.id)
        db.add(row)
    elif row.job_offer_id is None:
        row.job_offer_id = offer.id
    svc.commit(db)
    return row


def import_daily_offer(db: Session, data: dict) -> Application:
    """Persist a source-verified daily offer, keeping its original ID and URL."""
    url = data['business_france_url']
    offer = db.query(JobOffer).filter(JobOffer.job_url == url).first()
    if offer is None:
        company = db.query(Company).filter(func.lower(Company.name) == data['company'].lower()).first()
        if company is None:
            company = Company(name=data['company']); db.add(company); db.flush()
        from datetime import datetime
        posted = data.get('broadcast_date')
        try:
            posted = datetime.fromisoformat(posted.replace('Z', '+00:00')).replace(tzinfo=None) if posted else None
        except ValueError:
            posted = None
        offer = JobOffer(company_id=company.id, job_title=data['title'], job_url=url,
                         source='business_france', raw_text='\n\n'.join(filter(None, [data.get('description'), data.get('profile')])),
                         posted_date=posted)
        db.add(offer); db.flush()
    contact = data.get('contact') or {}
    if contact.get('name') or contact.get('email'):
        exists = db.query(CompanyContact).filter(
            CompanyContact.company_id == offer.company_id,
            func.lower(CompanyContact.contact_name) == (contact.get('name') or 'Contact Business France').lower(),
            CompanyContact.email == contact.get('email'),
        ).first()
        if exists is None:
            db.add(CompanyContact(company_id=offer.company_id,
                contact_name=contact.get('name') or 'Contact Business France',
                role_raw='Contact Business France',
                email=contact.get('email'),
                source_url=contact.get('source_url') or url,
                data_source=contact.get('source') or 'business_france',
                verification_status='pending'))
    svc.commit(db)
    return save_offer(db, offer.id)


def ready_document_types(db, identifier):
    return {doc.document_type.value for doc in svc.documents(db).filter(GeneratedDocument.application_id == identifier).all()
            if doc.content and doc.content.strip()}


async def generate_documents(identifier, payload, db):
    from app.web.api import generate
    return await generate(identifier, payload, db)


async def prepare_application(db: Session, identifier: int) -> dict:
    async with application_lock(identifier):
        row = svc.get_application(db, identifier)
        original_status = row.status
        if not db.query(JobAnalysis).filter(JobAnalysis.application_id == identifier).first():
            from app.web.api import analyze
            await analyze(identifier, db)
        missing = [kind for kind in DOCUMENT_TYPES if kind not in ready_document_types(db, identifier)]
        result = {'status': 'full_success', 'errors': {}}
        if missing:
            from app.web.api import GenerationInput
            result = await generate_documents(identifier, GenerationInput(document_types=missing), db)
        missing = [kind for kind in DOCUMENT_TYPES if kind not in ready_document_types(db, identifier)]
        # A preparation retry never undoes a sent candidacy or a received response.
        if original_status.value not in EARLY_STATUSES:
            row.status = original_status
        elif not missing:
            row.status = ApplicationStatusEnum.generated
        elif row.status == ApplicationStatusEnum.generated:
            row.status = ApplicationStatusEnum.analyzed
        svc.commit(db)
        from app.services.application_workflow_service import serialize_application
        return {'status': 'full_success' if not missing else result.get('status', 'partial_success'),
                'errors': result.get('errors', {}), 'missing': missing,
                'application': serialize_application(db, row, detail=True)}

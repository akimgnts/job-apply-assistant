"""Authenticated workspace API; authentication is applied by the application middleware."""
import os
import re
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.config import config
from app.database.db import get_db
from app.database.models import (Application, ApplicationStatusEnum, Company, CompanyContact,
    JobOffer, JobAnalysis, GeneratedDocument, ProfileBlock, CareerIntelligenceSnapshot, OutreachDraft,
    Opportunity, OpportunityEvent, OpportunityLink)
from app.services.opportunity_service import OpportunityService
from app.services.offer_signal_service import OfferSignalService
from app.web import service as svc

router = APIRouter(prefix='/api')
Page = Query(1, ge=1)
PageSize = Query(25, ge=1, le=100)


class ApplicationInput(BaseModel):
    raw_offer: str = Field(min_length=1, max_length=100000)
    company: str | None = Field(None, max_length=255)
    job_title: str | None = Field(None, max_length=255)
    source_url: str | None = Field(None, max_length=2000)

    @field_validator('raw_offer')
    @classmethod
    def not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError('Collez le texte de l’offre.')
        return value.strip()

    @field_validator('source_url')
    @classmethod
    def safe_url(cls, value: str | None) -> str | None:
        if value and (urlsplit(value).scheme not in ('http', 'https') or not urlsplit(value).hostname or any(c.isspace() for c in value)):
            raise ValueError('Une URL HTTP ou HTTPS est requise.')
        return value or None


class StatusInput(BaseModel):
    status: ApplicationStatusEnum


class GenerationInput(BaseModel):
    document_types: list[Literal['cv', 'letter', 'mail']] = Field(default_factory=lambda: ['cv', 'letter', 'mail'], min_length=1, max_length=3)


def require_ai() -> None:
    if not config.OPENAI_API_KEY:
        raise HTTPException(503, 'L’IA n’est pas configurée. Ajoutez OPENAI_API_KEY dans votre fichier .env puis redémarrez le serveur.')


@router.get('/overview')
def overview(db: Session = Depends(get_db)) -> dict:
    applications = svc.applications(db)
    return {'counts': {'offers': db.query(JobOffer).count(), 'active_offers': db.query(JobOffer).filter(JobOffer.status == 'active').count(), 'archived_offers': db.query(JobOffer).filter(JobOffer.status.in_(['archived', 'closed'])).count(), 'applications': applications.count(), 'documents': svc.documents(db).count(), 'companies': db.query(Company).count(), 'profile_blocks': db.query(ProfileBlock).count()},
            'statuses': {status.value: applications.filter(Application.status == status).count() for status in ApplicationStatusEnum},
            'recent_applications': [svc.application_data(db, row) for row in applications.order_by(Application.id.desc()).limit(5)],
            'sources': [{'source': source, 'count': count} for source, count in db.query(JobOffer.source, func.count(JobOffer.id)).group_by(JobOffer.source).all()], 'ai_available': bool(config.OPENAI_API_KEY)}


@router.get('/offers')
def offers(q: str | None = None, source: str | None = None, status: Literal['active', 'archived', 'closed', 'all'] = 'active', signal: str | None = None, hours: int | None = Query(None, ge=1, le=720), sort: Literal['recent', 'relevance'] = 'recent', page: int = Page, page_size: int = PageSize, db: Session = Depends(get_db)) -> dict:
    query = svc.search(db.query(JobOffer).join(Company), q, JobOffer.job_title, Company.name, JobOffer.raw_text)
    if source:
        query = query.filter(JobOffer.source == source)
    if status == 'archived':
        query = query.filter(JobOffer.status.in_(['archived', 'closed']))
    elif status != 'all':
        query = query.filter(JobOffer.status == status)
    rows = query.order_by(JobOffer.created_at.desc(), JobOffer.id.desc()).all()
    if hours is not None:
        rows = [row for row in rows if OfferSignalService.is_recent(row, hours / 24)]
    scored = [(row, OfferSignalService.score(row)) for row in rows]
    if signal == 'target':
        scored = [(row, meta) for row, meta in scored if meta['score'] >= 45]
    elif signal in {'priority', 'potential', 'noise'}:
        scored = [(row, meta) for row, meta in scored if meta['tier'] == signal]
    elif signal == 'recent':
        scored = [(row, meta) for row, meta in scored if meta['recency'] == 'new']
    from datetime import datetime
    def rank(item):
        row, meta = item
        date = OfferSignalService.reference_date(row) or datetime.min
        return (meta['score'], date, row.id) if sort == 'relevance' else (date, meta['score'], row.id)
    scored.sort(key=rank, reverse=True)
    total = len(scored)
    selected = scored[(page - 1) * page_size: page * page_size]
    return {'items': [svc.offer_data(db, row) for row, _ in selected], 'total': total, 'page': page, 'page_size': page_size}


@router.get('/offers/{identifier}')
def offer(identifier: int, db: Session = Depends(get_db)) -> dict:
    return svc.offer_data(db, svc.get_offer(db, identifier))


@router.post('/offers/{identifier}/direct-source')
async def direct_source(identifier: int, db: Session = Depends(get_db)) -> dict:
    from app.services.direct_source_finder import DirectSourceFinder
    row = svc.get_offer(db, identifier)
    return await DirectSourceFinder.find(company=row.company.name, title=row.job_title, original_url=row.job_url)


@router.post('/offers/{identifier}/save')
def save_offer(identifier: int, db: Session = Depends(get_db)) -> dict:
    offer = svc.get_offer(db, identifier)
    # Lock the shared source row so concurrent PostgreSQL requests cannot duplicate a save.
    db.query(JobOffer).filter(JobOffer.id == identifier).with_for_update().first()
    row = svc.applications(db).filter(Application.source_url == offer.job_url).first()
    if row is None:
        row = Application(telegram_user_id=svc.user_id(), company=offer.company.name, job_title=offer.job_title, source_url=offer.job_url, raw_offer=offer.raw_text or offer.job_title, status=ApplicationStatusEnum.saved)
        db.add(row)
        db.flush()
    OpportunityService.ensure_for_job_offer(db, offer, svc.user_id())
    OpportunityService.ensure_for_application(db, row)
    if row is not None:
        svc.commit(db)
    return svc.application_data(db, row, True)


@router.get('/applications')
def applications(q: str | None = None, status: ApplicationStatusEnum | None = None, preparing: bool = False, page: int = Page, page_size: int = PageSize, db: Session = Depends(get_db)) -> dict:
    query = svc.search(svc.applications(db), q, Application.company, Application.job_title, Application.raw_offer)
    if status:
        query = query.filter(Application.status == status)
    if preparing:
        query = query.filter(Application.status.in_([ApplicationStatusEnum.saved, ApplicationStatusEnum.analyzed, ApplicationStatusEnum.generated]))
    return svc.paginate(query.order_by(Application.updated_at.desc(), Application.id.desc()), page, page_size, lambda row: svc.application_data(db, row))


@router.post('/applications', status_code=201)
def create_application(payload: ApplicationInput, db: Session = Depends(get_db)) -> dict:
    row = Application(**payload.model_dump(), telegram_user_id=svc.user_id(), status=ApplicationStatusEnum.saved)
    db.add(row)
    db.flush()
    OpportunityService.ensure_for_application(db, row)
    svc.commit(db)
    return svc.application_data(db, row, True)


@router.get('/opportunities')
def opportunities(q: str | None = None, status: str | None = None, page: int = Page, page_size: int = PageSize, db: Session = Depends(get_db)) -> dict:
    query = svc.search(db.query(Opportunity).filter(Opportunity.owner_id == svc.user_id()), q, Opportunity.company, Opportunity.job_title)
    if status:
        query = query.filter(Opportunity.status == status)

    def row_data(row: Opportunity) -> dict:
        links = db.query(OpportunityLink).filter(OpportunityLink.opportunity_id == row.id).all()
        events = db.query(OpportunityEvent).filter(OpportunityEvent.opportunity_id == row.id).order_by(OpportunityEvent.occurred_at.desc().nullslast(), OpportunityEvent.id.desc()).limit(8).all()
        data = svc.serialize(row)
        data['links'] = [svc.serialize(link, ('opportunity_id',)) for link in links]
        data['events'] = [svc.serialize(event, ('opportunity_id',)) for event in events]
        data['email_count'] = sum(1 for link in links if link.source_type == 'email_event')
        data['offer_count'] = sum(1 for link in links if link.source_type == 'job_offer')
        data['application_count'] = sum(1 for link in links if link.source_type == 'application')
        return data

    return svc.paginate(query.order_by(Opportunity.last_activity_at.desc().nullslast(), Opportunity.updated_at.desc()), page, page_size, row_data)


@router.get('/applications/{identifier}')
def application(identifier: int, db: Session = Depends(get_db)) -> dict:
    return svc.application_data(db, svc.get_application(db, identifier), True)


@router.patch('/applications/{identifier}')
def change_status(identifier: int, payload: StatusInput, db: Session = Depends(get_db)) -> dict:
    row = svc.get_application(db, identifier)
    row.status = payload.status
    svc.commit(db)
    return svc.application_data(db, row, True)


@router.post('/applications/{identifier}/analyze')
async def analyze(identifier: int, db: Session = Depends(get_db)) -> dict:
    row = svc.get_application(db, identifier)
    if not config.OPENAI_API_KEY:
        analysis = OfferSignalService.analyze_application(row)
        positioning = analysis.get('positioning') or {}
        db.add(JobAnalysis(application_id=row.id, analysis_json=analysis, **{key: analysis.get(key, []) for key in ('missions', 'required_skills', 'soft_skills', 'ats_keywords', 'missing_points', 'strengths')}))
        row.match_score = analysis.get('match_score')
        row.recommended_angle = positioning.get('positioning')
        row.status = ApplicationStatusEnum.analyzed
        svc.commit(db)
        return svc.application_data(db, row, True)
    try:
        from app.agents.analysis_agent import AnalysisAgent
        from app.agents.matching_agent import MatchingAgent
        from app.agents.positioning_agent import PositioningAgent
        analysis = MatchingAgent.enrich_analysis(await AnalysisAgent.analyze(db, row.raw_offer), db)
        positioning = await PositioningAgent.choose_angle(analysis)
        analysis['positioning'] = positioning
        db.add(JobAnalysis(application_id=row.id, analysis_json=analysis, **{key: analysis.get(key, []) for key in ('missions', 'required_skills', 'soft_skills', 'ats_keywords', 'missing_points', 'strengths')}))
        row.company = analysis.get('company') or row.company
        row.job_title = analysis.get('job_title') or row.job_title
        score = analysis.get('match_score')
        row.match_score = int(score) if isinstance(score, (int, float)) and 0 <= score <= 10 else None
        row.recommended_angle = positioning.get('positioning')
        row.status = ApplicationStatusEnum.analyzed
        svc.commit(db)
    except HTTPException:
        raise
    except Exception:
        db.rollback()
        raise HTTPException(502, 'L’analyse a échoué. Vérifiez la connexion et la configuration IA puis réessayez.') from None
    return svc.application_data(db, row, True)


@router.post('/applications/{identifier}/generate')
async def generate(identifier: int, payload: GenerationInput, db: Session = Depends(get_db)) -> dict:
    row = svc.get_application(db, identifier)
    require_ai()
    analysis = db.query(JobAnalysis).filter(JobAnalysis.application_id == identifier).order_by(JobAnalysis.id.desc()).first()
    if analysis is None:
        raise HTTPException(409, 'Analysez cette candidature avant de générer des documents.')
    try:
        from app.agents.generation_agent import GenerationAgent
        result = await GenerationAgent.generate_documents(db, application_id=row.id, analysis=analysis.analysis_json, positioning=row.recommended_angle or '', document_types=list(dict.fromkeys(payload.document_types)), skill_profile=(analysis.analysis_json.get('positioning') or {}).get('skill_profile', 'general_business_data'), telegram_user_id=svc.user_id())
        successful = any(result.get('documents', {}).values())
        if successful:
            row.status = ApplicationStatusEnum.generated
            svc.commit(db)
        else:
            db.rollback()
        errors = {key: 'Génération impossible. Réessayez après vérification de la configuration IA.' if value else None for key, value in result.get('errors', {}).items()}
        return {'status': result.get('status', 'full_failure'), 'errors': errors, 'application': svc.application_data(db, row, True)}
    except HTTPException:
        raise
    except Exception:
        db.rollback()
        raise HTTPException(502, 'La génération a échoué. Vérifiez la configuration IA puis réessayez.') from None


@router.get('/documents')
def documents(q: str | None = None, page: int = Page, page_size: int = PageSize, db: Session = Depends(get_db)) -> dict:
    query = svc.search(svc.documents(db), q, GeneratedDocument.filename, Application.company, Application.job_title)
    return svc.paginate(query.order_by(GeneratedDocument.id.desc()), page, page_size, svc.document_data)


@router.get('/documents/{identifier}')
def document(identifier: int, db: Session = Depends(get_db)) -> dict:
    return svc.document_data(svc.get_document(db, identifier), True)


@router.get('/documents/{identifier}/download')
def download(identifier: int, db: Session = Depends(get_db)) -> Response:
    doc = svc.get_document(db, identifier)
    filename = re.sub(r'[^a-zA-Z0-9._-]', '_', Path(doc.filename).name).lstrip('.') or f'document-{doc.id}.txt'
    return Response(doc.content, media_type='text/plain' if doc.document_type.value == 'mail' else 'text/html', headers={'Content-Disposition': f'attachment; filename="{filename}"', 'X-Content-Type-Options': 'nosniff', 'Content-Security-Policy': "sandbox; default-src 'none'; style-src 'unsafe-inline'"})


@router.get('/companies')
def companies(q: str | None = None, page: int = Page, page_size: int = PageSize, db: Session = Depends(get_db)) -> dict:
    query = svc.search(db.query(Company), q, Company.name)
    return svc.paginate(query.order_by(Company.name), page, page_size, lambda row: {**svc.serialize(row), 'offer_count': db.query(JobOffer).filter(JobOffer.company_id == row.id).count(), 'contact_count': db.query(CompanyContact).filter(CompanyContact.company_id == row.id).count()})


@router.get('/contacts')
def contacts(q: str | None = None, page: int = Page, page_size: int = PageSize, db: Session = Depends(get_db)) -> dict:
    query = db.query(CompanyContact).join(Company).filter(CompanyContact.verification_status != 'invalid')
    query = svc.search(query, q, Company.name, CompanyContact.contact_name, CompanyContact.role_raw)
    return svc.paginate(query.order_by(CompanyContact.updated_at.desc(), CompanyContact.id.desc()), page, page_size,
                        lambda row: {**svc.serialize(row), 'company': row.company.name})


@router.get('/companies/{identifier}')
def company(identifier: int, db: Session = Depends(get_db)) -> dict:
    row = db.get(Company, identifier)
    if row is None:
        raise HTTPException(404, 'Entreprise introuvable.')
    return {**svc.serialize(row), 'offers': [svc.offer_data(db, offer) for offer in row.job_offers], 'contacts': [svc.serialize(contact) for contact in row.contacts]}


@router.get('/profile')
def profile(db: Session = Depends(get_db)) -> dict:
    from app.services.master_cv_service import load_master_cv
    try:
        master = load_master_cv()
    except (ValueError, FileNotFoundError):
        master = None
    return {'blocks': [svc.serialize(row) for row in db.query(ProfileBlock).order_by(ProfileBlock.priority.desc()).all()], 'master_cv': master}


@router.get('/intelligence')
def intelligence(db: Session = Depends(get_db)) -> dict:
    from app.services.career_action_plan_service import CareerActionPlanService
    snapshot = db.query(CareerIntelligenceSnapshot).filter(CareerIntelligenceSnapshot.telegram_user_id == svc.user_id()).order_by(CareerIntelligenceSnapshot.id.desc()).first()
    data = CareerActionPlanService.build(db, svc.user_id())
    data['latest_snapshot'] = svc.serialize(snapshot) if snapshot else None
    return data


@router.get('/settings')
def settings(db: Session = Depends(get_db)) -> dict:
    return {'ai_configured': bool(config.OPENAI_API_KEY), 'telegram_configured': bool(config.TELEGRAM_BOT_TOKEN), 'database_backend': db.bind.dialect.name, 'web_user_id': svc.user_id(), 'access_protected': bool(os.getenv('WEB_ACCESS_TOKEN')), 'snapshot_available': (config.PROJECT_ROOT / 'exports' / 'ats_job_offers_live.csv').exists()}


@router.post('/import-snapshot')
def import_snapshot(db: Session = Depends(get_db)) -> dict:
    from app.web.bootstrap import import_snapshot as run_import
    try:
        return run_import(db)
    except Exception:
        db.rollback()
        raise HTTPException(503, 'Import des archives impossible. Vérifiez le fichier CSV et la base de données.') from None


class ContactInput(BaseModel):
    contact_name: str = Field(min_length=1, max_length=255)
    role_raw: str = Field(min_length=1, max_length=255)
    email: str | None = Field(None, max_length=255)
    linkedin_url: str | None = Field(None, max_length=500)
    source_url: str = Field(min_length=1, max_length=500)

    @field_validator('contact_name', 'role_raw')
    @classmethod
    def not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError('Ce champ est obligatoire.')
        return value.strip()

    @field_validator('linkedin_url', 'source_url')
    @classmethod
    def safe_url(cls, value: str | None) -> str | None:
        return ApplicationInput.safe_url(value)

    @field_validator('email')
    @classmethod
    def valid_email(cls, value: str | None) -> str | None:
        if value and not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', value):
            raise ValueError('Saisissez une adresse e-mail valide.')
        return value or None


class ContactVerificationInput(BaseModel):
    verification_status: Literal['verified', 'pending', 'invalid']


class OutreachInput(BaseModel):
    company_id: int = Field(gt=0)
    contact_id: int = Field(gt=0)
    job_offer_ids: list[int] = Field(default_factory=list, max_length=20)
    channel: Literal['email', 'linkedin'] = 'email'


def outreach_data(row: OutreachDraft) -> dict:
    return {**svc.serialize(row), 'company': row.company.name, 'contact_name': row.contact.contact_name}


@router.post('/companies/{identifier}/contacts', status_code=201)
def create_contact(identifier: int, payload: ContactInput, db: Session = Depends(get_db)) -> dict:
    """Save a sourced contact for explicit review; never infer verification."""
    if db.get(Company, identifier) is None:
        raise HTTPException(404, 'Entreprise introuvable.')
    row = CompanyContact(company_id=identifier, **payload.model_dump(), data_source='manual', verification_status='pending')
    db.add(row)
    svc.commit(db)
    return svc.serialize(row)


@router.patch('/companies/{identifier}/contacts/{contact_id}')
def verify_contact(identifier: int, contact_id: int, payload: ContactVerificationInput, db: Session = Depends(get_db)) -> dict:
    """Persist the user's explicit source review decision."""
    row = db.query(CompanyContact).filter(CompanyContact.id == contact_id, CompanyContact.company_id == identifier).first()
    if row is None:
        raise HTTPException(404, 'Contact introuvable pour cette entreprise.')
    row.verification_status = payload.verification_status
    svc.commit(db)
    return svc.serialize(row)


@router.get('/outreach')
def outreach(q: str | None = None, status: str | None = None, company_id: int | None = None, page: int = Page, page_size: int = PageSize, db: Session = Depends(get_db)) -> dict:
    query = svc.search(db.query(OutreachDraft).join(Company).join(CompanyContact, OutreachDraft.contact_id == CompanyContact.id), q, Company.name, CompanyContact.contact_name, OutreachDraft.subject_line, OutreachDraft.message_text)
    if status:
        query = query.filter(OutreachDraft.status == status)
    if company_id:
        query = query.filter(OutreachDraft.company_id == company_id)
    return svc.paginate(query.order_by(OutreachDraft.id.desc()), page, page_size, outreach_data)


@router.post('/outreach', status_code=201)
async def create_outreach(payload: OutreachInput, db: Session = Depends(get_db)) -> dict:
    """Generate a grounded draft for a reviewed contact, without sending anything."""
    if db.get(Company, payload.company_id) is None:
        raise HTTPException(404, 'Entreprise introuvable.')
    contact = db.get(CompanyContact, payload.contact_id)
    if contact is None or contact.company_id != payload.company_id:
        raise HTTPException(422, 'Le contact doit appartenir à cette entreprise.')
    if contact.verification_status != 'verified':
        raise HTTPException(409, 'Vérifiez la source du contact avant de préparer un brouillon.')
    offer_ids = list(dict.fromkeys(payload.job_offer_ids))
    count = db.query(JobOffer).filter(JobOffer.id.in_(offer_ids), JobOffer.company_id == payload.company_id).count()
    if count != len(offer_ids):
        raise HTTPException(422, 'Toutes les offres doivent appartenir à cette entreprise.')
    require_ai()
    try:
        from app.services.outreach_draft_service import OutreachDraftService
        draft = await OutreachDraftService.create_draft(db, company_id=payload.company_id, contact_id=payload.contact_id, job_offer_ids=offer_ids, channel=payload.channel)
        return outreach_data(draft)
    except Exception:
        db.rollback()
        raise HTTPException(502, 'La préparation du brouillon a échoué. Vérifiez la configuration IA et réessayez.') from None

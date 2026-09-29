"""Application lifecycle with auditable actions and conservative read-only Gmail sync."""
import fcntl
import hashlib
import os
import tempfile
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import quote

from app.config import config
from app.database.models import (Application, ApplicationEvent, ApplicationStatusEnum,
    CompanyContact, EmailEvent, GeneratedDocument, GmailSyncState, JobAnalysis,
    JobOffer, OutreachTracking)
from app.services.email_tracking_service import classify_email, match_application
from app.services.gmail_service import GmailService, GmailUnavailable

LABELS = {'analyzed':'À préparer', 'generated':'Documents prêts', 'saved':'Enregistrée',
    'applied':'Candidature envoyée', 'received':'Accusé de réception', 'replied':'Réponse reçue',
    'interview':'Entretien', 'rejected':'Refus', 'archived':'Archivée'}
EMAIL_STATUS = {'acknowledgement':'received', 'received':'received', 'recruiter_reply':'replied',
    'replied':'replied', 'interview_request':'interview', 'interview':'interview',
    'rejection':'rejected', 'rejected':'rejected'}
DEFAULT_QUERY = 'newer_than:90d {candidature recrutement entretien application interview recruiting recruiter} -category:promotions -category:social'


def setting(name, default=None):
    return os.environ.get(name, getattr(config, name, default))


def owner_id():
    return str(setting('GMAIL_APPLICATION_USER_ID', os.getenv('WEB_USER_ID', 'local')))


def iso(value):
    return value.isoformat() + 'Z' if value else None


def applications(db):
    return db.query(Application).filter(Application.telegram_user_id == owner_id())


def get_application(db, identifier):
    app = applications(db).filter(Application.id == identifier).first()
    if app is None:
        raise LookupError('Candidature introuvable.')
    return app


def status_value(app):
    return app.status.value if hasattr(app.status, 'value') else app.status


def _tracks(db, app):
    return db.query(OutreachTracking).filter_by(application_id=app.id).order_by(OutreachTracking.id.desc()).all()


def _transition(db, app, status, at, source='manual', email=None):
    previous = status_value(app)
    if previous == status:
        return False
    app.status = ApplicationStatusEnum(status)
    app.status_updated_at = at
    if status == 'applied' and not app.applied_at:
        app.applied_at = at
    tracks = _tracks(db, app)
    if status == 'applied' and not tracks:
        track = OutreachTracking(application_id=app.id, outreach_type='email', status='pending',
            outreach_date=app.applied_at, last_follow_up=app.applied_at, next_follow_up=app.applied_at + timedelta(days=7))
        db.add(track)
        tracks = [track]
    for track in tracks:
        if status == 'applied' and not track.outreach_date:
            track.outreach_date = app.applied_at
            track.last_follow_up = app.applied_at
            track.next_follow_up = app.applied_at + timedelta(days=track.reminder_interval_days or 7)
        elif status in ('replied', 'interview', 'rejected'):
            # An application response cannot identify which of several contacts replied.
            track.next_follow_up = None
            if len(tracks) == 1:
                track.response_received = 1
                track.response_date = at
                track.response_message = email.body_text if email else track.response_message
                track.response_sentiment = {'replied':'neutral','interview':'positive','rejected':'negative'}[status]
                track.status = {'replied':'responded','interview':'interview','rejected':'rejected'}[status]
        elif status == 'archived':
            track.next_follow_up = None
            track.status = 'archived'
    db.add(ApplicationEvent(application_id=app.id, email_event_id=email.id if email else None,
        event_type='status_changed', previous_status=previous, new_status=status, source=source,
        detail=LABELS[status], created_at=at))
    return True


def set_application_status(db, application_id, status):
    if status not in LABELS:
        raise ValueError('Statut de candidature invalide.')
    app = get_application(db, application_id)
    _transition(db, app, status, datetime.utcnow())
    db.commit()
    return app


def _apply_email(db, event, app, method='manual', confidence=100):
    if event.application_id and event.application_id != app.id:
        raise ValueError('Ce message est déjà associé à une autre candidature.')
    if db.query(ApplicationEvent).filter_by(email_event_id=event.id).first():
        return
    event.application_id, event.link_method, event.match_confidence = app.id, method, confidence
    event.status = 'processed'
    target = EMAIL_STATUS.get(event.confirmed_type or event.detected_type)
    current = status_value(app)
    at = event.received_at or datetime.utcnow()
    # Old messages and low-information receipts never overwrite newer decisions.
    allowed = bool(target and event.received_at and current not in ('archived', 'rejected'))
    if current == 'interview' and target in ('received', 'replied'):
        allowed = False
    if current == 'replied' and target == 'received':
        allowed = False
    if app.status_updated_at and at < app.status_updated_at:
        allowed = False
    if 'SENT' in (event.labels or []) or event.sender_email == event.mailbox:
        allowed = False
    changed = allowed and _transition(db, app, target, at, 'gmail', event)
    if not changed:
        db.add(ApplicationEvent(application_id=app.id, email_event_id=event.id, event_type='email_linked',
            previous_status=current, new_status=current, source='gmail',
            detail='Message associé : ' + (event.subject or '')[:500], created_at=at))


def link_email(db, email_id, application_id):
    event = db.query(EmailEvent).filter_by(id=email_id, owner_id=owner_id()).first()
    if not event:
        raise LookupError('Message introuvable.')
    app = get_application(db, application_id)
    _apply_email(db, event, app)
    db.commit()
    return event


def serialize_email(event, detail=False):
    result = {key:getattr(event,key) for key in ('id','application_id','sender_email','sender_name','subject','snippet','link_method','match_confidence','status')}
    result.update(classification=event.confirmed_type or event.detected_type,
        classification_reason=event.classification_reason, received_at=iso(event.received_at),
        gmail_thread_id=event.thread_id,
        gmail_url=f'https://mail.google.com/mail/u/?authuser={quote(event.mailbox)}#all/{quote(event.thread_id or event.gmail_message_id, safe="")}')
    if detail:
        result['body_text'] = event.body_text
    return result


def serialize_application(db, app, detail=False):
    status = status_value(app)
    documents = db.query(GeneratedDocument).filter_by(application_id=app.id, telegram_user_id=app.telegram_user_id).order_by(GeneratedDocument.id.desc()).all()
    emails = db.query(EmailEvent).filter_by(application_id=app.id, owner_id=app.telegram_user_id).order_by(EmailEvent.received_at.desc()).all()
    tracks = _tracks(db, app)
    due = min((t.next_follow_up for t in tracks if t.next_follow_up), default=None)
    action = {'analyzed':'Préparer le CV et la lettre', 'saved':'Préparer le CV et la lettre',
        'generated':'Envoyer la candidature puis confirmer l’envoi', 'applied':'Attendre la réponse',
        'received':'Attendre une réponse du recruteur', 'replied':'Lire la réponse et préparer la suite',
        'interview':'Préparer l’entretien', 'rejected':'Poursuivre les autres candidatures', 'archived':'Aucune action'}[status]
    follow_up_due = bool(due and due <= datetime.utcnow() and status in ('applied','received'))
    if follow_up_due:
        action = 'Préparer une relance'
    result = dict(id=app.id, company=app.company, job_title=app.job_title, source_url=app.source_url,
        job_offer_id=app.job_offer_id, status=status, status_label=LABELS[status], match_score=app.match_score,
        documents=[{'id':d.id,'type':d.document_type.value,'filename':d.filename,'url':f'/api/documents/{d.id}/download'} for d in documents],
        next_action=action, follow_up_due=follow_up_due, next_follow_up=iso(due),
        applied_at=iso(app.applied_at), created_at=iso(app.created_at), updated_at=iso(app.updated_at), email_count=len(emails))
    if detail:
        analyses = db.query(JobAnalysis).filter_by(application_id=app.id).order_by(JobAnalysis.id.desc()).all()
        events = db.query(ApplicationEvent).filter_by(application_id=app.id).order_by(ApplicationEvent.created_at.desc(),ApplicationEvent.id.desc()).all()
        contacts = []
        company_id = db.query(JobOffer.company_id).filter_by(id=app.job_offer_id).scalar() if app.job_offer_id else None
        if company_id:
            contacts = db.query(CompanyContact).filter_by(company_id=company_id).all()
        result.update(raw_offer=app.raw_offer, analyses=[a.analysis_json for a in analyses], emails=[serialize_email(e, True) for e in emails],
            events=[{'id':e.id,'type':e.event_type,'previous_status':e.previous_status,'status':e.new_status,'source':e.source,'detail':e.detail,'created_at':iso(e.created_at)} for e in events],
            contacts=[{'id':c.id,'name':c.contact_name,'role':c.role_raw,'email':c.email,'linkedin':c.linkedin_url} for c in contacts])
    return result


def gmail_status(db):
    enabled = str(setting('GMAIL_ENABLED', 'false')).lower() == 'true'
    token = Path(setting('GMAIL_TOKEN_FILE', 'secrets/gmail-token.json'))
    state = db.get(GmailSyncState, owner_id())
    configured = enabled and token.suffix == '.json' and token.is_file()
    return {'configured':configured, 'enabled':enabled,
        'connected':bool(configured and state and state.mailbox and state.last_synced_at and not state.last_error),
        'mailbox':state.mailbox if state else None, 'last_sync':iso(state.last_synced_at) if state else None,
        'error':state.last_error if state else None, 'has_more':bool(state and state.next_page_token),
        'unmatched_count':db.query(EmailEvent).filter_by(owner_id=owner_id(),application_id=None).count()}


@contextmanager
def _sync_lock(db):
    key = hashlib.sha256((str(db.get_bind().url) + owner_id()).encode()).hexdigest()[:24]
    with (Path(tempfile.gettempdir()) / f'jobapply-gmail-{key}.lock').open('a') as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise GmailUnavailable('Une synchronisation est déjà en cours.') from None
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def sync_gmail(db, gmail_service=None, max_pages=3):
    stats = {'imported':0, 'duplicates':0, 'linked':0, 'unmatched':0, 'has_more':False, 'error':None}
    if str(setting('GMAIL_ENABLED', 'false')).lower() != 'true':
        return {**stats, 'error':'Gmail n’est pas configuré. Activez GMAIL_ENABLED et autorisez la lecture du compte.'}
    gmail = gmail_service or GmailService()
    try:
        with _sync_lock(db):
            owner = owner_id()
            state = db.get(GmailSyncState, owner)
            if state is None:
                state = GmailSyncState(owner_id=owner)
                db.add(state)
                db.commit()
            mailbox = gmail.authenticate()
            if state.mailbox and state.mailbox != mailbox:
                raise GmailUnavailable('Le compte Gmail diffère du compte déjà synchronisé. Utilisez un autre espace candidat.')
            query = setting('GMAIL_SEARCH_QUERY', DEFAULT_QUERY)
            if state.query != query:
                state.next_page_token = None
            state.mailbox, state.query = mailbox, query
            for _ in range(max(1, min(max_pages, 10))):
                page = gmail.page(query, 100, state.next_page_token)
                page_stats = {'imported':0,'duplicates':0,'linked':0,'unmatched':0}
                for raw in page['messages']:
                    if db.query(EmailEvent.id).filter_by(owner_id=owner, mailbox=mailbox, gmail_message_id=raw['gmail_message_id']).first():
                        page_stats['duplicates'] += 1
                        continue
                    classification = classify_email(raw)
                    event = EmailEvent(owner_id=owner, mailbox=mailbox, gmail_message_id=raw['gmail_message_id'],
                        thread_id=raw.get('thread_id'), sender_email=raw.get('sender_email','')[:320],
                        sender_name=raw.get('sender_name','')[:255], recipients=raw.get('recipients', []),
                        subject=raw.get('subject','')[:500], snippet=raw.get('snippet','')[:2000],
                        body_text=raw.get('body_text','')[:20000], received_at=raw.get('received_at'),
                        labels=raw.get('labels', []), detected_type=classification['type'], classification_reason=classification['reason'])
                    db.add(event)
                    db.flush()
                    app, method, confidence = match_application(db, event)
                    if app:
                        _apply_email(db, event, app, method, confidence)
                        page_stats['linked'] += 1
                    else:
                        page_stats['unmatched'] += 1
                    page_stats['imported'] += 1
                state.next_page_token = page.get('next_page_token')
                state.last_synced_at, state.last_error = datetime.utcnow(), None
                db.commit()
                for key in page_stats:
                    stats[key] += page_stats[key]
                stats['has_more'] = bool(state.next_page_token)
                if not state.next_page_token:
                    break
            return {**stats, 'last_sync':iso(state.last_synced_at)}
    except Exception as error:
        db.rollback()
        message = str(error) if isinstance(error, GmailUnavailable) else 'La synchronisation a échoué. Les pages déjà enregistrées sont conservées ; réessayez.'
        state = db.get(GmailSyncState, owner_id())
        if state:
            state.last_error = message
            db.commit()
        return {**stats, 'error':message}

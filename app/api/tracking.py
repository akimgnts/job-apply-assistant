"""Private candidate tracking API. Does not expose Gmail credentials or mutate Gmail."""
import hmac
import ipaddress
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session
from app.config import config
from app.database.db import get_db
from app.database.models import Application, EmailEvent, GmailSyncState, OutreachTracking
from app.services.email_tracking_service import EVENT_TYPES, owned_applications, suggestions, update_tracking
from app.services.email_ingestion_service import EmailIngestionService
from app.services.gmail_service import GmailUnavailable
from app.services.application_tracking_agent import ApplicationTrackingAgent


def private_access(request: Request):
    token = os.getenv('WEB_ACCESS_TOKEN', '')
    if token:
        if not hmac.compare_digest(request.headers.get('authorization','').encode(), ('Bearer '+token).encode()):
            raise HTTPException(401, 'Accès au suivi non autorisé. Configurez le jeton côté serveur web.')
    else:
        try:
            local = ipaddress.ip_address(request.client.host).is_loopback and request.url.hostname in ('localhost','127.0.0.1','::1')
        except (ValueError, AttributeError):
            local = False
        if not local or config.APP_ENV == 'production':
            raise HTTPException(403, 'Configurez WEB_ACCESS_TOKEN pour un accès distant au suivi.')
    origin = request.headers.get('origin')
    if origin and urlsplit(origin).netloc != request.url.netloc:
        raise HTTPException(403, 'Origine non autorisée.')


router = APIRouter(prefix='/api/tracking', dependencies=[Depends(private_access)])


def owner():
    return config.GMAIL_APPLICATION_USER_ID


def iso(value):
    return value.isoformat()+'Z' if value else None


def events(db):
    return db.query(EmailEvent).filter(EmailEvent.owner_id == owner())


def get_event(db, identifier):
    event = events(db).filter(EmailEvent.id == identifier).first()
    if not event:
        raise HTTPException(404, 'Message introuvable.')
    return event


def event_data(event, detail=False):
    result = {key:getattr(event,key) for key in ('id','thread_id','sender_email','sender_name','subject','snippet','detected_type','confirmed_type','status','application_id','link_method','classification_reason')}
    result['received_at'] = iso(event.received_at)
    if detail:
        result['body_text'] = event.body_text
        result['recipients'] = event.recipients or []
        from urllib.parse import quote
        result['gmail_url'] = f'https://mail.google.com/mail/u/?authuser={quote(event.mailbox)}#all/{quote(event.thread_id or event.gmail_message_id, safe="")}'
    return result


@router.get('/status')
def status(db: Session = Depends(get_db)):
    state = db.get(GmailSyncState, owner())
    return {'enabled':config.GMAIL_ENABLED, 'authorized':Path(config.GMAIL_TOKEN_FILE).is_file() and Path(config.GMAIL_TOKEN_FILE).suffix=='.json',
        'scheduler_enabled':config.GMAIL_SCHEDULER_ENABLED and config.GMAIL_ENABLED,
        'interval_minutes':config.GMAIL_INGESTION_INTERVAL_MINUTES, 'owner_id':owner(),
        'mailbox':state.mailbox if state else None, 'last_synced_at':iso(state.last_synced_at) if state else None,
        'last_error':state.last_error if state else None, 'has_more':bool(state and state.next_page_token),
        'query':config.GMAIL_SEARCH_QUERY, 'pending_count':events(db).filter(EmailEvent.status=='pending').count(),
        'event_count':events(db).count()}


@router.post('/sync')
def sync(db: Session = Depends(get_db)):
    try:
        return EmailIngestionService(db).ingest_emails()
    except GmailUnavailable as exc:
        raise HTTPException(503, str(exc)) from None


@router.get('/emails')
def list_emails(q: str = '', state: Literal['all','pending','processed','archived']='all', page: int=Query(1,ge=1), db: Session=Depends(get_db)):
    query = events(db)
    if state != 'all':
        query = query.filter(EmailEvent.status==state)
    if q.strip():
        term='%'+q.strip().replace('\\','\\\\').replace('%','\\%').replace('_','\\_')+'%'
        query=query.filter(or_(EmailEvent.subject.ilike(term,escape='\\'),EmailEvent.sender_email.ilike(term,escape='\\')))
    return {'items':[event_data(e) for e in query.order_by(EmailEvent.received_at.desc(),EmailEvent.id.desc()).offset((page-1)*25).limit(25)], 'total':query.count(),'page':page,'page_size':25}


@router.get('/opportunities')
def opportunities(
    q: str = '',
    view: Literal['all','needs_review','replies','interviews','rejections','job_boards','sent']='all',
    page: int = Query(1, ge=1),
    db: Session = Depends(get_db),
):
    rows = ApplicationTrackingAgent.build_opportunities(events(db).order_by(EmailEvent.received_at.desc(), EmailEvent.id.desc()).all())
    if q.strip():
        needle = q.strip().lower()
        rows = [row for row in rows if needle in f"{row['company']} {row['job_title']} {row['latest_subject'] or ''}".lower()]
    if view == 'needs_review':
        rows = [row for row in rows if row['needs_review_count']]
    elif view == 'replies':
        rows = [row for row in rows if row['status'] == 'reply']
    elif view == 'interviews':
        rows = [row for row in rows if row['status'] == 'interview']
    elif view == 'rejections':
        rows = [row for row in rows if row['status'] == 'rejected']
    elif view == 'job_boards':
        rows = [row for row in rows if row['status'] == 'job_board']
    elif view == 'sent':
        rows = [row for row in rows if row['status'] in ('sent', 'acknowledged')]
    total = len(rows)
    start = (page - 1) * 25
    items = []
    for row in rows[start:start+25]:
        item = dict(row)
        item['latest_received_at'] = iso(item['latest_received_at'])
        items.append(item)
    return {'items': items, 'total': total, 'page': page, 'page_size': 25}


@router.get('/emails/{identifier}')
def email(identifier: int, db: Session=Depends(get_db)):
    event=get_event(db,identifier)
    return {**event_data(event,True),'suggestions':suggestions(db,event)}


class ReviewInput(BaseModel):
    action: Literal['confirm','ignore']
    application_id: int | None = None
    event_type: str | None = None


@router.post('/emails/{identifier}/review')
def review(identifier: int, payload: ReviewInput, db: Session=Depends(get_db)):
    event=events(db).filter(EmailEvent.id==identifier).with_for_update().first()
    if event is None:
        raise HTTPException(404,'Message introuvable.')
    if event.status=='processed':
        if payload.action=='confirm' and event.application_id==payload.application_id and event.confirmed_type==payload.event_type:
            return event_data(event,True)
        raise HTTPException(409,'Ce message a déjà été validé. Sa liaison est conservée pour protéger l’historique.')
    if payload.action=='ignore':
        event.status='archived'
        event.application_id=None
        event.link_method=None
    else:
        if payload.event_type not in EVENT_TYPES or payload.event_type=='unknown':
            raise HTTPException(422,'Choisissez un type de message avant de valider.')
        app=owned_applications(db,owner()).filter(Application.id==payload.application_id).with_for_update().first()
        if not app:
            raise HTTPException(404,'Candidature introuvable dans cet espace.')
        event.application_id=app.id
        event.confirmed_type=payload.event_type
        event.status='processed'
        event.link_method='manual'
        update_tracking(db,event)
    db.commit()
    return event_data(event,True)


@router.get('/applications')
def applications(db: Session=Depends(get_db)):
    apps=owned_applications(db,owner()).order_by(Application.updated_at.desc()).all()
    rows=[]
    for app in apps:
        tracks=db.query(OutreachTracking).filter(OutreachTracking.application_id==app.id).order_by(OutreachTracking.id.desc()).all()
        linked=events(db).filter(EmailEvent.application_id==app.id).order_by(EmailEvent.received_at.desc()).all()
        track=tracks[0] if tracks else None
        rows.append({'id':app.id,'company':app.company,'job_title':app.job_title,
            'preparation_status':app.status.value,'tracking_status':track.status if track else 'not_contacted',
            'response_received':bool(track and track.response_received),'outreach_date':iso(track.outreach_date) if track else None,
            'response_date':iso(track.response_date) if track else None,
            'next_follow_up':iso(track.next_follow_up) if track else None,
            'multiple_contacts':len(tracks)>1,
            'email_count':len(linked),'pending_count':sum(e.status=='pending' for e in linked),
            'events':[event_data(e) for e in linked]})
    return rows


class FollowUpInput(BaseModel):
    next_follow_up: datetime | None


@router.patch('/applications/{identifier}/follow-up')
def follow_up(identifier: int, payload: FollowUpInput, db: Session=Depends(get_db)):
    app=owned_applications(db,owner()).filter(Application.id==identifier).with_for_update().first()
    if not app:
        raise HTTPException(404,'Candidature introuvable.')
    tracks=db.query(OutreachTracking).filter(OutreachTracking.application_id==identifier).all()
    if len(tracks)>1:
        raise HTTPException(409,'Plusieurs contacts existent pour ce dossier. Gérez les échéances par contact.')
    value=payload.next_follow_up
    if value:
        if value.tzinfo is None:
            raise HTTPException(422,'Une date avec fuseau horaire est requise.')
        value=value.astimezone(timezone.utc).replace(tzinfo=None)
    track=tracks[0] if tracks else OutreachTracking(application_id=identifier,status='pending')
    track.next_follow_up=value
    db.add(track)
    db.commit()
    return {'next_follow_up':iso(value)}

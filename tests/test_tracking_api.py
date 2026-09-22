"""End-to-end tracking API tests: real isolated DB, no credentials or external calls."""
from datetime import datetime
from unittest.mock import Mock
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.api.tracking import router
from app.config import config
from app.database.db import Base, get_db
from app.database.models import Application, EmailEvent, OutreachTracking, GmailSyncState, Opportunity, OpportunityLink
from app.services.email_ingestion_service import EmailIngestionService
from app.services.gmail_service import GmailUnavailable


@pytest.fixture
def workspace(monkeypatch):
    engine=create_engine('sqlite://',connect_args={'check_same_thread':False},poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session=sessionmaker(bind=engine)()
    monkeypatch.setattr(config,'GMAIL_APPLICATION_USER_ID','owner')
    monkeypatch.setattr(config,'GMAIL_ENABLED',False)
    monkeypatch.setenv('WEB_ACCESS_TOKEN','testing-token')
    app=FastAPI();app.include_router(router)
    app.dependency_overrides[get_db]=lambda:session
    client=TestClient(app,headers={'Authorization':'Bearer testing-token'})
    session.add_all([Application(id=1,telegram_user_id='owner',company='Acme',job_title='Data Analyst',raw_offer='SQL'),Application(id=2,telegram_user_id='other',company='Other',raw_offer='SQL')])
    session.commit()
    yield client,session
    session.close();engine.dispose()


def add_email(db,identifier=1,owner='owner',kind='interview_request',thread='thread1'):
    row=EmailEvent(id=identifier,owner_id=owner,mailbox='candidate@example.org',gmail_message_id=f'm{identifier}',thread_id=thread,sender_email='ada@acme.test',subject='Acme entretien',body_text='Nous vous proposons un entretien chez Acme',received_at=datetime(2026,9,16,10),status='pending',detected_type=kind)
    db.add(row);db.commit();return row


def test_ownership_and_private_access(workspace):
    client,db=workspace
    add_email(db,1,'owner');add_email(db,2,'other')
    assert client.get('/api/tracking/status',headers={'Authorization':'wrong'}).status_code==401
    assert client.get('/api/tracking/emails').json()['total']==1
    assert client.get('/api/tracking/emails/2').status_code==404
    assert len(client.get('/api/tracking/applications').json())==1
    assert client.post('/api/tracking/emails/1/review',json={'action':'confirm','application_id':2,'event_type':'interview_request'}).status_code==404
    assert client.post('/api/tracking/sync').status_code==503


def test_confirmation_updates_tracking_once_and_preserves_preparation(workspace):
    client,db=workspace;add_email(db)
    assert db.query(OutreachTracking).count()==0
    payload={'action':'confirm','application_id':1,'event_type':'interview_request'}
    assert client.post('/api/tracking/emails/1/review',json=payload).status_code==200
    track=db.query(OutreachTracking).one()
    assert track.status=='interview' and track.response_received==1
    assert db.get(Application,1).status.value=='analyzed'
    assert client.post('/api/tracking/emails/1/review',json=payload).status_code==200
    assert db.query(OutreachTracking).count()==1
    assert client.post('/api/tracking/emails/1/review',json={'action':'ignore'}).status_code==409


def test_acknowledgement_never_counts_as_reply(workspace):
    client,db=workspace;add_email(db,kind='acknowledgement')
    result=client.post('/api/tracking/emails/1/review',json={'action':'confirm','application_id':1,'event_type':'acknowledgement'})
    assert result.status_code==200
    assert db.query(OutreachTracking).count()==0


def test_ignore_does_not_delete_message_and_due_is_persisted(workspace):
    client,db=workspace;add_email(db)
    assert client.post('/api/tracking/emails/1/review',json={'action':'ignore'}).status_code==200
    assert db.get(EmailEvent,1).status=='archived'
    result=client.patch('/api/tracking/applications/1/follow-up',json={'next_follow_up':'2026-10-01T10:00:00+02:00'})
    assert result.json()['next_follow_up']=='2026-10-01T08:00:00Z'
    assert client.patch('/api/tracking/applications/2/follow-up',json={'next_follow_up':None}).status_code==404
    assert client.patch('/api/tracking/applications/1/follow-up',json={'next_follow_up':'2026-10-01T10:00:00'}).status_code==422


def test_thread_link_requires_confirmed_same_owner_and_account(workspace):
    from app.services.email_tracking_service import link_known_thread
    client,db=workspace;add_email(db)
    client.post('/api/tracking/emails/1/review',json={'action':'confirm','application_id':1,'event_type':'interview_request'})
    other=EmailEvent(owner_id='owner',mailbox='candidate@example.org',thread_id='thread1',gmail_message_id='m3')
    link_known_thread(db,other)
    assert other.application_id==1 and other.link_method=='thread'
    other.mailbox='another@example.org';other.application_id=None
    link_known_thread(db,other)
    assert other.application_id is None


def test_pagination_idempotence_resume_and_failure(workspace,monkeypatch):
    client,db=workspace;monkeypatch.setattr(config,'GMAIL_ENABLED',True)
    gmail=Mock();gmail.authenticate.return_value='candidate@example.org'
    item={'gmail_message_id':'one','thread_id':'t1','subject':'Acme candidature reçue','sender_email':'a@acme.test','body_text':'Nous avons bien reçu votre candidature','received_at':datetime(2026,9,16),'labels':[]}
    gmail.page.return_value={'messages':[item],'next_page_token':'next'}
    service=EmailIngestionService(db,gmail)
    result=service.ingest_emails(max_pages=1)
    assert result['imported']==1 and result['has_more']
    assert db.get(GmailSyncState,'owner').next_page_token=='next'
    gmail.page.return_value={'messages':[item],'next_page_token':None}
    result=service.ingest_emails(max_pages=1)
    assert result['duplicates']==1 and not result['has_more']
    assert gmail.page.call_args.args[2]=='next'
    gmail.page.side_effect=GmailUnavailable('Lecture impossible')
    with pytest.raises(GmailUnavailable):service.ingest_emails()
    assert db.get(GmailSyncState,'owner').last_error=='Lecture impossible'
    assert db.query(EmailEvent).count()==1


def test_migration_unique_head_and_roundtrip(workspace):
    import importlib.util
    from alembic.config import Config
    from alembic.script import ScriptDirectory
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from sqlalchemy import inspect
    client,db=workspace
    cfg=Config('alembic.ini');script=ScriptDirectory.from_config(cfg)
    assert script.get_heads()==['opportunities_20260919']
    path='migrations/versions/gmail_tracking_20260917.py'
    spec=importlib.util.spec_from_file_location('migration',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    with db.bind.begin() as conn:
        EmailEvent.__table__.drop(conn);GmailSyncState.__table__.drop(conn)
        with Operations.context(MigrationContext.configure(conn)):
            module.upgrade()
            assert 'email_events' in inspect(conn).get_table_names()
            module.downgrade()
            assert 'email_events' not in inspect(conn).get_table_names()


def test_older_sent_confirmation_does_not_schedule_after_bounce(workspace):
    client,db=workspace
    bounce=add_email(db,1,kind='bounce')
    client.post('/api/tracking/emails/1/review',json={'action':'confirm','application_id':1,'event_type':'bounce'})
    sent=add_email(db,2,kind='application_sent')
    sent.received_at=datetime(2026,9,15,10);db.commit()
    client.post('/api/tracking/emails/2/review',json={'action':'confirm','application_id':1,'event_type':'application_sent'})
    track=db.query(OutreachTracking).one()
    assert track.status=='bounced'
    assert track.next_follow_up is None


def test_opportunities_group_gmail_history_into_candidate_rows(workspace):
    client,db=workspace
    sent=add_email(db,1,kind='application_sent',thread='niji-thread')
    sent.subject='Application — Data Analyst | Niji'
    sent.labels=['SENT']
    sent.sender_email='akim@example.org'
    sent.body_text='Bonjour Niji'
    reply=add_email(db,2,kind='unknown',thread='niji-thread')
    reply.subject='Re: Application — Data Analyst | Niji'
    reply.sender_email='recruteur@niji.fr'
    reply.body_text='Votre candidature a bien été enregistrée ; notre HRBP va revenir vers vous.'
    alert=add_email(db,3,kind='newsletter',thread='linkedin-alert')
    alert.subject='Votre alerte emploi LinkedIn'
    alert.sender_email='jobalerts-noreply@linkedin.com'
    alert.body_text='De nouvelles offres correspondent à vos préférences.'
    db.commit()

    result=client.get('/api/tracking/opportunities')

    assert result.status_code==200
    data=result.json()
    assert data['total'] == 1
    rows={row['company']: row for row in data['items']}
    assert rows['Niji']['status'] == 'reply'
    assert rows['Niji']['email_count'] == 2
    assert rows['Niji']['needs_review_count'] == 2
    assert 'LinkedIn' not in rows
    assert db.query(Opportunity).count() == 0  # Reading must not create opportunities
    assert db.query(OpportunityLink).filter_by(source_type='email_event').count() == 0
    thread=client.get(f'/api/tracking/emails/{sent.id}/thread').json()
    assert len(thread['items']) == 2
    assert {item['direction'] for item in thread['items']} == {'sent', 'received'}

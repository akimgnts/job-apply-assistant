"""Behavior tests use an isolated database; no mailbox or production data is touched."""
import importlib.util
from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session


def test_workflow_service_is_available():
    assert importlib.util.find_spec('app.services.application_workflow_service') is not None


@pytest.fixture
def db(monkeypatch):
    monkeypatch.delenv('GMAIL_APPLICATION_USER_ID', raising=False)
    monkeypatch.setenv('WEB_USER_ID', 'local')
    from app.database.models import Base
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


def application(db, **extra):
    from app.database.models import Application
    values = dict(telegram_user_id='local', company='Acme', job_title='Data Analyst', raw_offer='Offer text')
    values.update(extra)
    row = Application(**values)
    db.add(row)
    db.commit()
    return row


def email(db, **extra):
    from app.database.models import EmailEvent
    values = dict(mailbox='candidate@example.org', gmail_message_id='m1', gmail_thread_id='t1',
                  sender_email='recruiter@acme.example', subject='Your application', body_text='',
                  classification='received', received_at=datetime.utcnow())
    values.update(extra)
    row = EmailEvent(**values)
    db.add(row)
    db.commit()
    return row


def test_applied_is_explicit_and_idempotent_with_followup(db):
    from app.database.models import ApplicationEvent, OutreachTracking
    from app.services.application_workflow_service import set_application_status, serialize_application
    app = application(db)
    assert serialize_application(db, app)['applied_at'] is None
    set_application_status(db, app.id, 'applied')
    stamp = app.applied_at
    set_application_status(db, app.id, 'applied')
    assert app.applied_at == stamp
    assert db.query(ApplicationEvent).count() == 1
    tracking = db.query(OutreachTracking).one()
    assert tracking.next_follow_up == stamp + timedelta(days=7)
    assert not tracking.response_received


def test_receipt_is_not_human_reply_and_cannot_regress_interview(db):
    from app.database.models import OutreachTracking
    from app.services.application_workflow_service import set_application_status, link_email
    app = application(db)
    set_application_status(db, app.id, 'applied')
    receipt = email(db)
    link_email(db, receipt.id, app.id)
    assert app.status.value == 'received'
    assert not db.query(OutreachTracking).one().response_received
    set_application_status(db, app.id, 'interview')
    later = email(db, gmail_message_id='m2')
    link_email(db, later.id, app.id)
    assert app.status.value == 'interview'


def test_rejection_clears_followup_and_stale_message_does_not_regress(db):
    from app.database.models import OutreachTracking
    from app.services.application_workflow_service import set_application_status, link_email
    app = application(db)
    set_application_status(db, app.id, 'applied')
    rejection = email(db, classification='rejected')
    link_email(db, rejection.id, app.id)
    tracking = db.query(OutreachTracking).one()
    assert app.status.value == 'rejected'
    assert tracking.response_received == 1
    assert tracking.next_follow_up is None
    stale = email(db, gmail_message_id='m2', classification='interview', received_at=datetime.utcnow()-timedelta(days=3))
    link_email(db, stale.id, app.id)
    assert app.status.value == 'rejected'


def test_link_cannot_silently_move_email_between_applications(db):
    from app.services.application_workflow_service import link_email
    app, other = application(db), application(db, company='Other')
    row = email(db)
    link_email(db, row.id, app.id)
    with pytest.raises(ValueError, match='déjà'):
        link_email(db, row.id, other.id)


def test_unique_company_and_title_matching_leaves_ambiguity_unmatched(db):
    from app.services.email_tracking_service import match_application
    app = application(db)
    row = email(db, subject='Acme – Data Analyst: candidature reçue')
    assert match_application(db, row)[0].id == app.id
    application(db)
    assert match_application(db, row)[0] is None
    row.subject = 'Acme hiring newsletter'
    assert match_application(db, row)[0] is None


def test_known_thread_matches_only_same_mailbox(db):
    from app.services.email_tracking_service import match_application
    app = application(db)
    email(db, application_id=app.id)
    row = email(db, gmail_message_id='m2', subject='A reply')
    assert match_application(db, row)[0].id == app.id
    row.mailbox = 'another@example.org'
    assert match_application(db, row)[0] is None


def test_own_sent_and_unknown_messages_do_not_change_application(db):
    from app.services.email_tracking_service import classify_email
    assert classify_email({'labels':['SENT'], 'subject':'Your interview'})['type'] == 'application_sent'
    assert classify_email({'subject':'Newsletter', 'automated':True})['type'] == 'newsletter'
    assert classify_email({'subject':'Hello'})['type'] == 'unknown'


def test_not_configured_returns_honest_state(db, monkeypatch):
    from app.services.application_workflow_service import gmail_status, sync_gmail
    monkeypatch.setenv('GMAIL_ENABLED', 'false')
    monkeypatch.setenv('GMAIL_TOKEN_FILE', '/nonexistent/gmail-token.json')
    assert gmail_status(db)['connected'] is False
    result = sync_gmail(db)
    assert result['imported'] == 0
    assert result['error']


def test_sync_is_idempotent_and_records_unmatched_messages(db, monkeypatch):
    from app.database.models import EmailEvent
    from app.services.application_workflow_service import sync_gmail
    monkeypatch.setenv('GMAIL_ENABLED', 'true')
    app = application(db)
    class Gmail:
        def authenticate(self): return 'candidate@example.org'
        def page(self, *args):
            return {'messages':[{'gmail_message_id':'gmail1','thread_id':'thread1',
                'subject':'Acme Data Analyst – candidature reçue', 'body_text':'Nous avons bien reçu votre candidature',
                'sender_email':'jobs@acme.example','received_at':datetime.utcnow(), 'labels':['INBOX']},
                {'gmail_message_id':'gmail2','thread_id':'thread2','subject':'Personal email','body_text':'Hello',
                'sender_email':'friend@example.org','received_at':datetime.utcnow(),'labels':['INBOX']}],
                'next_page_token':None}
    result = sync_gmail(db, Gmail())
    assert result['imported'] == 2
    assert result['linked'] == 1
    assert db.query(EmailEvent).filter_by(application_id=None).count() == 1
    assert sync_gmail(db, Gmail())['duplicates'] == 2
    assert db.query(EmailEvent).count() == 2


def test_sync_page_failure_is_visible_and_does_not_erase_saved_pages(db, monkeypatch):
    from app.database.models import EmailEvent
    from app.services.application_workflow_service import sync_gmail, gmail_status
    from app.services.gmail_service import GmailUnavailable
    monkeypatch.setenv('GMAIL_ENABLED', 'true')
    class Gmail:
        def authenticate(self): return 'candidate@example.org'
        def page(self, query, size, token):
            if token:
                raise GmailUnavailable('Lecture Gmail interrompue')
            return {'messages':[{'gmail_message_id':'saved','subject':'Hello','labels':[]}], 'next_page_token':'page2'}
    result = sync_gmail(db, Gmail())
    assert result['error'] == 'Lecture Gmail interrompue'
    assert result['imported'] == 1
    assert db.query(EmailEvent).count() == 1
    assert gmail_status(db)['error']


def test_owner_filter_applies_to_manual_mutations(db, monkeypatch):
    from app.services.application_workflow_service import set_application_status
    app = application(db, telegram_user_id='someone-else')
    monkeypatch.setenv('GMAIL_APPLICATION_USER_ID', 'candidate')
    with pytest.raises(LookupError):
        set_application_status(db, app.id, 'applied')

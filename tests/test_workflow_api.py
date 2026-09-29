"""Isolated route and additive schema tests for the application workspace."""
import importlib.util
from datetime import datetime

import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool


def test_workflow_routes_available():
    assert importlib.util.find_spec('app.api.workflow') is not None


@pytest_asyncio.fixture
async def workspace(monkeypatch):
    from app.api.workflow import router
    from app.database.db import Base, get_db
    from app.database.models import Application, EmailEvent
    monkeypatch.setenv('WEB_USER_ID', 'local')
    monkeypatch.setenv('GMAIL_APPLICATION_USER_ID', 'local')
    monkeypatch.setenv('GMAIL_ENABLED', 'false')
    engine = create_engine('sqlite://', connect_args={'check_same_thread':False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = Session(engine)
    session.add_all([Application(id=1, telegram_user_id='local', company='Acme', job_title='Data Analyst', raw_offer='SQL'),
        Application(id=2, telegram_user_id='another', company='Other', raw_offer='Private'),
        EmailEvent(id=1, owner_id='local', mailbox='candidate@example.org', gmail_message_id='mail1',
            subject='Application received', detected_type='acknowledgement', received_at=datetime.utcnow()),
        EmailEvent(id=2, owner_id='another', mailbox='other@example.org', gmail_message_id='mail2')])
    session.commit()
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: session
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        yield client, session
    session.close()
    engine.dispose()


@pytest.mark.asyncio
async def test_workflow_contract_and_ownership(workspace):
    client, db = workspace
    data = (await client.get('/api/workflow/applications')).json()
    assert len(data['items']) == 1
    assert data['gmail']['connected'] is False
    assert data['items'][0]['status_label'] == 'À préparer'
    details = (await client.get('/api/workflow/applications/1')).json()
    assert all(key in details for key in ('raw_offer','analyses','emails','events','contacts'))
    assert (await client.get('/api/workflow/applications/2')).status_code == 404
    assert (await client.post('/api/workflow/applications/2/status', json={'status':'applied'})).status_code == 404
    assert (await client.post('/api/workflow/applications/1/status', json={'status':'invalid'})).status_code == 422
    assert (await client.post('/api/workflow/applications/1/status', json={'status':'applied'})).json()['applied_at']


@pytest.mark.asyncio
async def test_link_and_sync_errors_visible(workspace):
    client, db = workspace
    assert (await client.get('/api/workflow/emails?unmatched=true')).json()['total'] == 1
    assert (await client.post('/api/workflow/emails/1/link', json={'application_id':2})).status_code == 404
    result = await client.post('/api/workflow/emails/1/link', json={'application_id':1})
    assert result.status_code == 200
    assert result.json()['application_id'] == 1
    assert (await client.get('/api/workflow/emails?unmatched=true')).json()['total'] == 0
    assert (await client.post('/api/workflow/gmail/sync')).json()['error']


def test_schema_upgrade_is_additive_and_repeatable():
    from app.database.workflow_schema import ensure_workflow_schema
    engine = create_engine('sqlite:///:memory:')
    with engine.begin() as conn:
        conn.execute(text('CREATE TABLE applications (id INTEGER PRIMARY KEY, company VARCHAR(255))'))
        conn.execute(text("INSERT INTO applications (id, company) VALUES (1, 'Keep me')"))
    ensure_workflow_schema(engine)
    ensure_workflow_schema(engine)
    columns = {c['name'] for c in inspect(engine).get_columns('applications')}
    assert {'job_offer_id','applied_at','status_updated_at'}.issubset(columns)
    assert {'email_events','application_events','gmail_sync_states'}.issubset(inspect(engine).get_table_names())
    with engine.connect() as conn:
        assert conn.execute(text('SELECT company FROM applications WHERE id=1')).scalar_one() == 'Keep me'
    engine.dispose()

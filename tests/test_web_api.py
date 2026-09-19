"""HTTP contracts for the single-user workspace, using an isolated SQLite database."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.database.db import Base, get_db
from app.database.models import Application, Company, JobOffer, GeneratedDocument, Opportunity
from app.web.api import router


@pytest.fixture
def workspace(monkeypatch):
    monkeypatch.setenv('WEB_USER_ID', 'local')
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    company = Company(name='Acme')
    session.add(company)
    session.flush()
    session.add(JobOffer(company_id=company.id, job_title='Data analyst', job_url='https://example.org/job', source='archive', raw_text='SQL et Python'))
    other = Application(telegram_user_id='other', raw_offer='Private', company='Hidden')
    session.add(other)
    session.flush()
    session.add(GeneratedDocument(application_id=other.id, telegram_user_id='other', document_type='cv', filename='secret.html', content='secret'))
    session.commit()
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: session
    with TestClient(app) as client:
        yield client, session
    session.close()
    engine.dispose()


def test_radar_save_is_idempotent_and_scoped(workspace):
    client, session = workspace
    assert client.get('/api/offers?q=missing').json()['total'] == 0
    offer = client.get('/api/offers?q=Acme').json()['items'][0]
    first = client.post(f"/api/offers/{offer['id']}/save")
    assert first.status_code == 200
    assert first.json()['status'] == 'saved'
    assert client.post(f"/api/offers/{offer['id']}/save").json()['id'] == first.json()['id']
    assert client.get('/api/applications').json()['total'] == 1
    assert client.get('/api/applications/1').status_code == 404
    assert client.get('/api/documents/1/download').status_code == 404
    assert client.get('/api/documents').json()['total'] == 0
    opportunities = client.get('/api/opportunities').json()
    assert opportunities['total'] == 1
    assert opportunities['items'][0]['offer_count'] == 1
    assert opportunities['items'][0]['application_count'] == 1


def test_manual_application_status_validation_and_missing_ai(workspace, monkeypatch):
    from app.config import config
    monkeypatch.setattr(config, 'OPENAI_API_KEY', '')
    client, session = workspace
    assert client.post('/api/applications', json={'raw_offer': '   '}).status_code == 422
    created = client.post('/api/applications', json={'raw_offer': 'SQL analyst', 'company': 'Acme', 'job_title': 'Analyst'}).json()
    app_id = created['id']
    opportunity = client.get('/api/opportunities?q=Acme').json()
    assert opportunity['total'] == 1
    assert opportunity['items'][0]['application_count'] == 1
    assert client.patch(f'/api/applications/{app_id}', json={'status': 'sent'}).status_code == 422
    assert client.patch(f'/api/applications/{app_id}', json={'status': 'archived'}).json()['status'] == 'archived'
    assert client.post(f'/api/applications/{app_id}/analyze').status_code == 503
    assert client.post(f'/api/applications/{app_id}/generate', json={'document_types': ['unknown']}).status_code == 422
    assert client.get('/api/offers?page=0').status_code == 422
    assert client.get('/api/settings').json()['ai_configured'] is False


def test_overview_profile_and_safe_document_download(workspace):
    client, session = workspace
    created = client.post('/api/applications', json={'raw_offer': 'SQL analyst'}).json()
    doc = GeneratedDocument(application_id=created['id'], telegram_user_id='local', document_type='mail', filename='../../unsafe\r\nname.txt', content='Bonjour', format='txt')
    session.add(doc)
    session.commit()
    response = client.get(f'/api/documents/{doc.id}/download')
    assert response.status_code == 200
    assert response.text == 'Bonjour'
    assert '\r' not in response.headers['content-disposition']
    assert '../' not in response.headers['content-disposition']
    assert client.get('/api/overview').json()['counts']['applications'] == 1
    assert 'master_cv' in client.get('/api/profile').json()
    assert client.get('/api/companies/1').json()['offers'][0]['job_title'] == 'Data analyst'


def test_analysis_and_generation_use_existing_agents_without_exposing_errors(workspace, monkeypatch):
    import sys
    from types import SimpleNamespace
    from unittest.mock import AsyncMock
    from app.config import config
    monkeypatch.setattr(config, 'OPENAI_API_KEY', 'test-key')
    analysis_agent = AsyncMock(return_value={'company': 'Acme', 'job_title': 'SQL Analyst', 'match_score': 8, 'missing_points': ['dbt'], 'strengths': ['SQL'], 'profile_blocks_to_use': [999]})
    position_agent = AsyncMock(return_value={'positioning': 'Data Analyst BI', 'skill_profile': 'general_business_data'})
    generation_agent = AsyncMock(return_value={'status': 'full_failure', 'documents': {'mail': None}, 'errors': {'mail': 'secret API key sensitive database address'}})
    monkeypatch.setitem(sys.modules, 'app.agents.analysis_agent', SimpleNamespace(AnalysisAgent=SimpleNamespace(analyze=analysis_agent)))
    monkeypatch.setitem(sys.modules, 'app.agents.positioning_agent', SimpleNamespace(PositioningAgent=SimpleNamespace(choose_angle=position_agent)))
    monkeypatch.setitem(sys.modules, 'app.agents.generation_agent', SimpleNamespace(GenerationAgent=SimpleNamespace(generate_documents=generation_agent)))
    client, session = workspace
    created = client.post('/api/applications', json={'raw_offer': 'SQL analyst'}).json()
    identifier = created['id']
    assert client.post(f'/api/applications/{identifier}/generate', json={'document_types': ['mail']}).status_code == 409
    analyzed = client.post(f'/api/applications/{identifier}/analyze')
    assert analyzed.status_code == 200
    assert analyzed.json()['status'] == 'analyzed'
    assert analyzed.json()['analysis']['profile_blocks_to_use'] == []
    intelligence = client.get('/api/intelligence').json()
    assert intelligence['frequent_gaps'] == [{'skill': 'dbt', 'frequency': 1, 'importance': None}]
    failed = client.post(f'/api/applications/{identifier}/generate', json={'document_types': ['mail']})
    assert failed.json()['application']['status'] == 'analyzed'
    assert 'secret' not in failed.text
    generation_agent.return_value = {'status': 'full_success', 'documents': {'mail': 'Bonjour'}, 'errors': {'mail': None}}
    succeeded = client.post(f'/api/applications/{identifier}/generate', json={'document_types': ['mail']})
    assert succeeded.json()['application']['status'] == 'generated'
    assert generation_agent.call_args.kwargs['telegram_user_id'] == 'local'


def test_failed_analysis_does_not_modify_application(workspace, monkeypatch):
    import sys
    from types import SimpleNamespace
    from unittest.mock import AsyncMock
    from app.config import config
    monkeypatch.setattr(config, 'OPENAI_API_KEY', 'test-key')
    monkeypatch.setitem(sys.modules, 'app.agents.analysis_agent', SimpleNamespace(AnalysisAgent=SimpleNamespace(analyze=AsyncMock(side_effect=RuntimeError('secret-token')))))
    monkeypatch.setitem(sys.modules, 'app.agents.positioning_agent', SimpleNamespace(PositioningAgent=SimpleNamespace()))
    client, session = workspace
    created = client.post('/api/applications', json={'raw_offer': 'SQL analyst'}).json()
    failed = client.post(f"/api/applications/{created['id']}/analyze")
    assert failed.status_code == 502
    assert 'secret-token' not in failed.text
    assert client.get(f"/api/applications/{created['id']}").json()['status'] == 'saved'


def test_manual_contacts_require_valid_sources_and_remain_pending(workspace):
    client, session = workspace
    payload = {'contact_name': 'Ada', 'role_raw': 'Recruiter', 'source_url': 'https://example.org/team'}
    assert client.post('/api/companies/1/contacts', json={**payload, 'source_url': 'javascript:alert(1)'}).status_code == 422
    assert client.post('/api/companies/1/contacts', json={**payload, 'source_url': 'https://'}).status_code == 422
    assert client.post('/api/companies/1/contacts', json={**payload, 'contact_name': '  '}).status_code == 422
    result = client.post('/api/companies/1/contacts', json=payload)
    assert result.status_code == 201
    assert result.json()['verification_status'] == 'pending'
    assert client.post('/api/companies/999/contacts', json=payload).status_code == 404


def test_outreach_validates_associations_and_delegates_generation(workspace, monkeypatch):
    import sys
    from types import SimpleNamespace
    from unittest.mock import AsyncMock
    from app.database.models import CompanyContact, OutreachDraft
    from app.config import config
    monkeypatch.setattr(config, 'OPENAI_API_KEY', 'test-key')
    client, session = workspace
    contact = CompanyContact(company_id=1, contact_name='Ada', role_raw='Recruiter', source_url='https://example.org/team', data_source='manual', verification_status='pending')
    session.add(contact)
    session.commit()
    payload = {'company_id': 1, 'contact_id': contact.id, 'job_offer_ids': [1], 'channel': 'email'}
    assert client.post('/api/outreach', json=payload).status_code == 409
    contact.verification_status = 'verified'
    company = Company(name='Other')
    session.add(company)
    session.flush()
    session.add(JobOffer(company_id=company.id, job_title='Other offer', job_url='https://other.org/jobs', source='archive'))
    session.commit()
    assert client.post('/api/outreach', json={**payload, 'job_offer_ids': [2]}).status_code == 422
    assert client.post('/api/outreach', json={**payload, 'company_id': company.id}).status_code == 422
    assert client.post('/api/outreach', json={**payload, 'channel': 'send-email'}).status_code == 422

    async def create_draft(db, company_id, contact_id, job_offer_ids, channel):
        draft = OutreachDraft(company_id=company_id, contact_id=contact_id, job_offer_id=job_offer_ids[0], channel=channel, subject_line='Hello', message_text='Draft only', status='READY')
        db.add(draft)
        db.commit()
        return draft
    generator = AsyncMock(side_effect=create_draft)
    monkeypatch.setitem(sys.modules, 'app.services.outreach_draft_service', SimpleNamespace(OutreachDraftService=SimpleNamespace(create_draft=generator)))
    result = client.post('/api/outreach', json=payload)
    assert result.status_code == 201
    assert result.json()['contact_name'] == 'Ada'
    assert client.get('/api/outreach?q=Acme&status=READY').json()['total'] == 1
    assert client.get('/api/outreach?company_id=999').json()['total'] == 0
    generator.assert_awaited_once()


def test_contact_verification_is_explicit_and_company_scoped(workspace):
    client, session = workspace
    created = client.post('/api/companies/1/contacts', json={'contact_name': 'Ada', 'role_raw': 'Recruiter', 'source_url': 'https://example.org/team'}).json()
    contact_id = created['id']
    assert client.patch(f'/api/companies/999/contacts/{contact_id}', json={'verification_status': 'verified'}).status_code == 404
    assert client.patch(f'/api/companies/1/contacts/{contact_id}', json={'verification_status': 'trusted'}).status_code == 422
    assert client.patch(f'/api/companies/1/contacts/{contact_id}', json={'verification_status': 'verified'}).json()['verification_status'] == 'verified'

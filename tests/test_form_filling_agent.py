import asyncio
import json
import pytest
from app.services.form_filling_agent import FormFillingAgent
from app.config import config

MASTER = {'personal_info': {'name': 'Test Candidate', 'email': 'test@example.org', 'phone': '+33123456789'},
          'experience': ['Built dashboards with Power BI for the sales team.']}


def field(identifier, label, kind='text', **kwargs):
    return dict(id=identifier, label=label, name='', type=kind, **kwargs)


def test_known_identity_fills_but_existing_sensitive_and_unknown_answers_do_not(monkeypatch):
    monkeypatch.setattr(config, 'OPENAI_API_KEY', '')
    result = asyncio.run(FormFillingAgent.plan([
        field('first', 'Prénom'), field('last', 'Nom de famille'), field('mail', 'Email', 'email'),
        field('existing', 'Téléphone', filled=True), field('salary', 'Salaire souhaité'),
        field('visa', 'Require visa sponsorship?', 'select'), field('agree', 'I agree', 'checkbox'),
        field('q', 'Votre expérience ?', 'textarea')], MASTER))
    assert {a['id']: a['value'] for a in result['answers']} == {'first':'Test','last':'Candidate','mail':'test@example.org'}
    assert {p['id'] for p in result['pending']} == {'existing','salary','visa','agree','q'}
    assert result['submission'] == 'manual_review_required'


def test_ai_answer_requires_exact_profile_evidence_and_known_field(monkeypatch):
    monkeypatch.setattr(config, 'OPENAI_API_KEY', 'test-key')
    async def llm(*args, **kwargs):
        return json.dumps({'answers':[
            {'id':'q','value':'Je construis des tableaux de bord Power BI.', 'evidence':MASTER['experience'][0]},
            {'id':'q2','value':'Je suis expert en Kubernetes.', 'evidence':'Expert Kubernetes'},
            {'id':'invented','value':'Unexpected answer', 'evidence':MASTER['experience'][0]},
        ]})
    monkeypatch.setattr('app.services.openai_service.call_openai', llm)
    result = asyncio.run(FormFillingAgent.plan([field('q','Quels tableaux de bord avez-vous construits ?','textarea'),field('q2','Quelle pratique Kubernetes ?','textarea')], MASTER))
    assert [a['id'] for a in result['answers']] == ['q']
    assert result['pending'][0]['id'] == 'q2'


def test_model_failure_leaves_questions_for_review(monkeypatch):
    monkeypatch.setattr(config, 'OPENAI_API_KEY', 'test-key')
    async def fail(*args, **kwargs):
        raise RuntimeError('Provider unavailable')
    monkeypatch.setattr('app.services.openai_service.call_openai', fail)
    result = asyncio.run(FormFillingAgent.plan([field('q','Motivation','textarea')], MASTER))
    assert not result['answers']
    assert result['pending']


def test_form_plan_uses_application_ownership_and_rejects_duplicate_fields(monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from sqlalchemy.pool import StaticPool
    from app.database.db import Base, get_db
    from app.database.models import Application
    from app.api.extension import router
    monkeypatch.setenv('WEB_USER_ID', 'local')
    engine=create_engine('sqlite://',connect_args={'check_same_thread':False},poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        mine=Application(telegram_user_id='local',raw_offer='SQL')
        other=Application(telegram_user_id='other',raw_offer='private')
        db.add_all([mine,other]);db.commit()
        app=FastAPI();app.include_router(router);app.dependency_overrides[get_db]=lambda:db
        with TestClient(app) as client:
            assert client.post('/api/extension/plan',json={'application_id':other.id,'fields':[]}).status_code==404
            assert client.post('/api/extension/plan',json={'application_id':mine.id,'fields':[field('x','Email'),field('x','Nom')]}).status_code==422
            assert client.post('/api/extension/plan',json={'application_id':mine.id,'fields':[field('x','Email','email')]}).json()['answers'][0]['method']=='profile'
    engine.dispose()

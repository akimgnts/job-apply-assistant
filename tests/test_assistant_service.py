import asyncio
import json
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi import HTTPException
from app.database.db import Base
from app.database.models import Application, Company, CompanyContact, JobOffer
from app.services import assistant_service as service

@pytest.fixture
def db(monkeypatch):
    monkeypatch.setenv('WEB_USER_ID', 'local')
    engine=create_engine('sqlite://')
    Base.metadata.create_all(engine)
    session=sessionmaker(bind=engine)()
    c=Company(name='Numberly');session.add(c);session.flush()
    session.add(CompanyContact(company_id=c.id,contact_name='Contact publié',role_raw='Recruiter',source_url='https://example.com',data_source='website'))
    session.add(JobOffer(company_id=c.id,job_title='Data Analyst',job_url='https://example.com/jobs/1',source='website',raw_text='Python SQL'))
    session.add_all([Application(telegram_user_id='local',raw_offer='SQL',company='Numberly',job_title='Data Analyst'),Application(telegram_user_id='other',raw_offer='Private',company='Secret')]);session.commit()
    yield session
    session.close();engine.dispose()


def test_search_scopes_private_resources_and_escapes_wildcards(db):
    data=service.read_resource(db,{'resource':'applications','query':''})
    assert data['total']==1
    assert data['items'][0]['company']=='Numberly'
    assert service.read_resource(db,{'resource':'applications','query':'%'})['total']==0
    assert service.read_resource(db,{'resource':'contacts','query':'Numberly'})['total']==1


def test_missing_ai_still_returns_real_resources(db,monkeypatch):
    monkeypatch.setattr(service.config,'OPENAI_API_KEY',None)
    answer=asyncio.run(service.chat(db,'contacts Numberly',[]))
    assert answer['mode']=='local'
    assert any(source['kind']=='contact' for source in answer['sources'])
    assert 'Contact publié' in answer['reply']


def test_ai_reads_data_and_cannot_execute_mutations_while_answering(db,monkeypatch):
    calls=[]
    async def fake(prompt,json_mode=False):
        calls.append(prompt)
        if len(calls)==1:
            return json.dumps({'queries':[{'resource':'applications','query':'Numberly'}]})
        return json.dumps({'reply':'Une candidature trouvée.', 'actions':[{'type':'set_status','id':1,'status':'applied','label':'Marquer candidaté'}]})
    monkeypatch.setattr(service,'ask_model',fake)
    monkeypatch.setattr(service.config,'OPENAI_API_KEY','test')
    answer=asyncio.run(service.chat(db,'Marque Numberly candidaté',[]))
    assert len(calls)==2
    assert db.get(Application,1).status.value != 'applied'
    assert answer['actions'][0]['type']=='set_status'
    assert 'Numberly' in calls[1]


def test_action_scope_and_allowlist(db):
    with pytest.raises(HTTPException):
        asyncio.run(service.execute_action(db,{'type':'set_status','id':2,'status':'applied'}))
    with pytest.raises(HTTPException):
        asyncio.run(service.execute_action(db,{'type':'send_email','id':1}))


def test_ai_invented_actions_are_removed(db,monkeypatch):
    async def fake(prompt,json_mode=False):
        return json.dumps({'reply':'Résultat', 'actions':[{'type':'send_email','id':1},{'type':'set_status','id':999,'status':'applied'}]})
    monkeypatch.setattr(service,'ask_model',fake)
    monkeypatch.setattr(service.config,'OPENAI_API_KEY','test')
    answer=asyncio.run(service.chat(db,'bonjour',[]))
    assert answer['actions']==[]

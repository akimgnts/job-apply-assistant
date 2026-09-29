import asyncio
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database.db import Base
from app.database.models import Application, ApplicationStatusEnum, Company, CompanyContact, JobOffer, GeneratedDocument, DocumentTypeEnum, JobAnalysis
from app.services import preparation_service as service

@pytest.fixture
def db(monkeypatch):
    monkeypatch.setenv('WEB_USER_ID', 'local')
    engine = create_engine('sqlite://')
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()
    engine.dispose()


def test_import_reuses_existing_offer_application(db):
    company = Company(name='Example')
    db.add(company); db.flush()
    offer = JobOffer(company_id=company.id, job_title='Data Analyst', job_url='https://example.com/jobs/1', source='website', raw_text='SQL Python reporting')
    db.add(offer); db.commit()
    first = service.save_offer(db, offer.id)
    second = service.save_offer(db, offer.id)
    assert first.id == second.id
    assert first.job_offer_id == offer.id
    assert db.query(Application).count() == 1


def test_prepare_generates_only_missing_documents_and_preserves_applied(db, monkeypatch):
    row = Application(telegram_user_id='local', company='Example', raw_offer='Data analyst SQL', status=ApplicationStatusEnum.applied)
    db.add(row); db.flush()
    db.add(JobAnalysis(application_id=row.id, analysis_json={'match_score': 8}))
    db.add(GeneratedDocument(application_id=row.id, telegram_user_id='local', document_type=DocumentTypeEnum.cv, filename='cv.html', content='<html>CV</html>'))
    db.commit()
    calls=[]
    async def generate(identifier, payload, db):
        calls.append(payload.document_types)
        for kind in payload.document_types:
            db.add(GeneratedDocument(application_id=identifier, telegram_user_id='local', document_type=DocumentTypeEnum(kind), filename=kind+'.html', content='Document'))
        db.commit()
        return {'status':'full_success', 'errors':{}}
    monkeypatch.setattr(service, 'generate_documents', generate)
    result=asyncio.run(service.prepare_application(db,row.id))
    assert calls == [['letter','mail']]
    assert row.status == ApplicationStatusEnum.applied
    assert result['status'] == 'full_success'
    asyncio.run(service.prepare_application(db,row.id))
    assert len(calls) == 1


def test_empty_document_is_not_ready(db,monkeypatch):
    row=Application(telegram_user_id='local',raw_offer='SQL', status=ApplicationStatusEnum.saved)
    db.add(row); db.flush()
    db.add(JobAnalysis(application_id=row.id,analysis_json={}))
    db.add(GeneratedDocument(application_id=row.id,telegram_user_id='local',document_type=DocumentTypeEnum.cv,filename='empty.html',content='   '))
    db.commit()
    async def fail(identifier,payload,db):
        return {'status':'full_failure','errors':{t:'indisponible' for t in payload.document_types}}
    monkeypatch.setattr(service,'generate_documents',fail)
    result=asyncio.run(service.prepare_application(db,row.id))
    assert result['missing'] == ['cv','letter','mail']
    assert row.status == ApplicationStatusEnum.saved


def test_import_other_users_url_does_not_share_application(db):
    c=Company(name='Example');db.add(c);db.flush()
    o=JobOffer(company_id=c.id,job_title='Data',job_url='https://example.com/role',source='website');db.add(o)
    db.add(Application(telegram_user_id='someone_else',raw_offer='private',source_url=o.job_url));db.commit()
    result=service.save_offer(db,o.id)
    assert result.telegram_user_id == 'local'
    assert db.query(Application).count() == 2


def test_daily_import_persists_sourced_contact_once(db):
    data = {'id': 246269, 'title': 'SDR', 'company': 'Bessand', 'business_france_url': 'https://mon-vie-via.businessfrance.fr/offres/246269',
        'broadcast_date': '2026-09-26T00:00:00', 'description': 'Prospection', 'profile': 'Sales',
        'contact': {'name': 'Monsieur Mathurin Dubois', 'email': 'mgavilan@bessand.com', 'source': 'business_france',
            'source_url': 'https://mon-vie-via.businessfrance.fr/offres/246269'}}
    first = service.import_daily_offer(db, data)
    second = service.import_daily_offer(db, data)
    assert first.id == second.id
    contacts = db.query(CompanyContact).all()
    assert len(contacts) == 1
    assert contacts[0].email == 'mgavilan@bessand.com'

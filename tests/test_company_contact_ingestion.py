from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.database.db import Base
from app.database.models import Company, CompanyContact
from app.models.job_source_adapter import NormalizedJobOffer
from app.services.company_contact_ingestion import persist_offer_contacts


def test_persists_and_deduplicates_offer_contacts():
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    try:
        company = Company(name='ACME')
        db.add(company)
        db.flush()
        offer = NormalizedJobOffer(
            job_title='Data Analyst',
            company_name='ACME',
            job_url='https://mon-vie-via.businessfrance.fr/offres/245336',
            source='business_france_vie',
            contacts=[{
                'contact_name': 'Marie Durand',
                'role_raw': 'Chargée de recrutement',
                'email': 'marie.durand@example.org',
                'source_url': 'https://mon-vie-via.businessfrance.fr/offres/245336',
                'data_source': 'business_france_vie',
                'verification_status': 'pending',
            }],
        )

        created = persist_offer_contacts(db, company, offer)
        again = persist_offer_contacts(db, company, offer)
        db.commit()

        assert created == 1
        assert again == 0
        row = db.query(CompanyContact).one()
        assert row.contact_name == 'Marie Durand'
        assert row.role_raw == 'Chargée de recrutement'
        assert row.email == 'marie.durand@example.org'
        assert row.verification_status == 'pending'
    finally:
        db.close()
        engine.dispose()

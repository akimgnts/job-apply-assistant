from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.db import Base
from app.database.models import Application, Company, EmailEvent, JobOffer, Opportunity, OpportunityEvent, OpportunityLink
from app.services.opportunity_service import OpportunityService


def session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    return db, engine


def test_job_offer_and_manual_application_share_one_opportunity_by_url():
    db, engine = session()
    company = Company(name="Acme")
    db.add(company)
    db.flush()
    offer = JobOffer(company_id=company.id, job_title="Data Analyst", job_url="https://acme.test/jobs/1", source="business_france", raw_text="SQL")
    app = Application(telegram_user_id="local", company="Acme", job_title="Data Analyst", source_url="https://acme.test/jobs/1", raw_offer="SQL")
    db.add_all([offer, app])
    db.commit()

    first = OpportunityService.ensure_for_job_offer(db, offer, "local")
    second = OpportunityService.ensure_for_application(db, app)
    db.commit()

    assert first.id == second.id
    assert db.query(Opportunity).count() == 1
    links = {(link.source_type, link.source_id) for link in db.query(OpportunityLink).all()}
    assert links == {("job_offer", offer.id), ("application", app.id)}
    assert db.query(OpportunityEvent).count() == 2
    engine.dispose()


def test_gmail_thread_reuses_sent_opportunity_for_reply():
    db, engine = session()
    sent = EmailEvent(
        owner_id="local",
        mailbox="akim@example.org",
        gmail_message_id="m1",
        thread_id="thread-niji",
        sender_email="akim@example.org",
        subject="Application — Data Analyst | Niji",
        body_text="Bonjour Niji",
        labels=["SENT"],
        detected_type="application_sent",
        status="pending",
        received_at=datetime(2026, 9, 18, 9),
    )
    reply = EmailEvent(
        owner_id="local",
        mailbox="akim@example.org",
        gmail_message_id="m2",
        thread_id="thread-niji",
        sender_email="recruteur@niji.fr",
        subject="Re: Application — Data Analyst | Niji",
        body_text="Votre profil nous intéresse.",
        labels=[],
        detected_type="recruiter_reply",
        status="pending",
        received_at=datetime(2026, 9, 18, 13),
    )
    db.add_all([sent, reply])
    db.commit()

    first = OpportunityService.ensure_for_email_event(db, sent)
    second = OpportunityService.ensure_for_email_event(db, reply)
    db.commit()

    assert first.id == second.id
    opportunity = db.query(Opportunity).one()
    assert opportunity.company == "Niji"
    assert opportunity.job_title == "Data Analyst"
    assert opportunity.status == "reply"
    assert db.query(OpportunityEvent).count() == 2
    engine.dispose()

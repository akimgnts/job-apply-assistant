"""Persist sourced contacts extracted from job-board offers."""
from __future__ import annotations
from sqlalchemy.orm import Session
from app.database.models import Company, CompanyContact
from app.models.job_source_adapter import NormalizedJobOffer


def persist_offer_contacts(db: Session, company: Company, offer: NormalizedJobOffer) -> int:
    """Save contacts attached to an offer, deduplicated inside the company."""
    created = 0
    for contact in offer.contacts or []:
        name = str(contact.get('contact_name') or '').strip()
        source_url = str(contact.get('source_url') or offer.job_url or '').strip()
        if not name or not source_url:
            continue
        email = (contact.get('email') or None)
        if email:
            email = str(email).strip().lower() or None
        query = db.query(CompanyContact).filter(CompanyContact.company_id == company.id)
        existing = query.filter(CompanyContact.email == email).first() if email else query.filter(CompanyContact.contact_name == name, CompanyContact.source_url == source_url).first()
        if existing:
            continue
        db.add(CompanyContact(
            company_id=company.id,
            contact_name=name,
            role_raw=str(contact.get('role_raw') or 'Contact recrutement').strip(),
            role_category=contact.get('role_category') or 'recruiter',
            email=email,
            linkedin_url=contact.get('linkedin_url'),
            source_url=source_url,
            data_source=contact.get('data_source') or offer.source,
            verification_status=contact.get('verification_status') or 'pending',
        ))
        created += 1
    return created

"""Database operations and serialization for the single-user web workspace."""
import os
from enum import Enum
from datetime import datetime
from fastapi import HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session
from app.database.models import Application, Company, JobOffer, GeneratedDocument, JobAnalysis


def user_id() -> str:
    return os.getenv('WEB_USER_ID', 'local')


def serialize(row, exclude: tuple = ()) -> dict:
    """Serialize model columns without internal ownership and disk paths."""
    result = {}
    for column in row.__table__.columns:
        key = column.key
        if key in ('telegram_user_id', 'file_path') or key in exclude:
            continue
        value = getattr(row, key)
        result[key] = value.isoformat() if isinstance(value, datetime) else value.value if isinstance(value, Enum) else value
    return result


def applications(db: Session):
    return db.query(Application).filter(Application.telegram_user_id == user_id())


def documents(db: Session):
    return db.query(GeneratedDocument).join(Application).filter(Application.telegram_user_id == user_id(), GeneratedDocument.telegram_user_id == user_id())


def get_application(db: Session, identifier: int) -> Application:
    row = applications(db).filter(Application.id == identifier).first()
    if row is None:
        raise HTTPException(404, 'Candidature introuvable.')
    return row


def get_document(db: Session, identifier: int) -> GeneratedDocument:
    row = documents(db).filter(GeneratedDocument.id == identifier).first()
    if row is None:
        raise HTTPException(404, 'Document introuvable.')
    return row


def get_offer(db: Session, identifier: int) -> JobOffer:
    row = db.get(JobOffer, identifier)
    if row is None:
        raise HTTPException(404, 'Offre introuvable.')
    return row


def search(query, term: str | None, *columns):
    if term and term.strip():
        escaped = term.strip().replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
        query = query.filter(or_(*(column.ilike(f'%{escaped}%', escape='\\') for column in columns)))
    return query


def paginate(query, page: int, page_size: int, mapper) -> dict:
    return {'items': [mapper(row) for row in query.offset((page - 1) * page_size).limit(page_size).all()], 'total': query.count(), 'page': page, 'page_size': page_size}


def offer_data(db: Session, offer: JobOffer) -> dict:
    saved = applications(db).filter(Application.source_url == offer.job_url).first()
    return {**serialize(offer), 'company': offer.company.name, 'saved_application_id': saved.id if saved else None}


def document_data(doc: GeneratedDocument, content: bool = False) -> dict:
    return {**serialize(doc, () if content else ('content',)), 'company': doc.application.company, 'job_title': doc.application.job_title}


def application_data(db: Session, row: Application, detail: bool = False) -> dict:
    data = serialize(row)
    if detail:
        latest = db.query(JobAnalysis).filter(JobAnalysis.application_id == row.id).order_by(JobAnalysis.id.desc()).first()
        data['analysis'] = latest.analysis_json if latest else None
        data['documents'] = [document_data(doc) for doc in documents(db).filter(GeneratedDocument.application_id == row.id).order_by(GeneratedDocument.id.desc()).all()]
    return data


def commit(db: Session) -> None:
    """Rollback failed writes without exposing database credentials in errors."""
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(503, 'Enregistrement impossible. Réessayez après vérification de la base de données.') from None

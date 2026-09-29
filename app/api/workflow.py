"""Application workflow API: preparation state, Gmail evidence and follow-up status."""
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.database.models import EmailEvent
from app.services import application_workflow_service as workflow


router = APIRouter(prefix="/api/workflow")


class StatusInput(BaseModel):
    status: Literal[
        "saved",
        "analyzed",
        "generated",
        "applied",
        "received",
        "replied",
        "interview",
        "rejected",
        "archived",
    ]


class LinkEmailInput(BaseModel):
    application_id: int = Field(gt=0)


@router.get("/applications")
def applications(db: Session = Depends(get_db)):
    rows = workflow.applications(db).order_by(workflow.Application.updated_at.desc(), workflow.Application.id.desc()).all()
    return {
        "items": [workflow.serialize_application(db, row) for row in rows],
        "gmail": workflow.gmail_status(db),
    }


@router.get("/applications/{identifier}")
def application(identifier: int, db: Session = Depends(get_db)):
    try:
        return workflow.serialize_application(db, workflow.get_application(db, identifier), detail=True)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from None


@router.post("/applications/{identifier}/status")
def set_status(identifier: int, payload: StatusInput, db: Session = Depends(get_db)):
    try:
        return workflow.serialize_application(db, workflow.set_application_status(db, identifier, payload.status), detail=True)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from None
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None


@router.get("/emails")
def emails(
    unmatched: bool = Query(False),
    page: int = Query(1, ge=1),
    db: Session = Depends(get_db),
):
    query = db.query(EmailEvent).filter(EmailEvent.owner_id == workflow.owner_id())
    if unmatched:
        query = query.filter(EmailEvent.application_id.is_(None))
    query = query.order_by(EmailEvent.received_at.desc(), EmailEvent.id.desc())
    total = query.count()
    rows = query.offset((page - 1) * 25).limit(25).all()
    return {
        "items": [workflow.serialize_email(row) for row in rows],
        "total": total,
        "page": page,
        "page_size": 25,
    }


@router.post("/emails/{identifier}/link")
def link_email(identifier: int, payload: LinkEmailInput, db: Session = Depends(get_db)):
    try:
        return workflow.serialize_email(workflow.link_email(db, identifier, payload.application_id), detail=True)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from None
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from None


@router.get("/gmail/status")
def gmail_status(db: Session = Depends(get_db)):
    return workflow.gmail_status(db)


@router.post("/gmail/sync")
def sync_gmail(db: Session = Depends(get_db)):
    return workflow.sync_gmail(db)

"""Extension plans use the same session and application ownership as the web UI."""
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.database.db import get_db
from app.database.models import JobAnalysis
from app.services.master_cv_service import load_master_cv
from app.services.form_filling_agent import FormFillingAgent
from app.web import service as workspace

router = APIRouter(prefix='/api/extension')


class FormField(BaseModel):
    id: str = Field(min_length=1, max_length=100)
    label: str = Field(default='', max_length=500)
    name: str = Field(default='', max_length=200)
    type: Literal['text', 'email', 'tel', 'url', 'number', 'date', 'textarea', 'select', 'file', 'checkbox', 'radio', 'password', 'hidden', 'custom']
    autocomplete: str = Field(default='', max_length=100)
    required: bool = False
    filled: bool = False
    options: list[str] = Field(default_factory=list, max_length=100)


class PlanInput(BaseModel):
    application_id: int = Field(gt=0)
    fields: list[FormField] = Field(max_length=80)


@router.post('/plan')
async def plan(payload: PlanInput, db: Session = Depends(get_db)):
    workspace.get_application(db, payload.application_id)
    if len({field.id for field in payload.fields}) != len(payload.fields):
        raise HTTPException(422, 'Les identifiants des champs doivent être uniques.')
    analysis = db.query(JobAnalysis).filter_by(application_id=payload.application_id).order_by(JobAnalysis.id.desc()).first()
    return await FormFillingAgent.plan([field.model_dump() for field in payload.fields], load_master_cv(), analysis.analysis_json if analysis else {})

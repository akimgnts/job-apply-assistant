"""Assistant endpoints; same workspace authentication and ownership as the UI."""
from typing import Literal
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.database.db import get_db
from app.services import assistant_service

router = APIRouter(prefix='/api/assistant')

class Message(BaseModel):
    role: Literal['user','assistant']
    content: str = Field(max_length=6000)

class ChatInput(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    history: list[Message] = Field(default_factory=list, max_length=12)

class ActionInput(BaseModel):
    type: Literal['open','prepare','save_offer','set_status','link_email','sync_gmail']
    id: int | None = Field(default=None,gt=0)
    resource: str | None = Field(default=None,max_length=30)
    status: str | None = Field(default=None,max_length=30)
    application_id: int | None = Field(default=None,gt=0)

@router.post('/message')
async def message(payload:ChatInput, db:Session=Depends(get_db)):
    return await assistant_service.chat(db,payload.message,[m.model_dump() for m in payload.history])

@router.post('/action')
async def action(payload:ActionInput, db:Session=Depends(get_db)):
    return await assistant_service.execute_action(db,payload.model_dump(exclude_none=True))

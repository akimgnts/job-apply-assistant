"""One-click preparation and source-verified imports for the web and assistant."""
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.database.db import get_db
from app.services import preparation_service as svc

router = APIRouter(prefix='/api/preparation')

class DailyImport(BaseModel):
    date: date
    offer_id: int = Field(gt=0)

@router.post('/offers/{identifier}')
def save_offer(identifier: int, db: Session = Depends(get_db)):
    from app.services.application_workflow_service import serialize_application
    return serialize_application(db, svc.save_offer(db, identifier), detail=True)

@router.post('/daily')
async def import_daily(payload: DailyImport, db: Session = Depends(get_db)):
    from app.api.daily import get_daily_service
    from app.services.application_workflow_service import serialize_application
    service = get_daily_service()
    result = await service.get_daily_offers(payload.date.isoformat(), verify_external=False)
    offer = next((row for row in result['offers'] if str(row['id']) == str(payload.offer_id)), None)
    if offer is None:
        raise HTTPException(404, 'Cette offre n’est pas présente dans les résultats de cette date.')
    return serialize_application(db, svc.import_daily_offer(db, offer), detail=True)

@router.post('/applications/{identifier}')
async def prepare(identifier: int, db: Session = Depends(get_db)):
    return await svc.prepare_application(db, identifier)

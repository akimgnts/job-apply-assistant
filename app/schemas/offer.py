from pydantic import BaseModel
from typing import Optional

class OfferInput(BaseModel):
    raw_text: str
    source_url: Optional[str] = None

class OfferExtracted(BaseModel):
    raw_offer: str
    source_url: Optional[str] = None
    is_url: bool

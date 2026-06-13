from pydantic import BaseModel
from typing import List

class DocumentRequest(BaseModel):
    application_id: int
    document_types: List[str]

class GeneratedDocumentResponse(BaseModel):
    document_type: str
    filename: str
    content: str

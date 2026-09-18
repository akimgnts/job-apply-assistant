"""Data schemas for ScrapeGraphAI lead discovery provider.

Defines the interface between ScrapeGraphAI extraction and LeadDiscoveryService verification.
"""

from typing import Optional
from pydantic import BaseModel, Field


class DiscoveredContact(BaseModel):
    """Raw contact discovered by ScrapeGraphAI.

    This is passed to LeadDiscoveryService for verification, normalization, and persistence.
    """

    contact_name: Optional[str] = Field(
        None,
        description="Contact full name from public source"
    )
    role_raw: Optional[str] = Field(
        None,
        description="Exact job title as found publicly"
    )
    company: str = Field(
        ...,
        description="Company name"
    )
    source_url: str = Field(
        ...,
        description="MANDATORY: Public URL where contact was found (verification provenance)"
    )
    linkedin_url: Optional[str] = Field(
        None,
        description="LinkedIn profile URL if publicly accessible"
    )
    email: Optional[str] = Field(
        None,
        description="Email if publicly listed (NOT guessed)"
    )
    evidence_text: Optional[str] = Field(
        None,
        description="Short quote from source supporting contact identity/role"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "contact_name": "Jane Doe",
                "role_raw": "Talent Acquisition Manager",
                "company": "Sidel",
                "source_url": "https://sidel.com/careers/page",
                "linkedin_url": None,
                "email": None,
                "evidence_text": "Jane Doe, Talent Acquisition Manager at Sidel, hiring for Data & AI roles"
            }
        }


class DiscoveryResult(BaseModel):
    """Result of discovery for a company."""

    company: str
    candidates: list[DiscoveredContact]
    search_queries_used: list[str] = Field(
        default_factory=list,
        description="Queries executed during discovery"
    )
    sources_checked: list[str] = Field(
        default_factory=list,
        description="Public sources checked"
    )
    errors: list[str] = Field(
        default_factory=list,
        description="Non-critical errors during discovery"
    )

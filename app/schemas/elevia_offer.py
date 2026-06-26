from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field, asdict


@dataclass
class EleviaOfferCatalogEntry:
    """Normalized Elevia offer catalog entry."""
    offer_id: str
    title: str
    company: str
    location: str
    description: Optional[str] = None
    contract_type: Optional[str] = None
    mission_duration: Optional[str] = None
    source_type: str = "elevia"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class EleviaOfferDetail:
    """Normalized Elevia offer detailed information."""
    offer_id: str
    title: str
    company: str
    location: str
    description: str
    full_text: str
    contract_type: Optional[str] = None
    mission_duration: Optional[str] = None
    required_skills: List[str] = field(default_factory=list)
    soft_skills: List[str] = field(default_factory=list)
    salary_range: Optional[Dict[str, Any]] = None
    ats_keywords: List[str] = field(default_factory=list)
    source_type: str = "elevia"
    raw_data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_job_offer_text(self) -> str:
        """Convert to job offer text format for analysis agents."""
        parts = [
            f"Title: {self.title}",
            f"Company: {self.company}",
            f"Location: {self.location}",
        ]
        if self.contract_type:
            parts.append(f"Contract Type: {self.contract_type}")
        if self.mission_duration:
            parts.append(f"Mission Duration: {self.mission_duration}")
        if self.required_skills:
            parts.append(f"Required Skills: {', '.join(self.required_skills)}")
        if self.soft_skills:
            parts.append(f"Soft Skills: {', '.join(self.soft_skills)}")
        parts.append("")
        parts.append("Description:")
        parts.append(self.description)
        parts.append("")
        parts.append("Full Offer:")
        parts.append(self.full_text)
        return "\n".join(parts)


@dataclass
class EleviaProfile:
    """Normalized Elevia profile information."""
    profile_id: str
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    skills: List[str] = field(default_factory=list)
    experience: List[Dict[str, Any]] = field(default_factory=list)
    education: List[Dict[str, Any]] = field(default_factory=list)
    certifications: List[str] = field(default_factory=list)
    raw_data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class EleviaMatchContext:
    """Matching context from Elevia (if available)."""
    match_score: Optional[float] = None
    matching_skills: List[str] = field(default_factory=list)
    missing_skills: List[str] = field(default_factory=list)
    strengths: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    raw_data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class EleviaIntegrationContext:
    """Complete context for Elevia integration."""
    source: str = "elevia"
    source_offer_id: str = ""
    source_type: str = "business_france"
    offer_catalog_entry: Optional[EleviaOfferCatalogEntry] = None
    offer_detail: Optional[EleviaOfferDetail] = None
    profile: Optional[EleviaProfile] = None
    matching_context: Optional[EleviaMatchContext] = None
    application_strategy_context: Dict[str, Any] = field(default_factory=dict)
    artifact_generation_context: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "source_offer_id": self.source_offer_id,
            "source_type": self.source_type,
            "offer_catalog_entry": self.offer_catalog_entry.to_dict() if self.offer_catalog_entry else None,
            "offer_detail": self.offer_detail.to_dict() if self.offer_detail else None,
            "profile": self.profile.to_dict() if self.profile else None,
            "matching_context": self.matching_context.to_dict() if self.matching_context else None,
            "application_strategy_context": self.application_strategy_context,
            "artifact_generation_context": self.artifact_generation_context,
        }

    def get_job_offer_text(self) -> str:
        """Get job offer text for analysis."""
        if self.offer_detail:
            return self.offer_detail.to_job_offer_text()
        elif self.offer_catalog_entry:
            return (
                f"Title: {self.offer_catalog_entry.title}\n"
                f"Company: {self.offer_catalog_entry.company}\n"
                f"Location: {self.offer_catalog_entry.location}\n"
                f"{self.offer_catalog_entry.description or ''}"
            )
        return ""

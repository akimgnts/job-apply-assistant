"""Phase 6: Build outreach context from company + contact + job data."""

from dataclasses import dataclass
from typing import Optional
from sqlalchemy.orm import Session
from app.database.models import Company, CompanyContact, JobOffer, JobAnalysis
from app.services.evidence_registry_service import load_evidence_registry
import logging

logger = logging.getLogger(__name__)


@dataclass
class VerifiedSkill:
    skill: str
    evidence_id: str
    evidence_snippet: str
    match_type: str  # DIRECT, SUPPORTING, GAP
    confidence: Optional[float] = None


@dataclass
class OutreachContext:
    """Immutable context for outreach generation (never invented)."""
    company_name: str
    contact_name: str
    contact_role: str
    contact_verification_status: str
    verified_skills: list[VerifiedSkill]
    gap_skills: list[str]  # Only names, never claimed as capabilities
    job_offers: list[dict]
    candidate_info: dict


class OutreachContextBuilder:
    @staticmethod
    def build(
        db: Session,
        company_id: int,
        contact_id: int,
        job_offer_ids: list[int]
    ) -> OutreachContext:
        """Build context from database.

        Fetches company, contact, job offers, and skill evidence mapping.
        All evidence_ids must exist in the registry.
        """
        # Fetch company
        company = db.query(Company).filter(Company.id == company_id).first()
        if not company:
            raise ValueError(f"Company not found: {company_id}")

        # Fetch contact
        contact = db.query(CompanyContact).filter(
            CompanyContact.id == contact_id,
            CompanyContact.company_id == company_id
        ).first()
        if not contact:
            raise ValueError(f"Contact not found: {contact_id}")

        # Fetch job offers
        offers = db.query(JobOffer).filter(
            JobOffer.id.in_(job_offer_ids),
            JobOffer.company_id == company_id
        ).all()

        # Load registry
        registry = load_evidence_registry()

        # Build skill map from all job analyses
        verified_skills = []
        gap_skills = set()

        for offer in offers:
            analysis = db.query(JobAnalysis).filter(
                JobAnalysis.job_offer_id == offer.id
            ).first()

            if not analysis or not analysis.analysis_json:
                continue

            # Get skill_evidence_map
            skill_map = analysis.analysis_json.get("skill_evidence_map", {})
            required_skills = analysis.analysis_json.get("required_skills", [])

            for skill in required_skills:
                if skill in skill_map:
                    evidence_info = skill_map[skill]
                    evidence_id = evidence_info.get("evidence_id")

                    if evidence_id:
                        # Verify evidence_id exists in registry
                        if evidence_id not in registry:
                            logger.warning(f"Evidence ID not in registry: {evidence_id}")
                            gap_skills.add(skill)
                            continue

                        # Build verified skill
                        evidence = registry[evidence_id]
                        verified_skills.append(VerifiedSkill(
                            skill=skill,
                            evidence_id=evidence_id,
                            evidence_snippet=evidence.get("text", "")[:150],
                            match_type=evidence_info.get("match", "SUPPORTING"),
                            confidence=evidence_info.get("confidence")
                        ))
                else:
                    gap_skills.add(skill)

        # Remove duplicates
        verified_skills = list({v.evidence_id: v for v in verified_skills}.values())
        gap_skills = sorted(list(gap_skills))

        # Get candidate info from config
        from app.config import config
        candidate_info = {
            "name": config.CANDIDATE_NAME or "Candidate",
            "email": config.CANDIDATE_EMAIL,
            "linkedin": config.CANDIDATE_LINKEDIN,
            "github": config.CANDIDATE_GITHUB,
        }

        return OutreachContext(
            company_name=company.name,
            contact_name=contact.contact_name,
            contact_role=contact.role_raw,
            contact_verification_status=contact.verification_status,
            verified_skills=verified_skills,
            gap_skills=gap_skills,
            job_offers=[{
                "title": o.job_title,
                "url": o.job_url,
                "required": o.required_skills or []
            } for o in offers],
            candidate_info=candidate_info
        )

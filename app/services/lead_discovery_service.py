"""Phase 5: Lead Discovery & Verification

Identify and verify real, relevant people to contact at high-priority companies.
Answers: "Who are the best real people to contact at this company?"

STRICT CONSTRAINTS:
- Never invent: name, title, employer, email, LinkedIn URL, source
- If unverifiable: leave null or don't create the lead
- Missing contact > fabricated contact
- All contacts must have source_url (verification provenance)

VERIFICATION STATUS:
- VERIFIED: name + role + company confirmed by current public source
- PARTIAL: identity/company verified, role/relevance uncertain
- STALE: source appears outdated, current employment unconfirmable

ROLE CATEGORIES (Conservative):
- TALENT_ACQUISITION: Recruiters, TA partners, hiring leads
- DATA_LEADERSHIP: Head of Data, VP Data, Data Director
- DATA_MANAGER: Data Manager, Data Lead, Analytics Manager
- AI_LEADERSHIP: Head of AI, AI Director
- AI_MANAGER: AI Manager, ML Lead
- ENGINEERING_MANAGER: Engineering Manager
- RECRUITER: Generic recruiter role
- null: Uncertain/adjacent roles

CONTACT RELEVANCE (Deterministic):
- HIGH: Recruiting role OR functional role matching company's skill gaps
- MEDIUM: Adjacent/related role or functional manager
- LOW: General company contact or uncertain relevance

EMAIL POLICY:
- Only store if genuinely/publicly available
- NO guessing: firstname.lastname@company.com
- NO pattern inference
- NO fabrication
- email = null is acceptable
"""
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database.models import Company, JobOffer, JobAnalysis, CompanyContact
import logging
from typing import Optional, Dict, List
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)

# Role normalization categories
class RoleCategory(str, Enum):
    """Conservative role categories for Data/AI hiring contexts."""
    TALENT_ACQUISITION = "TALENT_ACQUISITION"
    DATA_LEADERSHIP = "DATA_LEADERSHIP"
    DATA_MANAGER = "DATA_MANAGER"
    AI_LEADERSHIP = "AI_LEADERSHIP"
    AI_MANAGER = "AI_MANAGER"
    ENGINEERING_MANAGER = "ENGINEERING_MANAGER"
    RECRUITER = "RECRUITER"


# Verification status
class VerificationStatus(str, Enum):
    """Strict verification levels."""
    VERIFIED = "VERIFIED"  # Public source confirms name + role + company
    PARTIAL = "PARTIAL"    # Identity/company confirmed, role uncertain
    STALE = "STALE"        # Source outdated, current employment unclear


# Contact relevance
class ContactRelevance(str, Enum):
    """Deterministic relevance classification."""
    HIGH = "HIGH"          # Recruiter OR functional role matching skills
    MEDIUM = "MEDIUM"      # Adjacent/related role
    LOW = "LOW"            # General contact or uncertain


def normalize_role_category(role_raw: str) -> Optional[RoleCategory]:
    """Normalize a public role title to a category.

    Args:
        role_raw: Exact public job title

    Returns:
        RoleCategory enum or None if uncertain

    Strategy: Conservative matching. If uncertain, return None rather than guess.
    """
    if not role_raw:
        return None

    role_lower = role_raw.lower()

    # Talent Acquisition roles (explicit TA titles or data/ai recruiting)
    if "talent acquisition" in role_lower or "ta partner" in role_lower:
        return RoleCategory.TALENT_ACQUISITION

    if ("data" in role_lower or "ai" in role_lower or "ml" in role_lower) and \
       any(term in role_lower for term in ["recruiter", "talent", "hiring", "recruitment"]):
        return RoleCategory.TALENT_ACQUISITION

    # Generic recruiting roles
    if any(term in role_lower for term in ["recruiter", "talent manager", "ats", "hiring manager", "recruitment"]):
        return RoleCategory.RECRUITER

    # Data leadership
    if any(term in role_lower for term in ["head of data", "vp data", "data director", "chief data"]):
        return RoleCategory.DATA_LEADERSHIP

    # Data manager
    if any(term in role_lower for term in ["data manager", "data lead", "analytics manager", "data team lead"]):
        return RoleCategory.DATA_MANAGER

    # AI leadership
    if any(term in role_lower for term in ["head of ai", "ai director", "chief ai", "vp ai"]):
        return RoleCategory.AI_LEADERSHIP

    # AI manager
    if any(term in role_lower for term in ["ai manager", "ml lead", "ai engineer manager", "ai team lead"]):
        return RoleCategory.AI_MANAGER

    # Engineering manager
    if "engineering manager" in role_lower or "eng manager" in role_lower:
        return RoleCategory.ENGINEERING_MANAGER

    # Uncertain
    return None


def calculate_contact_relevance(
    role_category: Optional[RoleCategory],
    company_id: int,
    db: Session,
    company_skill_frequency: dict
) -> tuple[ContactRelevance, List[str]]:
    """Calculate contact relevance deterministically.

    Args:
        role_category: Normalized role category
        company_id: Target company ID
        db: Database session
        company_skill_frequency: Skill frequency dict from Phase 4

    Returns:
        (ContactRelevance, [reasons])

    Logic:
    - HIGH: Recruiting role OR functional data/ai role + company has matching skills
    - MEDIUM: Adjacent role or functional manager in related area
    - LOW: General contact or uncertain
    """
    reasons = []

    if not role_category:
        return (ContactRelevance.LOW, ["Role category unknown or uncertain"])

    # Recruiting roles = HIGH relevance
    if role_category in [RoleCategory.TALENT_ACQUISITION, RoleCategory.RECRUITER]:
        reasons.append("Direct recruiting/TA role")
        return (ContactRelevance.HIGH, reasons)

    # Functional data/ai roles with matching skills = HIGH
    if role_category in [RoleCategory.DATA_LEADERSHIP, RoleCategory.DATA_MANAGER]:
        if company_skill_frequency and ("SQL" in company_skill_frequency or "Python" in company_skill_frequency):
            reasons.append("Data leadership role with active data hiring")
            return (ContactRelevance.HIGH, reasons)
        reasons.append("Data functional role")
        return (ContactRelevance.MEDIUM, reasons)

    if role_category in [RoleCategory.AI_LEADERSHIP, RoleCategory.AI_MANAGER]:
        if company_skill_frequency and ("machine learning" in str(company_skill_frequency).lower() or "ai" in str(company_skill_frequency).lower()):
            reasons.append("AI leadership role with active AI hiring")
            return (ContactRelevance.HIGH, reasons)
        reasons.append("AI functional role")
        return (ContactRelevance.MEDIUM, reasons)

    # Engineering manager = MEDIUM (adjacent to data/ai teams)
    if role_category == RoleCategory.ENGINEERING_MANAGER:
        reasons.append("Engineering manager (adjacent to data/AI teams)")
        return (ContactRelevance.MEDIUM, reasons)

    # Default LOW
    reasons.append("Role relevance to data/AI hiring unclear")
    return (ContactRelevance.LOW, reasons)


def deduplicate_contact(
    db: Session,
    company_id: int,
    contact_name: str,
    linkedin_url: Optional[str],
    email: Optional[str]
) -> bool:
    """Check if a contact already exists (deduplication).

    Args:
        db: Database session
        company_id: Target company
        contact_name: Contact full name
        linkedin_url: LinkedIn profile URL (if any)
        email: Email address (if any)

    Returns:
        True if contact exists, False if new

    Strategy (conservative):
    - Same company + linkedin_url → duplicate
    - Same company + email (if email exists) → duplicate
    - Otherwise allow (same name at different companies is OK)
    """
    if linkedin_url:
        existing = db.query(CompanyContact).filter(
            CompanyContact.company_id == company_id,
            CompanyContact.linkedin_url == linkedin_url
        ).first()
        if existing:
            logger.info(f"Duplicate detected: {company_id} + {linkedin_url}")
            return True

    if email:
        existing = db.query(CompanyContact).filter(
            CompanyContact.company_id == company_id,
            CompanyContact.email == email
        ).first()
        if existing:
            logger.info(f"Duplicate detected: {company_id} + {email}")
            return True

    return False


def persist_contact(
    db: Session,
    company_id: int,
    contact_name: str,
    role_raw: str,
    role_category: Optional[RoleCategory],
    linkedin_url: Optional[str],
    email: Optional[str],
    source_url: str,
    data_source: str,
    verification_status: VerificationStatus
) -> CompanyContact:
    """Persist a verified contact.

    Args:
        db: Database session
        company_id: Company FK
        contact_name: Full name
        role_raw: Exact public title
        role_category: Normalized category
        linkedin_url: LinkedIn profile (if available)
        email: Email (if genuinely available)
        source_url: MANDATORY: verification source
        data_source: Source type (e.g., "manual_verified", "linkedin", "company_website")
        verification_status: VERIFIED / PARTIAL / STALE

    Returns:
        Persisted CompanyContact

    Constraint: source_url is MANDATORY (verification provenance)
    """
    if not source_url:
        raise ValueError("source_url is mandatory for contact verification provenance")

    contact = CompanyContact(
        company_id=company_id,
        contact_name=contact_name,
        role_raw=role_raw,
        role_category=role_category.value if role_category else None,
        linkedin_url=linkedin_url,  # nullable
        email=email,                # nullable
        source_url=source_url,      # mandatory
        data_source=data_source,
        verification_status=verification_status.value
    )

    db.add(contact)
    db.commit()

    logger.info(
        f"✅ Persisted contact: {contact_name} at company {company_id} "
        f"(source: {source_url}, status: {verification_status.value})"
    )

    return contact


def get_company_skill_frequency(db: Session, company_id: int) -> dict:
    """Get skill frequency for a company from Phase 3/4 data.

    Args:
        db: Database session
        company_id: Company ID

    Returns:
        Dict of {skill: count}
    """
    # Get all active offers for this company
    offers = db.query(JobOffer).filter(
        JobOffer.company_id == company_id,
        JobOffer.status == "active"
    ).all()

    skill_frequency = {}
    for offer in offers:
        # Get analysis for this offer
        analysis = db.query(JobAnalysis).filter(
            JobAnalysis.job_offer_id == offer.id
        ).first()

        if analysis and analysis.analysis_json:
            required_skills = analysis.analysis_json.get("required_skills", [])
            for skill in required_skills:
                skill_frequency[skill] = skill_frequency.get(skill, 0) + 1

    return skill_frequency


def discover_and_verify_contacts(
    db: Session,
    company_id: int,
    candidate_contacts: List[Dict],
    max_contacts: int = 3
) -> List[CompanyContact]:
    """Discover and verify contacts for a company.

    Args:
        db: Database session
        company_id: Target company
        candidate_contacts: List of discovered contacts, each with:
            {
                "contact_name": str,
                "role_raw": str,
                "linkedin_url": Optional[str],
                "email": Optional[str],
                "source_url": str (MANDATORY),
                "data_source": str,
                "verification_status": str (VERIFIED/PARTIAL/STALE)
            }
        max_contacts: Max contacts to persist per company

    Returns:
        List of persisted CompanyContact objects
    """
    if not candidate_contacts:
        logger.info(f"No candidate contacts provided for company {company_id}")
        return []

    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise ValueError(f"Company {company_id} not found")

    skill_frequency = get_company_skill_frequency(db, company_id)

    persisted = []
    deduplicated_count = 0

    for candidate in candidate_contacts[:max_contacts]:
        # Validate mandatory fields
        if not candidate.get("source_url"):
            logger.warning(f"Skipping contact {candidate.get('contact_name')}: missing source_url")
            continue

        contact_name = candidate.get("contact_name", "")
        role_raw = candidate.get("role_raw", "")

        # Check deduplication
        if deduplicate_contact(
            db,
            company_id,
            contact_name,
            candidate.get("linkedin_url"),
            candidate.get("email")
        ):
            deduplicated_count += 1
            continue

        # Normalize role
        role_category = normalize_role_category(role_raw)

        # Calculate relevance
        relevance, reasons = calculate_contact_relevance(role_category, company_id, db, skill_frequency)

        # Persist
        try:
            status = VerificationStatus(candidate.get("verification_status", "VERIFIED"))
        except ValueError:
            status = VerificationStatus.PARTIAL

        contact = persist_contact(
            db,
            company_id=company_id,
            contact_name=contact_name,
            role_raw=role_raw,
            role_category=role_category,
            linkedin_url=candidate.get("linkedin_url"),
            email=candidate.get("email"),
            source_url=candidate.get("source_url"),
            data_source=candidate.get("data_source", "manual_verified"),
            verification_status=status
        )

        # Attach relevance to the contact (for output, not persistence in MVP)
        contact._relevance = relevance.value
        contact._relevance_reasons = reasons

        persisted.append(contact)

    if deduplicated_count > 0:
        logger.info(f"Deduplicated {deduplicated_count} duplicate contacts for company {company_id}")

    logger.info(
        f"✅ Discovery complete for company {company_id}: "
        f"{len(persisted)} contacts verified, {deduplicated_count} deduplicated"
    )

    return persisted


def format_contact_output(contact: CompanyContact) -> dict:
    """Format a contact for output (CLI, API, etc.).

    Args:
        contact: CompanyContact object

    Returns:
        Dict with all contact info + computed fields
    """
    return {
        "contact_name": contact.contact_name,
        "role_raw": contact.role_raw,
        "role_category": contact.role_category,
        "company_id": contact.company_id,
        "linkedin_url": contact.linkedin_url,
        "email": contact.email,
        "source_url": contact.source_url,
        "data_source": contact.data_source,
        "verification_status": contact.verification_status,
        "contact_relevance": getattr(contact, "_relevance", None),
        "relevance_reasons": getattr(contact, "_relevance_reasons", []),
        "created_at": contact.created_at.isoformat() if contact.created_at else None,
    }

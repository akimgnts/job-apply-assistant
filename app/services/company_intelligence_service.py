"""Phase 4: Company Intelligence Aggregation

Transform JobOffers + JobAnalyses into company-level intelligence for outreach prioritization.

Deterministic signals:
- Offer volume (total active, relevant Data/BI/AI/Automation)
- Recurring skills (aggregate from all offer analyses)
- Candidate fit (DIRECT/SUPPORTING/GAP scoring from skill_evidence_map)
- Recruitment intensity (LOW/MEDIUM/HIGH based on offer count and recency)
- Company priority score (0-100, normalized, explainable ranking formula)

No LLM, no external data, no lead discovery. Pure aggregation of existing Radar signals.

PRIORITY SCORE FORMULA (Normalized to 0–100):
Raw score components:
  fit_base = avg_fit × 40 (0–40 points, fit = 0.0–1.0)
  offer_volume = min(relevant_offers × 10, 30) (0–30 points)
  best_fit_bonus = (best_fit - 0.6) × 20 if best_fit >= 0.6 else 0 (0–8 points)
  intensity_bonus = {HIGH: 10, MEDIUM: 5, LOW: 0} (0–10 points)

Raw maximum = 40 + 30 + 8 + 10 = 88
Normalized score = (raw_score / 88) × 100 → [0, 100]

STRONG MATCH THRESHOLD:
Offer is marked as "strong_match" if offer_fit >= 0.75 (75% fit)
Deterministic: DIRECT evidence = 1.0, SUPPORTING = 0.6, GAP = 0.0

ROADMAP:
Phase 4: Company Intelligence (this phase) — identify target companies
Phase 5: Lead Discovery & Verification — find real hiring contacts at those companies
  * Search for people at target companies
  * Verify role / company / source_url
  * Store LinkedIn URL when publicly available
  * Store email only if genuinely / publicly available
  * NO invented data, NO fake contacts
Phase 6: Outreach & Personalization — generate evidence-grounded messages
  * Create personalized emails based on verified contacts
  * No outreach generation in Phase 5
"""
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database.models import Company, JobOffer, JobAnalysis
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Score thresholds (deterministic constants)
STRONG_MATCH_THRESHOLD = 0.75  # Offer is "strong match" if fit >= 0.75
RAW_PRIORITY_SCORE_MAX = 88  # Theoretical raw maximum before normalization

# Skill relevance categories
RELEVANT_SKILL_KEYWORDS = {
    "data": ["data", "analytics", "analysis", "analyst", "warehouse", "engineering", "etl"],
    "ai": ["ai", "machine learning", "ml", "nlp", "deep learning", "neural", "gpt"],
    "bi": ["bi", "business intelligence", "power bi", "tableau", "dashboard"],
    "automation": ["automation", "rpa", "workflow", "orchestration"],
}

# Role family detection
RELEVANT_ROLE_KEYWORDS = {
    "data_analyst": ["data analyst", "analytics", "data specialist"],
    "bi_analyst": ["bi analyst", "business intelligence", "dashboards"],
    "data_engineer": ["data engineer", "etl", "pipeline"],
    "ai_ml": ["machine learning", "ai", "data scientist"],
}


def is_relevant_offer(job_title: str, analysis_json: Optional[dict] = None) -> bool:
    """Determine if an offer is relevant to Data/BI/AI/Automation profile.

    Args:
        job_title: Job title from JobOffer
        analysis_json: (Optional) Analysis JSON from JobAnalysis for additional context

    Returns:
        True if offer matches target roles or skills
    """
    title_lower = job_title.lower()

    # Check role family keywords
    for category, keywords in RELEVANT_ROLE_KEYWORDS.items():
        for keyword in keywords:
            if keyword in title_lower:
                return True

    # Check skill keywords in title
    for category, keywords in RELEVANT_SKILL_KEYWORDS.items():
        for keyword in keywords:
            if keyword in title_lower:
                return True

    # If analysis exists, check required_skills
    if analysis_json and isinstance(analysis_json, dict):
        required_skills = analysis_json.get("required_skills", [])
        for skill in required_skills:
            skill_lower = skill.lower()
            for category, keywords in RELEVANT_SKILL_KEYWORDS.items():
                for keyword in keywords:
                    if keyword in skill_lower:
                        return True

    return False


def calculate_skill_fit(evidence_list: list) -> tuple[float, dict]:
    """Calculate fit score for a single skill based on evidence.

    Evidence scoring:
    - DIRECT evidence = 1.0 (full weight)
    - SUPPORTING evidence = 0.6 (partial weight)
    - Empty/GAP = 0.0 (no evidence)

    Args:
        evidence_list: List of evidence dicts from skill_evidence_map[skill]

    Returns:
        (fit_score, match_breakdown) where breakdown shows evidence type counts
    """
    if not evidence_list:
        return (0.0, {"DIRECT": 0, "SUPPORTING": 0, "GAP": 1})

    direct_count = sum(1 for e in evidence_list if e.get("match_type") == "DIRECT")
    supporting_count = sum(1 for e in evidence_list if e.get("match_type") == "SUPPORTING")

    # Score: average evidence weight
    total_weight = (direct_count * 1.0) + (supporting_count * 0.6)
    avg_weight = total_weight / len(evidence_list) if evidence_list else 0.0

    return (avg_weight, {
        "DIRECT": direct_count,
        "SUPPORTING": supporting_count,
        "GAP": 0 if evidence_list else 1
    })


def calculate_offer_fit(analysis_json: dict) -> tuple[float, dict]:
    """Calculate fit score for a single offer.

    Aggregates skill-level fit scores across all required_skills.
    Score = average skill fit across all required skills.

    Args:
        analysis_json: Analysis JSON from JobAnalysis

    Returns:
        (offer_fit_score, breakdown) with score 0.0–1.0 and evidence counts
    """
    skill_evidence_map = analysis_json.get("skill_evidence_map", {})
    required_skills = analysis_json.get("required_skills", [])

    if not required_skills:
        return (0.0, {"skills_evaluated": 0, "direct": 0, "supporting": 0, "gaps": 0})

    skill_scores = []
    total_direct = 0
    total_supporting = 0
    total_gaps = 0

    for skill in required_skills:
        evidence_list = skill_evidence_map.get(skill, [])
        skill_score, breakdown = calculate_skill_fit(evidence_list)
        skill_scores.append(skill_score)

        total_direct += breakdown["DIRECT"]
        total_supporting += breakdown["SUPPORTING"]
        total_gaps += breakdown["GAP"]

    avg_fit = sum(skill_scores) / len(skill_scores) if skill_scores else 0.0

    return (avg_fit, {
        "skills_evaluated": len(required_skills),
        "direct": total_direct,
        "supporting": total_supporting,
        "gaps": total_gaps,
    })


def calculate_priority_score(avg_fit: float, relevant_offers: int, best_fit: float, intensity: str) -> int:
    """Calculate normalized priority score (0-100).

    Raw score formula:
    - fit_base = avg_fit × 40 (0-40 points)
    - offer_volume = min(relevant_offers × 10, 30) (0-30 points)
    - best_fit_bonus = (best_fit - 0.6) × 20 if best_fit >= 0.6 else 0 (0-8 points)
    - intensity_bonus = {HIGH: 10, MEDIUM: 5, LOW: 0} (0-10 points)

    Raw maximum = 88
    Normalized score = (raw_score / 88) × 100 → [0, 100]

    Args:
        avg_fit: Average offer fit (0.0-1.0)
        relevant_offers: Count of relevant offers
        best_fit: Best offer fit score (0.0-1.0)
        intensity: "HIGH", "MEDIUM", or "LOW"

    Returns:
        Priority score, normalized to 0-100
    """
    score_components = {
        "fit_base": avg_fit * 40,  # 0-40 points
        "offer_volume": min(relevant_offers * 10, 30),  # 0-30 points
        "best_fit_bonus": max(0, (best_fit - 0.6) * 20) if best_fit >= 0.6 else 0,  # 0-8 points
        "intensity_bonus": {"HIGH": 10, "MEDIUM": 5, "LOW": 0}[intensity],  # 0-10 points
    }

    raw_score = sum(score_components.values())

    # Normalize to 0-100
    normalized_score = (raw_score / RAW_PRIORITY_SCORE_MAX) * 100

    return int(round(normalized_score))


def get_recruitment_intensity(
    total_offers: int,
    relevant_offers: int,
    days_window: int = 7
) -> str:
    """Determine recruitment intensity category.

    LOW: 1-2 offers total, <1 relevant
    MEDIUM: 3-5 offers total, 1-2 relevant
    HIGH: 6+ offers total, 3+ relevant

    Args:
        total_offers: Total active offers for company
        relevant_offers: Offers matching Data/BI/AI profile
        days_window: Window for "recent" (unused for MVP, but available)

    Returns:
        "LOW", "MEDIUM", or "HIGH"
    """
    if total_offers >= 6 and relevant_offers >= 3:
        return "HIGH"
    elif total_offers >= 3 and relevant_offers >= 1:
        return "MEDIUM"
    else:
        return "LOW"


def get_company_intelligence(db: Session, company_id: int) -> dict:
    """Calculate comprehensive intelligence for a single company.

    Args:
        db: SQLAlchemy session
        company_id: Company ID

    Returns:
        Dict with company intelligence:
        {
            "company_id": int,
            "company_name": str,
            "offers": {
                "total": int,
                "active": int,
                "relevant": int,
                "strong_match": int (fit >= 0.75, deterministic threshold)
            },
            "skills": {
                "skill_name": count,
                ...
            },
            "fit": {
                "average": float (0.0-1.0),
                "best": float (0.0-1.0),
                "strong_match_count": int
            },
            "recruitment_intensity": "LOW"|"MEDIUM"|"HIGH",
            "priority_score": int (0-100),
            "priority_reasons": [str, ...]
        }
    """
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        return None

    # Get all active job offers for this company
    offers = db.query(JobOffer).filter(
        JobOffer.company_id == company_id,
        JobOffer.status == "active"
    ).all()

    if not offers:
        return {
            "company_id": company_id,
            "company_name": company.name,
            "offers": {"total": 0, "active": 0, "relevant": 0, "strong_match": 0},
            "skills": {},
            "fit": {"average": 0.0, "best": 0.0, "strong_match_count": 0},
            "recruitment_intensity": "LOW",
            "priority_score": 0,
            "priority_reasons": ["No active offers"]
        }

    # Collect analyses by offer
    offer_analyses = {}
    for offer in offers:
        analysis = db.query(JobAnalysis).filter(
            JobAnalysis.job_offer_id == offer.id
        ).first()
        offer_analyses[offer.id] = (offer, analysis)

    # Calculate signals
    total_offers = len(offers)
    relevant_offers = []
    skill_frequency = {}
    fit_scores = []
    strong_matches = []

    for offer_id, (offer, analysis) in offer_analyses.items():
        is_relevant = is_relevant_offer(offer.job_title, analysis.analysis_json if analysis else None)

        if is_relevant:
            relevant_offers.append(offer)

        # Aggregate skills
        if analysis and analysis.analysis_json:
            required_skills = analysis.analysis_json.get("required_skills", [])
            for skill in required_skills:
                skill_frequency[skill] = skill_frequency.get(skill, 0) + 1

            # Calculate fit
            offer_fit, _ = calculate_offer_fit(analysis.analysis_json)
            fit_scores.append(offer_fit)

            if offer_fit >= STRONG_MATCH_THRESHOLD:
                strong_matches.append(offer)

    # Aggregate fit metrics
    avg_fit = sum(fit_scores) / len(fit_scores) if fit_scores else 0.0
    best_fit = max(fit_scores) if fit_scores else 0.0

    # Recruitment intensity
    intensity = get_recruitment_intensity(total_offers, len(relevant_offers))

    # Build priority score (0-100, normalized)
    priority_score = calculate_priority_score(avg_fit, len(relevant_offers), best_fit, intensity)

    # Build reasons
    reasons = []
    if len(relevant_offers) > 0:
        reasons.append(f"{len(relevant_offers)} relevant offer(s)")
    if avg_fit >= 0.7:
        reasons.append(f"Strong profile fit ({avg_fit:.0%})")
    elif avg_fit >= 0.5:
        reasons.append(f"Moderate profile fit ({avg_fit:.0%})")
    if len(strong_matches) > 0:
        reasons.append(f"{len(strong_matches)} offer(s) with strong verified evidence")
    if intensity == "HIGH":
        reasons.append("High recent hiring intensity")
    elif intensity == "MEDIUM":
        reasons.append("Moderate hiring activity")

    # Top skills string
    if skill_frequency:
        top_skills_str = " · ".join(
            f"{skill} {count}x"
            for skill, count in sorted(skill_frequency.items(), key=lambda x: -x[1])[:5]
        )
        if top_skills_str:
            reasons.append(f"Key skills: {top_skills_str}")

    return {
        "company_id": company_id,
        "company_name": company.name,
        "offers": {
            "total": total_offers,
            "active": total_offers,
            "relevant": len(relevant_offers),
            "strong_match": len(strong_matches),
        },
        "skills": skill_frequency,
        "fit": {
            "average": round(avg_fit, 2),
            "best": round(best_fit, 2),
            "strong_match_count": len(strong_matches),
        },
        "recruitment_intensity": intensity,
        "priority_score": int(priority_score),
        "priority_reasons": reasons,
    }


def rank_companies(db: Session, limit: int = 10) -> list[dict]:
    """Rank all companies by outreach priority.

    Args:
        db: SQLAlchemy session
        limit: Maximum companies to return

    Returns:
        Sorted list of company intelligence dicts, highest priority first
    """
    companies = db.query(Company).all()

    intelligences = []
    for company in companies:
        intel = get_company_intelligence(db, company.id)
        if intel:
            intelligences.append(intel)

    # Sort by priority_score (descending), then by company_name (ascending) for ties
    intelligences.sort(key=lambda x: (-x["priority_score"], x["company_name"]))

    return intelligences[:limit]


def get_ranked_companies_report(db: Session, limit: int = 10) -> str:
    """Generate a human-readable ranked companies report.

    Args:
        db: SQLAlchemy session
        limit: Maximum companies to show

    Returns:
        Formatted text report
    """
    ranked = rank_companies(db, limit)

    lines = [
        "=" * 70,
        "COMPANY OUTREACH PRIORITY RANKING",
        "=" * 70,
        ""
    ]

    for idx, intel in enumerate(ranked, 1):
        lines.append(f"{idx}. {intel['company_name']} — {intel['priority_score']}")
        lines.append(f"   Fit profil: {intel['fit']['average']:.0%}")
        lines.append(f"   Recrutement: {intel['recruitment_intensity']}")
        lines.append(f"   Offres pertinentes: {intel['offers']['relevant']}")

        if intel['skills']:
            top_skills = " · ".join(
                f"{skill} {count}x"
                for skill, count in sorted(intel['skills'].items(), key=lambda x: -x[1])[:4]
            )
            lines.append(f"   Compétences: {top_skills}")

        if intel['offers']['strong_match'] > 0:
            lines.append(f"   {intel['offers']['strong_match']} offre(s) très compatible(s)")

        lines.append("")

    lines.append("=" * 70)
    return "\n".join(lines)

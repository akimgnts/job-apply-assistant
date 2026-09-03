"""Phase 3 Job Analysis Enrichment — Deterministic Evidence Mapping.

Analyzes JobOffer.raw_text using existing AnalysisAgent.
Maps required_skills to Master CV V3.1 evidence (experiences/projects).
Builds skill_evidence_map deterministically (no LLM, no hallucination).

Evidence ID format: "exp_<id>" (experience) or "proj_<id>" (project)
Match types: DIRECT (skill name in text), SUPPORTING (related skill), GAP (not found)
"""
import logging
import asyncio
from sqlalchemy.orm import Session
from app.database.models import JobOffer, JobAnalysis
from app.services.master_cv_service import load_master_cv
from app.agents.analysis_agent import AnalysisAgent

logger = logging.getLogger(__name__)


def find_skill_evidence_in_master_cv(skill_name: str, master_cv: dict) -> list:
    """Find evidence of a skill in Master CV (experiences + projects).

    Args:
        skill_name: Skill to search for (e.g., "Python", "Power BI")
        master_cv: Loaded Master CV structure

    Returns:
        List of evidence dicts: [{"evidence_id": "exp_0", "match_type": "DIRECT", "evidence_text": "..."}]
        Empty list if no evidence found (GAP).

    Match types:
    - DIRECT: Exact skill name found in experience/project bullet
    - SUPPORTING: Related skill found (e.g., "SQL" when searching "PostgreSQL")
    - (GAP is implicit if list is empty)
    """
    evidence = []
    skill_lower = skill_name.lower()

    # Search experiences
    for exp in master_cv.get("experiences", []):
        exp_id = exp.get("id")
        bullets = exp.get("bullets", [])

        for bullet_text in bullets:
            bullet_lower = bullet_text.lower()

            # Direct match: skill name appears in bullet
            if skill_lower in bullet_lower:
                evidence.append({
                    "evidence_id": f"exp_{exp_id}",
                    "match_type": "DIRECT",
                    "evidence_text": bullet_text[:150],  # First 150 chars
                })
                break  # One evidence per experience

            # Supporting match: related skill (e.g., database-related terms)
            supporting_terms = {
                "sql": ["postgresql", "mysql", "database", "query"],
                "power bi": ["dashboard", "dax", "powerbi", "bi"],
                "python": ["pandas", "numpy", "data analysis", "django", "flask"],
                "excel": ["vlookup", "pivot", "macro", "spreadsheet"],
                "aws": ["cloud", "ec2", "s3"],
                "docker": ["container", "containerization"],
            }

            if skill_lower in supporting_terms:
                for term in supporting_terms[skill_lower]:
                    if term in bullet_lower:
                        evidence.append({
                            "evidence_id": f"exp_{exp_id}",
                            "match_type": "SUPPORTING",
                            "evidence_text": bullet_text[:150],
                        })
                        break
                if evidence:  # If supporting evidence found, stop searching
                    break

    # Search projects
    for proj in master_cv.get("projects", []):
        proj_id = proj.get("id")
        bullets = proj.get("bullets", [])

        for bullet_text in bullets:
            bullet_lower = bullet_text.lower()

            # Direct match
            if skill_lower in bullet_lower:
                evidence.append({
                    "evidence_id": f"proj_{proj_id}",
                    "match_type": "DIRECT",
                    "evidence_text": bullet_text[:150],
                })
                break  # One evidence per project

    return evidence


async def analyze_and_enrich_job_offer(
    db: Session,
    job_offer: JobOffer
) -> tuple[JobAnalysis, dict]:
    """Analyze JobOffer using AnalysisAgent and enrich with Master CV evidence.

    Args:
        db: SQLAlchemy session
        job_offer: JobOffer object with raw_text populated

    Returns:
        (job_analysis, enriched_analysis_dict)
        - job_analysis: Persisted JobAnalysis object linked to JobOffer
        - enriched_analysis_dict: Full analysis with skill_evidence_map

    Process:
    1. Call AnalysisAgent.analyze(db, job_offer.raw_text) with empty profile
    2. Extract required_skills from analysis
    3. For each skill, find evidence in Master CV
    4. Build skill_evidence_map
    5. Persist JobAnalysis with job_offer_id FK
    """
    try:
        logger.info(f"Starting Phase 3 enrichment for JobOffer {job_offer.id}: {job_offer.job_title}")

        # Load Master CV (cached)
        master_cv = load_master_cv()

        # Step 1: Call AnalysisAgent with empty profile (no candidate profile needed for Radar)
        logger.info(f"Calling AnalysisAgent for {job_offer.job_title} at {job_offer.company_id}")
        analysis = await AnalysisAgent.analyze(db, job_offer.raw_text)

        # Step 2: Extract required_skills from analysis
        required_skills = analysis.get("required_skills", [])
        logger.info(f"Found {len(required_skills)} required skills: {required_skills}")

        # Step 3: Build skill_evidence_map
        skill_evidence_map = {}
        for skill in required_skills:
            evidence_list = find_skill_evidence_in_master_cv(skill, master_cv)

            if evidence_list:
                skill_evidence_map[skill] = evidence_list
                logger.info(f"  ✓ {skill}: {len(evidence_list)} evidence(s)")
            else:
                # GAP: skill not found in Master CV
                skill_evidence_map[skill] = []
                logger.info(f"  ✗ {skill}: NOT FOUND in Master CV (GAP)")

        # Step 4: Enrich analysis with skill_evidence_map
        enriched_analysis = {
            **analysis,
            "skill_evidence_map": skill_evidence_map,
        }

        # Step 5: Create JobAnalysis object
        job_analysis = JobAnalysis(
            job_offer_id=job_offer.id,
            application_id=None,  # This is for JobOffer analysis, not Application
            analysis_json=enriched_analysis,
            missions=analysis.get("missions", []),
            required_skills=required_skills,
            soft_skills=analysis.get("soft_skills", []),
            ats_keywords=analysis.get("ats_keywords", []),
            missing_points=analysis.get("missing_points", []),
            strengths=analysis.get("strengths", []),
            skill_evidence_map=skill_evidence_map,
        )

        # Step 6: Persist to DB
        db.add(job_analysis)
        db.commit()
        logger.info(f"✅ Persisted JobAnalysis for JobOffer {job_offer.id}")

        return job_analysis, enriched_analysis

    except Exception as e:
        logger.error(f"Failed to enrich JobOffer {job_offer.id}: {e}")
        db.rollback()
        raise


async def analyze_job_offers_batch(
    db: Session,
    job_offers: list[JobOffer]
) -> tuple[list[JobAnalysis], list[dict]]:
    """Analyze multiple JobOffers; batch-safe (one failure ≠ batch failure).

    Args:
        db: SQLAlchemy session
        job_offers: List of JobOffer objects

    Returns:
        (analyses, errors)
        - analyses: List of persisted JobAnalysis objects
        - errors: List of dicts {"offer_id": id, "error": str}
    """
    analyses = []
    errors = []

    for offer in job_offers:
        try:
            analysis, enriched = await analyze_and_enrich_job_offer(db, offer)
            analyses.append(analysis)
        except Exception as e:
            errors.append({
                "offer_id": offer.id,
                "offer_title": offer.job_title,
                "error": str(e),
            })
            logger.warning(f"Failed to analyze JobOffer {offer.id}: {e}")

    logger.info(f"Batch enrichment complete: {len(analyses)} success, {len(errors)} errors")
    return analyses, errors

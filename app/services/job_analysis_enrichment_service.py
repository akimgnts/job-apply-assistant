"""Phase 3 Job Analysis Enrichment — Deterministic Evidence Mapping.

Analyzes JobOffer.raw_text using existing AnalysisAgent.
Maps required_skills to Master CV V3.1 evidence via canonical Evidence Registry.
Builds skill_evidence_map deterministically (no LLM, no hallucination).

Evidence ID format: Canonical IDs from Evidence Registry
- SIDEL.DATA_BI.001 (experience + section + sequence)
- PROJECT.JOBAPPLY.001 (project + sequence)
- SKILL.PYTHON (skill)

Match types: DIRECT (exact match), SUPPORTING (related skill), GAP (not found)
"""
import logging
import asyncio
from sqlalchemy.orm import Session
from app.database.models import JobOffer, JobAnalysis
from app.services.evidence_registry_service import (
    load_evidence_registry,
    validate_evidence_id,
    resolve_evidence,
    find_evidence_by_skill_name,
)
from app.agents.analysis_agent import AnalysisAgent

logger = logging.getLogger(__name__)


def find_skill_evidence_in_registry(skill_name: str) -> list:
    """Find canonical evidence IDs for a skill using Evidence Registry.

    Args:
        skill_name: Skill to search for (e.g., "Python", "Power BI")

    Returns:
        List of evidence dicts with canonical IDs:
        [{"evidence_id": "SKILL.PYTHON", "match_type": "DIRECT", "evidence_text": "..."}]
        Empty list if no evidence found (GAP).

    Guarantees:
    - All evidence_ids exist in registry and are stable (not positional)
    - Evidence text corresponds to Master CV reality
    - No hallucination: only returns verified registry entries
    """
    evidence = []
    registry = load_evidence_registry()
    registry_evidence = registry["evidence"]

    # Direct skill match: look for SKILL.* entry
    skill_slug = skill_name.upper().replace(" ", "_")
    skill_id = f"SKILL.{skill_slug}"

    if skill_id in registry_evidence:
        evidence.append({
            "evidence_id": skill_id,
            "match_type": "DIRECT",
            "evidence_text": f"Skill: {skill_name}",
        })
        return evidence  # Skill match takes precedence

    # Search for skill mentions in experiences + projects
    skill_lower = skill_name.lower()

    for canonical_id, entry in registry_evidence.items():
        # Skip skills (already checked above)
        if canonical_id.startswith("SKILL."):
            continue

        entry_text = entry.get("text", "").lower()

        # Direct match: skill name appears in evidence text
        if skill_lower in entry_text:
            resolved = resolve_evidence(canonical_id)
            if resolved:
                evidence.append({
                    "evidence_id": canonical_id,
                    "match_type": "DIRECT",
                    "evidence_text": entry.get("text", "")[:150],
                })
                # Don't break: collect all evidence for this skill

    # If no direct evidence, look for supporting/related skills
    if not evidence:
        supporting_terms = {
            "sql": ["postgresql", "mysql", "database", "query", "data modeling"],
            "power bi": ["dashboard", "dax", "powerbi", "bi"],
            "python": ["pandas", "numpy", "data analysis", "django", "flask"],
            "excel": ["vlookup", "pivot", "macro", "spreadsheet"],
            "aws": ["cloud", "ec2", "s3"],
            "docker": ["container", "containerization"],
        }

        if skill_lower in supporting_terms:
            for related_term in supporting_terms[skill_lower]:
                for canonical_id, entry in registry_evidence.items():
                    if canonical_id.startswith("SKILL."):
                        continue

                    entry_text = entry.get("text", "").lower()
                    if related_term in entry_text:
                        evidence.append({
                            "evidence_id": canonical_id,
                            "match_type": "SUPPORTING",
                            "evidence_text": entry.get("text", "")[:150],
                        })
                        break  # One supporting evidence per term

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
    3. For each skill, find canonical evidence in Evidence Registry
    4. Build skill_evidence_map with canonical IDs (stable, not positional)
    5. Persist JobAnalysis with job_offer_id FK

    Guarantees:
    - All evidence_ids are from Evidence Registry (canonical, stable)
    - No hallucination: only uses verified registry entries
    - Evidence persisted is traceable back to Master CV V3.1
    """
    try:
        logger.info(f"Starting Phase 3 enrichment for JobOffer {job_offer.id}: {job_offer.job_title}")

        # Step 1: Call AnalysisAgent with empty profile (no candidate profile needed for Radar)
        logger.info(f"Calling AnalysisAgent for {job_offer.job_title} at {job_offer.company_id}")
        analysis = await AnalysisAgent.analyze(db, job_offer.raw_text)

        # Step 2: Extract required_skills from analysis
        required_skills = analysis.get("required_skills", [])
        logger.info(f"Found {len(required_skills)} required skills: {required_skills}")

        # Step 3: Build skill_evidence_map using canonical Evidence Registry IDs
        skill_evidence_map = {}
        for skill in required_skills:
            evidence_list = find_skill_evidence_in_registry(skill)

            if evidence_list:
                skill_evidence_map[skill] = evidence_list
                logger.info(f"  ✓ {skill}: {len(evidence_list)} evidence(s) {[e['evidence_id'] for e in evidence_list]}")
            else:
                # GAP: skill not found in Master CV
                skill_evidence_map[skill] = []
                logger.info(f"  ✗ {skill}: NOT FOUND in Master CV (GAP)")

        # Verify all evidence_ids are valid
        for skill, evidence_list in skill_evidence_map.items():
            for evidence in evidence_list:
                evidence_id = evidence.get("evidence_id")
                if not validate_evidence_id(evidence_id):
                    logger.error(f"Invalid evidence_id: {evidence_id} (not in registry)")
                    raise ValueError(f"Evidence ID {evidence_id} not found in registry")

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
        logger.info(f"✅ Persisted JobAnalysis for JobOffer {job_offer.id} with canonical evidence IDs")

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

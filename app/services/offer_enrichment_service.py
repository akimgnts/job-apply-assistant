import logging
from typing import Dict, Any, Optional
from app.services.elevia_gateway import EleviaOfferContext

logger = logging.getLogger(__name__)


class OfferEnrichmentService:
    """Enrich offer analysis with Elevia context."""

    @staticmethod
    def enrich_analysis_with_elevia_context(
        analysis: Dict[str, Any],
        elevia_context: EleviaOfferContext,
    ) -> Dict[str, Any]:
        """Merge Elevia context into existing analysis.

        Preserves existing analysis structure while adding Elevia enrichments.
        """
        if not analysis or not elevia_context:
            return analysis

        enriched = analysis.copy()

        # Add Elevia source metadata
        enriched["source"] = "elevia"
        enriched["source_offer_id"] = elevia_context.source_offer_id
        enriched["source_type"] = elevia_context.source_type

        # Enrich job information
        enriched["job_title"] = elevia_context.get_job_title()
        enriched["company"] = elevia_context.get_company()
        enriched["location"] = elevia_context.get_location()

        # Enrich required skills
        elevia_skills = elevia_context.get_required_skills()
        if elevia_skills:
            existing_skills = enriched.get("required_skills", [])
            # Merge, preferring Elevia structured data
            enriched["required_skills"] = list(set(elevia_skills + existing_skills))

        # Enrich soft skills
        elevia_soft = elevia_context.get_soft_skills()
        if elevia_soft:
            existing_soft = enriched.get("soft_skills", [])
            enriched["soft_skills"] = list(set(elevia_soft + existing_soft))

        # Enrich ATS keywords
        elevia_ats = elevia_context.get_ats_keywords()
        if elevia_ats:
            existing_ats = enriched.get("ats_keywords", [])
            enriched["ats_keywords"] = list(set(elevia_ats + existing_ats))

        # Add matching context if available
        match_score = elevia_context.get_match_score()
        if match_score is not None:
            enriched["elevia_match_score"] = match_score

        matching_expl = elevia_context.get_matching_explanation()
        if matching_expl:
            enriched["elevia_matching_explanation"] = matching_expl

        # Add Elevia offer context for reference
        enriched["elevia_context"] = elevia_context.to_dict()

        logger.info(
            "[ENRICHMENT] Analysis enriched with Elevia context: "
            "%s @ %s, skills=%d, soft_skills=%d",
            elevia_context.get_job_title(),
            elevia_context.get_company(),
            len(enriched.get("required_skills", [])),
            len(enriched.get("soft_skills", [])),
        )

        return enriched

    @staticmethod
    def build_artifact_generation_context(
        analysis: Dict[str, Any],
        positioning: str,
        elevia_context: Optional[EleviaOfferContext] = None,
    ) -> Dict[str, Any]:
        """Build context for CV/letter generation with Elevia enrichment."""
        context = {
            "job_title": analysis.get("job_title", "Unknown"),
            "company": analysis.get("company", "Unknown"),
            "location": analysis.get("location", "Unknown"),
            "positioning": positioning,
            "required_skills": analysis.get("required_skills", []),
            "soft_skills": analysis.get("soft_skills", []),
            "missions": analysis.get("missions", []),
            "strengths": analysis.get("strengths", []),
            "missing_points": analysis.get("missing_points", []),
            "ats_keywords": analysis.get("ats_keywords", []),
        }

        # Add Elevia-specific enrichments
        if elevia_context:
            context["source"] = "elevia"
            context["source_offer_id"] = elevia_context.source_offer_id
            context["elevia_match_score"] = elevia_context.get_match_score()
            context["elevia_matching_explanation"] = elevia_context.get_matching_explanation()

        logger.info(
            "[ARTIFACT_CONTEXT] Built generation context: "
            "%s @ %s, positioning=%s",
            context.get("job_title"),
            context.get("company"),
            positioning,
        )

        return context

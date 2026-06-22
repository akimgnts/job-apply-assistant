import logging
from typing import Dict, Any, Optional
from app.schemas.elevia_offer import EleviaIntegrationContext

logger = logging.getLogger(__name__)


class OfferEnrichmentService:
    """Enrich job analysis with external context (e.g., from Elevia)."""

    @staticmethod
    def enrich_analysis_with_elevia_context(
        analysis: Dict[str, Any],
        elevia_context: Optional[EleviaIntegrationContext],
    ) -> Dict[str, Any]:
        """Merge Elevia context into job analysis for better decision-making."""
        if not elevia_context:
            return analysis

        # Preserve original analysis, add Elevia context
        enriched = analysis.copy()

        # Store Elevia offer details
        enriched["elevia_source"] = {
            "offer_id": elevia_context.source_offer_id,
            "source_type": elevia_context.source_type,
        }

        # Enhance with offer detail context
        if elevia_context.offer_detail:
            offer_detail = elevia_context.offer_detail
            enriched["elevia_offer_detail"] = {
                "required_skills": offer_detail.required_skills,
                "soft_skills": offer_detail.soft_skills,
                "ats_keywords": offer_detail.ats_keywords,
                "contract_type": offer_detail.contract_type,
                "mission_duration": offer_detail.mission_duration,
            }

        # Merge matching context if available
        if elevia_context.matching_context:
            match = elevia_context.matching_context
            enriched["elevia_matching"] = {
                "match_score": match.match_score,
                "matching_skills": match.matching_skills,
                "missing_skills": match.missing_skills,
                "strengths": match.strengths,
                "recommendations": match.recommendations,
            }
            # Update top-level fields with Elevia insights
            if match.match_score is not None:
                enriched["elevia_match_score"] = match.match_score

        # Store profile context
        if elevia_context.profile:
            enriched["elevia_profile"] = {
                "skills": elevia_context.profile.skills,
                "experience_count": len(elevia_context.profile.experience),
                "education_count": len(elevia_context.profile.education),
            }

        return enriched

    @staticmethod
    def get_offer_text_from_elevia_context(
        elevia_context: EleviaIntegrationContext,
    ) -> str:
        """Extract job offer text from Elevia context for analysis."""
        return elevia_context.get_job_offer_text()

    @staticmethod
    def build_artifact_generation_context(
        analysis: Dict[str, Any],
        elevia_context: Optional[EleviaIntegrationContext],
    ) -> Dict[str, Any]:
        """Build context for document generation with Elevia data."""
        context = {}

        # Base offer information
        context["job_title"] = analysis.get("job_title", "")
        context["company"] = analysis.get("company", "")
        context["positioning"] = analysis.get("recommended_angle", "")

        # Add Elevia-specific context
        if elevia_context and elevia_context.offer_detail:
            offer = elevia_context.offer_detail
            context["location"] = offer.location
            context["contract_type"] = offer.contract_type
            context["mission_duration"] = offer.mission_duration
            context["required_skills"] = offer.required_skills
            context["soft_skills"] = offer.soft_skills
            context["ats_keywords"] = offer.ats_keywords

        if elevia_context and elevia_context.profile:
            profile = elevia_context.profile
            context["candidate_profile"] = {
                "skills": profile.skills,
                "location": profile.location,
                "experience": profile.experience,
                "education": profile.education,
            }

        if elevia_context and elevia_context.matching_context:
            match = elevia_context.matching_context
            context["matching_insights"] = {
                "matching_skills": match.matching_skills,
                "missing_skills": match.missing_skills,
                "recommendations": match.recommendations,
            }

        return context

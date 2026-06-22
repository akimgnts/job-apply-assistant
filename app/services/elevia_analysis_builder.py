import logging
from typing import Dict, Any, Optional
from app.services.elevia_gateway import EleviaOfferContext

logger = logging.getLogger(__name__)


class EleviaAnalysisBuilder:
    """Build analysis dict from EleviaOfferContext for agent consumption."""

    @staticmethod
    def build_analysis_from_offer_context(
        elevia_context: EleviaOfferContext,
    ) -> Dict[str, Any]:
        """Transform EleviaOfferContext into analysis structure.

        Compatible with existing AnalysisAgent output.
        """
        logger.info(
            "[ANALYSIS_BUILDER] Building analysis from Elevia offer: %s @ %s",
            elevia_context.get_job_title(),
            elevia_context.get_company(),
        )

        description = elevia_context.get_description()
        required_skills = elevia_context.get_required_skills()
        soft_skills = elevia_context.get_soft_skills()
        ats_keywords = elevia_context.get_ats_keywords()

        # Build missions from description (simple heuristic)
        missions = EleviaAnalysisBuilder._extract_missions(description)

        # Build analysis structure
        analysis = {
            # Core offer info
            "job_title": elevia_context.get_job_title(),
            "company": elevia_context.get_company(),
            "location": elevia_context.get_location(),
            "source": "elevia",
            "source_offer_id": elevia_context.source_offer_id,
            "source_type": elevia_context.source_type,
            # Requirements
            "description": description,
            "missions": missions,
            "required_skills": required_skills,
            "soft_skills": soft_skills,
            "ats_keywords": ats_keywords,
            # Candidate profile match
            "job_requirements": {
                "required_skills": required_skills,
                "soft_skills": soft_skills,
                "seniority": EleviaAnalysisBuilder._infer_seniority(description),
                "contract_type": elevia_context.offer_detail.get("contract_type", "CDI"),
            },
            # Matching context (if profile available)
            "matching_signals": EleviaAnalysisBuilder._extract_matching_signals(
                elevia_context
            ),
            "match_score": elevia_context.get_match_score(),
            "matching_explanation": elevia_context.get_matching_explanation(),
            # Strengths and gaps (to be filled by positioning/enrichment)
            "strengths": [],
            "missing_points": [],
            "cv_strategy": None,
            "bridges": [],
        }

        logger.info(
            "[ANALYSIS_BUILDER] Analysis built: "
            "required_skills=%d, soft_skills=%d, missions=%d, match=%.1f",
            len(required_skills),
            len(soft_skills),
            len(missions),
            analysis.get("match_score") or 0,
        )

        return analysis

    @staticmethod
    def _extract_missions(description: str) -> list:
        """Extract missions from offer description."""
        if not description:
            return []

        missions = []
        lines = description.split("\n")

        for line in lines:
            line = line.strip()
            # Simple heuristic: bullet points or numbered items
            if line.startswith(("•", "-", "*", "•", ">")):
                mission = line.lstrip("•-*> ").strip()
                if mission and len(mission) > 10:
                    missions.append(mission)
            elif line and any(line.startswith(f"{i}.") for i in range(1, 20)):
                # Numbered items
                mission = line.split(".", 1)[1].strip()
                if mission and len(mission) > 10:
                    missions.append(mission)

        # Limit to 5 missions
        return missions[:5]

    @staticmethod
    def _infer_seniority(description: str) -> str:
        """Infer seniority level from description."""
        if not description:
            return "unknown"

        description_lower = description.lower()

        senior_keywords = [
            "senior",
            "expert",
            "lead",
            "principal",
            "architect",
            "manager",
            "5+ years",
            "10+ years",
        ]
        mid_keywords = [
            "mid-level",
            "experienced",
            "3+ years",
            "confirmed",
            "2-4 years",
        ]
        junior_keywords = [
            "junior",
            "graduate",
            "entry-level",
            "0-2 years",
            "internship",
        ]

        senior_count = sum(1 for kw in senior_keywords if kw in description_lower)
        mid_count = sum(1 for kw in mid_keywords if kw in description_lower)
        junior_count = sum(1 for kw in junior_keywords if kw in description_lower)

        if senior_count > mid_count and senior_count > junior_count:
            return "senior"
        elif mid_count > junior_count:
            return "mid"
        elif junior_count > 0:
            return "junior"
        else:
            return "unknown"

    @staticmethod
    def _extract_matching_signals(elevia_context: EleviaOfferContext) -> Dict[str, Any]:
        """Extract matching signals from Elevia context."""
        signals = {
            "match_score": elevia_context.get_match_score(),
            "matching_explanation": elevia_context.get_matching_explanation(),
        }

        profile = elevia_context.profile
        if profile:
            signals["profile_id"] = profile.get("profile_id")
            signals["profile_skills"] = profile.get("skills", [])
            signals["profile_experience"] = profile.get("experience", [])

        matching_context = elevia_context.matching_context
        if matching_context:
            signals["strengths"] = matching_context.get("strengths", [])
            signals["gaps"] = matching_context.get("gaps", [])
            signals["recommendations"] = matching_context.get("recommendations", [])

        return signals

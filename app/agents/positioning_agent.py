import logging
from app.services.openai_service import generate_text
from app.prompts.positioning_prompt import get_positioning_prompt

logger = logging.getLogger(__name__)

VALID_ANGLES = [
    "Data Analyst BI",
    "Marketing Data Analyst",
    "Data Steward / Data Quality",
    "Business Analyst orienté data",
    "Data & AI Consultant",
    "Product / Ops Analyst",
    "Business Intelligence Analyst",
]

class PositioningAgent:
    """Choose best positioning angle + skill profile for the candidate."""

    @staticmethod
    async def choose_angle(
        analysis: dict,
        matching_signals: dict = None,
    ) -> dict:
        """Choose positioning angle + skill profile (JSON mode).

        Args:
            analysis: Job analysis dict with company, job_title, skills, missions
            matching_signals: Optional Elevia matching signals with:
                - match_score (0-10)
                - strengths (list of strong alignment areas)
                - gaps (list of missing skills/experience)
                - explanation (text summary)

        Returns validated dict with:
        {
            "positioning": angle from VALID_ANGLES,
            "skill_profile": key from SKILL_PROFILES,
            "reasoning": explanation,
            "positioning_enriched_by_elevia": bool (if matching_signals used)
        }
        """
        from app.services.openai_service import generate_cv_payload
        from app.config.skill_profiles import validate_skill_profile

        # Use enriched prompt if matching signals available
        if matching_signals:
            from app.prompts.positioning_prompt import get_positioning_prompt_enriched_elevia
            prompt = get_positioning_prompt_enriched_elevia(analysis, matching_signals)
            enriched = True
            logger.info(
                "[POSITIONING] Using Elevia-enriched positioning (score=%.1f)",
                matching_signals.get("match_score", 0)
            )
        else:
            prompt = get_positioning_prompt(analysis)
            enriched = False
            logger.info("[POSITIONING] Using standard positioning")

        try:
            result = await generate_cv_payload(prompt)

            positioning = result.get("positioning", "").strip()
            skill_profile = result.get("skill_profile", "general_business_data").strip()
            reasoning = result.get("reasoning", "")

            # Validate positioning angle
            if positioning not in VALID_ANGLES:
                logger.warning(f"Invalid positioning: {positioning}, using default")
                positioning = VALID_ANGLES[0]

            # Validate skill profile
            if not validate_skill_profile(skill_profile):
                logger.warning(f"Invalid skill_profile: {skill_profile}, using general_business_data")
                skill_profile = "general_business_data"

            logger.info(
                f"Selected positioning={positioning}, "
                f"skill_profile={skill_profile}, "
                f"enriched_by_elevia={enriched}"
            )
            logger.debug(f"Reasoning: {reasoning}")

            return {
                "positioning": positioning,
                "skill_profile": skill_profile,
                "reasoning": reasoning,
                "positioning_enriched_by_elevia": enriched,
            }

        except Exception as e:
            logger.error(f"Positioning selection failed: {e}, using defaults")
            return {
                "positioning": VALID_ANGLES[0],
                "skill_profile": "general_business_data",
                "reasoning": "Fallback due to error",
                "positioning_enriched_by_elevia": enriched if matching_signals else False,
            }

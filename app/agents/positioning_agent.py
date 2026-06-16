import logging
from app.services.openai_service import generate_text
from app.prompts.positioning_prompt import get_positioning_prompt

logger = logging.getLogger(__name__)

VALID_ANGLES = [
    "Data Analyst BI",
    "Marketing Data Analyst",
    "Data & AI Project Analyst",
    "Automation / AI Workflow Analyst",
    "Data Steward / Data Quality",
    "Business Analyst orienté data",
    "Product / Ops Analyst",
]

class PositioningAgent:
    """Choose best positioning angle + skill profile for the candidate."""

    @staticmethod
    async def choose_angle(analysis: dict) -> dict:
        """Choose positioning angle + skill profile (JSON mode).

        Returns validated dict with:
        {
            "positioning": angle from VALID_ANGLES,
            "skill_profile": key from SKILL_PROFILES,
            "reasoning": explanation
        }
        """
        from app.services.openai_service import generate_cv_payload
        from app.config.skill_profiles import validate_skill_profile

        prompt = get_positioning_prompt(analysis)

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
                f"skill_profile={skill_profile}"
            )
            logger.debug(f"Reasoning: {reasoning}")

            return {
                "positioning": positioning,
                "skill_profile": skill_profile,
                "reasoning": reasoning,
            }

        except Exception as e:
            logger.error(f"Positioning selection failed: {e}, using defaults")
            return {
                "positioning": VALID_ANGLES[0],
                "skill_profile": "general_business_data",
                "reasoning": "Fallback due to error",
            }

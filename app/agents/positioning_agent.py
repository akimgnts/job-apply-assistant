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
    """Choose best positioning angle for the candidate."""

    @staticmethod
    async def choose_angle(analysis: dict) -> str:
        """
        Choose positioning angle from predefined list.
        Falls back to first valid angle if AI output is invalid.
        """
        prompt = get_positioning_prompt(analysis)

        try:
            angle = await generate_text(prompt)
            angle = angle.strip()

            if angle in VALID_ANGLES:
                logger.info(f"Selected positioning angle: {angle}")
                return angle
            else:
                logger.warning(f"Invalid angle returned: {angle}, using default")
                return VALID_ANGLES[0]
        except Exception as e:
            logger.error(f"Positioning selection failed: {e}, using default")
            return VALID_ANGLES[0]

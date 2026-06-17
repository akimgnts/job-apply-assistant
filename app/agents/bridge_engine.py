import logging
from sqlalchemy.orm import Session
from app.services.openai_service import generate_text
from app.prompts.bridge_prompt import get_bridge_prompt
from app.services.master_cv_service import load_master_cv

logger = logging.getLogger(__name__)

class BridgeEngine:
    """Explicit reasoning: Why does this candidate make sense for this role?

    Before CV adaptation, reason through:
    1. What business problem does the role solve?
    2. What does the candidate actually possess?
    3. Where are the overlaps?
    4. Where are the gaps?

    This reasoning informs positioning + adaptation strategy.
    Never erase gaps. Never compensate with invented experience.
    """

    @staticmethod
    async def reason_fit(analysis: dict, positioning: str) -> dict:
        """Analyze candidate-role fit explicitly.

        Returns:
        {
            "business_problem": "What the company is solving",
            "primary_strengths": ["Strength 1", "Strength 2"],
            "gaps": ["Gap 1", "Gap 2"],
            "bridges": ["How we connect strength to need"],
            "seniority_assessment": "Junior|Mid|Senior|Overqualified",
            "positioning_rationale": "Why this positioning makes sense",
        }
        """
        master_cv = load_master_cv()

        prompt = get_bridge_prompt(analysis, positioning, master_cv)

        try:
            from app.services.openai_service import generate_cv_payload
            result = await generate_cv_payload(prompt)

            logger.info(f"Bridge reasoning completed for {analysis.get('job_title', 'Unknown')}")
            logger.debug(f"Bridges: {result.get('bridges', [])}")
            logger.debug(f"Gaps: {result.get('gaps', [])}")

            return {
                "business_problem": result.get("business_problem", ""),
                "primary_strengths": result.get("primary_strengths", []),
                "gaps": result.get("gaps", []),
                "bridges": result.get("bridges", []),
                "seniority_assessment": result.get("seniority_assessment", "Mid"),
                "positioning_rationale": result.get("positioning_rationale", ""),
            }

        except Exception as e:
            logger.error(f"Bridge reasoning failed: {e}")
            return {
                "business_problem": "Unable to analyze",
                "primary_strengths": [],
                "gaps": [],
                "bridges": [],
                "seniority_assessment": "Mid",
                "positioning_rationale": "Error in bridge analysis",
            }

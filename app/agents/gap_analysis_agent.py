import logging
from sqlalchemy.orm import Session
from app.services.openai_service import generate_cv_payload
from app.prompts.gap_analysis_prompt import get_gap_analysis_prompt
from app.services.master_cv_service import load_master_cv

logger = logging.getLogger(__name__)


class GapAnalysisAgent:
    """Measure exact gap between offer and candidate.

    P0: Not about understanding offer better.
    About measuring MISMATCH.

    Input: analysis + positioning
    Output: structured gap assessment with confidence score
    """

    @staticmethod
    async def analyze_gap(analysis: dict, positioning: str) -> dict:
        """Analyze gap between offer and Akim.

        Returns:
        {
            "role_family": "data_engineering|marketing|product|ops|finance|automation|governance",
            "required_level": "junior|mid|senior|lead|director",
            "candidate_level": "junior|mid|senior",
            "level_gap": "junior_vs_mid" (if gap exists, else null),
            "must_haves": {
                "SQL": true,
                "Python": true,
                "Team Leadership": false
            },
            "nice_to_haves": {
                "Snowflake": true,
                "Power BI": true,
                "Machine Learning": false
            },
            "missing_dimensions": [
                "Team leadership experience",
                "People management"
            ],
            "bridges": [
                "Automation experience can support team efficiency",
                "Data analysis can inform team decisions"
            ],
            "fit_factors": {
                "family_match": 0.85,
                "level_match": 0.50,
                "skill_match": 0.70,
                "seniority_feasible": false
            },
            "confidence": 0.62,
            "confidence_rationale": "Family matches well (data engineering), but senior level
                                     significantly above current junior level. Strong technical
                                     foundation but lacking management experience."
        }
        """
        master_cv = load_master_cv()

        prompt = get_gap_analysis_prompt(analysis, positioning, master_cv)

        try:
            result = await generate_cv_payload(prompt)

            confidence = result.get("confidence", 0.5)
            logger.info(
                f"Gap analysis: family={result.get('role_family')}, "
                f"level_gap={result.get('level_gap')}, "
                f"confidence={confidence}"
            )

            if result.get("missing_dimensions"):
                logger.debug(f"Missing: {result.get('missing_dimensions')}")

            if result.get("bridges"):
                logger.debug(f"Bridges: {result.get('bridges')}")

            return result

        except Exception as e:
            logger.error(f"Gap analysis failed: {e}")
            return {
                "role_family": "unknown",
                "required_level": "unknown",
                "candidate_level": "mid",
                "level_gap": None,
                "must_haves": {},
                "nice_to_haves": {},
                "missing_dimensions": [],
                "bridges": [],
                "fit_factors": {
                    "family_match": 0.5,
                    "level_match": 0.5,
                    "skill_match": 0.5,
                    "seniority_feasible": True,
                },
                "confidence": 0.5,
                "confidence_rationale": "Error in gap analysis",
            }

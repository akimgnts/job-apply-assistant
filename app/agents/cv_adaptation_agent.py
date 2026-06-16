import logging
from app.services.openai_service import generate_cv_payload
from app.prompts.adaptation_prompt import get_cv_adaptation_prompt

logger = logging.getLogger(__name__)


class CVAdaptationAgent:
    """Adapt Master CV to job offer. Never invent content.

    Takes existing Master CV content and adapts it:
    - Changes title to positioning
    - Rewrites summary for offer relevance
    - Reorders experiences by relevance
    - Emphasizes relevant bullets
    - Adjusts skill section
    - Adds ATS keywords
    """

    @staticmethod
    async def adapt_cv(
        analysis: dict,
        positioning: str,
        master_cv_data: dict,
    ) -> dict:
        """Adapt Master CV to job offer.

        Args:
            analysis: Job analysis (company, skills, missions, etc.)
            positioning: Chosen positioning angle
            master_cv_data: Master CV structure with all content

        Returns:
            Adaptation JSON:
            {
                "title": "Adapted title",
                "summary": "Adapted summary",
                "experience_order": [exp_ids],
                "experience_bullets": {exp_id: [bullets]},
                "project_order": [proj_ids],
                "project_bullets": {proj_id: [bullets]},
                "ats_keywords": [keywords]
            }
        """
        prompt = get_cv_adaptation_prompt(
            analysis,
            positioning,
            master_cv_data,
        )

        try:
            adaptation = await generate_cv_payload(prompt)
            logger.info(
                f"CV adapted: title={adaptation.get('title', 'N/A')}, "
                f"experiences_ordered={len(adaptation.get('experience_order', []))}, "
                f"projects_ordered={len(adaptation.get('project_order', []))}"
            )
            return adaptation
        except Exception as e:
            logger.error(f"CV adaptation failed: {e}")
            raise

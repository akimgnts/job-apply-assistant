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
        skill_profile: str = "general_business_data",
    ) -> dict:
        """Adapt Master CV to job offer using skill profile.

        Args:
            analysis: Job analysis (company, skills, missions, etc.)
            positioning: Chosen positioning angle
            master_cv_data: Master CV structure with all content
            skill_profile: Skill profile key for emphasis rules

        Returns:
            Adaptation JSON:
            {
                "title": "Adapted title",
                "summary": "Adapted summary",
                "experience_order": [exp_ids],
                "experience_bullets": {exp_id: [bullets]},
                "project_order": [proj_ids],
                "project_bullets": {proj_id: [bullets]},
                "skill_section_order": [section_labels],
                "skill_section_emphasis": {label: visibility},
                "ats_keywords": [keywords]
            }
        """
        prompt = get_cv_adaptation_prompt(
            analysis,
            positioning,
            master_cv_data,
            skill_profile,
        )

        try:
            adaptation = await generate_cv_payload(prompt)
            logger.info(
                f"CV adapted: title={adaptation.get('title', 'N/A')}, "
                f"skill_profile={skill_profile}, "
                f"experiences_ordered={len(adaptation.get('experience_order', []))}, "
                f"projects_ordered={len(adaptation.get('project_order', []))}"
            )
            return adaptation
        except Exception as e:
            logger.error(f"CV adaptation failed: {e}")
            raise

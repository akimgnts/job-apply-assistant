import logging
from app.services.openai_service import generate_cv_payload
from app.prompts.project_narrative_lite_prompt import get_project_narrative_lite_prompt

logger = logging.getLogger(__name__)


class ProjectNarrativeLiteAgent:
    """P1 Lite: Make projects credible without bloating CV.

    Rules:
    - Elevia: max 2 bullets
    - Job Apply Assistant: max 2 bullets
    - V.I.E Matcher: max 1 bullet
    - Total: max 5 project bullets

    Purpose: Evidence of capability, not main story.
    Sidel remains anchor. Projects stay focused.
    """

    @staticmethod
    async def enhance_projects(
        projects: list,
        positioning: str,
        skill_profile: str = "general_business_data",
    ) -> dict:
        """Enhance project bullets to be credible + role-relevant.

        Input: raw projects from master CV
        Output: 2/2/1 project bullets (total 5 max)
        """
        prompt = get_project_narrative_lite_prompt(projects, positioning, skill_profile)

        try:
            result = await generate_cv_payload(prompt)

            total = result.get("total_project_bullets", 5)
            if total > 5:
                logger.warning(f"Project bullet sum exceeded: {total}, should be ≤5")

            logger.info(
                f"Project narrative enhanced: "
                f"Elevia={len(result['projects'][0].get('bullets', []))}, "
                f"JAA={len(result['projects'][1].get('bullets', []))}, "
                f"VIE={len(result['projects'][2].get('bullets', []))}, "
                f"total={total}"
            )

            return {
                "projects": result.get("projects", []),
                "total_project_bullets": result.get("total_project_bullets", 5),
                "notes": result.get("notes", ""),
            }

        except Exception as e:
            logger.error(f"Project narrative enhancement failed: {e}")
            # Fallback: keep original projects with 1-2 bullets each
            return {
                "projects": projects,
                "total_project_bullets": sum(len(p.get("bullets", [])) for p in projects),
                "notes": "Fallback: using original project bullets",
            }

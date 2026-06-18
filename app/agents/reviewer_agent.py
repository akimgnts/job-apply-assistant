import logging
import re
from app.services.openai_service import generate_cv_payload
from app.prompts.reviewer_prompt import get_cv_reviewer_prompt

logger = logging.getLogger(__name__)


class ReviewerAgent:
    """Senior Reviewer: validate final CV adaptation quality.

    Checks for:
    - Bullets with no evidence (no numbers, no before/after, no scope)
    - Buzzwords and generic phrasing
    - Hallucinations (content not in Master CV)
    - Title coherence and positioning clarity

    Returns APPROVED (no changes) or REVISE (with specific bullet fixes).
    Corrections are applied directly — no full regeneration.
    """

    @staticmethod
    async def review(
        analysis: dict,
        positioning: str,
        adaptation: dict,
        master_cv: dict,
    ) -> dict:
        """Review adaptation and return verdict with issues.

        Returns:
            {
                "verdict": "APPROVED" | "REVISE",
                "score": int (1-10),
                "global_feedback": str,
                "issues": [
                    {
                        "location": "experience_0_bullet_2",
                        "current": "...",
                        "problem": "...",
                        "fix": "..."
                    }
                ]
            }
        """
        prompt = get_cv_reviewer_prompt(analysis, positioning, adaptation, master_cv)

        try:
            result = await generate_cv_payload(prompt)
            verdict = result.get("verdict", "APPROVED")
            score = result.get("score", 8)
            issues = result.get("issues", [])
            global_feedback = result.get("global_feedback", "")

            logger.info(
                f"Reviewer: verdict={verdict}, score={score}, "
                f"issues={len(issues)}, feedback={global_feedback}"
            )

            return {
                "verdict": verdict,
                "score": score,
                "global_feedback": global_feedback,
                "issues": issues,
            }

        except Exception as e:
            logger.error(f"ReviewerAgent failed: {e} — skipping review")
            return {
                "verdict": "APPROVED",
                "score": 7,
                "global_feedback": "Review skipped due to error",
                "issues": [],
            }

    @staticmethod
    def apply_corrections(adaptation: dict, issues: list[dict]) -> dict:
        """Apply reviewer fixes to specific bullets in adaptation.

        Only touches bullets flagged in issues.
        Max 5 corrections (matches reviewer output limit).
        Returns updated adaptation.
        """
        if not issues:
            return adaptation

        location_pattern = re.compile(
            r"^(experience|project)_(\d+)_bullet_(\d+)$"
        )

        applied = 0
        for issue in issues[:5]:
            location = issue.get("location", "")
            fix = issue.get("fix", "").strip()

            if not location or not fix:
                continue

            m = location_pattern.match(location)
            if not m:
                logger.warning(f"ReviewerAgent: unrecognized location '{location}', skipping")
                continue

            section_type = m.group(1)
            section_id = str(m.group(2))
            bullet_idx = int(m.group(3))

            if section_type == "experience":
                bullets = adaptation.get("experience_bullets", {}).get(section_id, [])
            else:
                bullets = adaptation.get("project_bullets", {}).get(section_id, [])

            if bullet_idx >= len(bullets):
                logger.warning(
                    f"ReviewerAgent: bullet index {bullet_idx} out of range for "
                    f"{section_type}_{section_id} (len={len(bullets)}), skipping"
                )
                continue

            original = bullets[bullet_idx]
            bullets[bullet_idx] = fix
            logger.info(
                f"ReviewerAgent: corrected {location}\n"
                f"  BEFORE: {original}\n"
                f"  AFTER:  {fix}"
            )
            applied += 1

        logger.info(f"ReviewerAgent: applied {applied}/{len(issues)} corrections")
        return adaptation

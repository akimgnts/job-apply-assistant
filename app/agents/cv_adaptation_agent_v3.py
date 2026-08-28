"""CVAdaptationAgent V3: Index-based selection, no rewriting.

CRITICAL: OpenAI returns ONLY indexes (experience_index, bullet_indices).
Python fetches exact text from Master CV using these indexes.
Final rendered text is BYTE-FOR-BYTE from Master CV source.

Principles:
1. Master CV is source of truth
2. OpenAI selects relevant indexes only
3. OpenAI NEVER sees or returns final bullet text
4. Selected text copied exactly from Master CV
5. No rewriting, adaptation, or emphasis by rewording
"""

import logging
import json
from typing import Dict, List, Optional
from app.services.openai_service import call_openai

logger = logging.getLogger(__name__)


class CVAdaptationAgentV3:
    """Select relevant Master CV content by index, fetch exact text from source."""

    @staticmethod
    async def adapt_cv(
        analysis: dict,
        positioning: str,
        master_cv_data: dict,
    ) -> dict:
        """Return index-based selection. NO TEXT GENERATION.

        Args:
            analysis: Job offer analysis
            positioning: Validated candidate positioning
            master_cv_data: Master CV with locked content

        Returns:
            {
              "title": positioning,
              "summary": safe summary (from Master CV or minimal template),
              "selected_experiences": [
                {
                  "experience_index": 0,
                  "bullet_indices": [0, 1, 2, 4],  // Skip bullet 3 if weak
                  "order": 1
                }
              ],
              "selected_projects": [...],
              "selected_skills": [0, 1, 2, 4],  // Skill indexes
              "metadata": {...}
            }
        """
        try:
            # Step 1: Score relevance and get selection indexes
            selection = await CVAdaptationAgentV3._score_and_select_indexes(
                analysis, positioning, master_cv_data
            )

            # Step 2: Extract summary (from Master CV, not generated)
            summary = CVAdaptationAgentV3._get_safe_summary(
                positioning, master_cv_data
            )

            # Step 3: Assemble adaptation with indexes only (NO TEXT)
            # Normalize to conversion-compatible format
            normalized_experiences = [
                {
                    "source_id": exp["experience_index"],
                    "bullet_indices": exp.get("bullet_indices", []),
                    "order": exp.get("order", i + 1),
                    "show": True,  # Selected experiences are always shown
                    "relevance": exp.get("relevance", 1.0),
                }
                for i, exp in enumerate(selection.get("selected_experiences", []))
            ]

            normalized_projects = [
                {
                    "source_id": proj["project_index"],
                    "bullet_indices": proj.get("bullet_indices", []),
                    "order": proj.get("order", i + 1),
                    "show": True,  # Selected projects are always shown
                    "relevance": proj.get("relevance", 1.0),
                }
                for i, proj in enumerate(selection.get("selected_projects", []))
            ]

            adaptation = {
                "title": positioning,
                "summary": summary,
                "selected_experience_blocks": normalized_experiences,
                "selected_project_blocks": normalized_projects,
                "selected_skill_blocks": selection.get("selected_skills", []),
                "metadata": {
                    "source": "cv_adaptation_agent_v3",
                    "strategy": "index_based_selection_no_rewriting",
                    "approach": "master_cv_is_source_of_truth",
                    "has_bullet_indices": True,
                },
            }

            logger.info(
                f"CV adapted (index-based): {len(adaptation['selected_experience_blocks'])} experiences, "
                f"{len(adaptation['selected_project_blocks'])} projects, "
                f"{len(adaptation['selected_skill_blocks'])} skills"
            )
            return adaptation

        except Exception as e:
            logger.error(f"CV adaptation failed: {e}", exc_info=True)
            raise

    @staticmethod
    async def _score_and_select_indexes(
        analysis: dict,
        positioning: str,
        master_cv_data: dict,
    ) -> dict:
        """Use OpenAI to score relevance. Return INDEXES ONLY, no text.

        OpenAI receives:
        - Job requirements
        - Candidate positioning
        - Master CV structure (titles, dates, but NO bullet text or skill content)

        OpenAI returns:
        - experience_index + bullet_indices to include
        - project_index + bullet_indices to include
        - skill_index list to include
        """
        prompt = CVAdaptationAgentV3._build_selection_prompt(
            analysis, positioning, master_cv_data
        )

        try:
            response_text = await call_openai(prompt, json_mode=True)
            response = json.loads(response_text)

            # Validate and sanitize indexes
            selection = {
                "selected_experiences": CVAdaptationAgentV3._validate_experience_indexes(
                    response.get("experiences", []),
                    len(master_cv_data.get("experiences", [])),
                ),
                "selected_projects": CVAdaptationAgentV3._validate_project_indexes(
                    response.get("projects", []),
                    len(master_cv_data.get("projects", [])),
                ),
                "selected_skills": CVAdaptationAgentV3._validate_skill_indexes(
                    response.get("skills", []),
                    len(master_cv_data.get("skills", [])),
                ),
            }

            logger.info(
                f"Selection scored: {len(selection['selected_experiences'])} experiences, "
                f"{len(selection['selected_projects'])} projects, "
                f"{len(selection['selected_skills'])} skills"
            )
            return selection

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse selection response: {e}")
            return CVAdaptationAgentV3._build_fallback_indexes(master_cv_data)
        except Exception as e:
            logger.error(f"Selection scoring failed: {e}")
            return CVAdaptationAgentV3._build_fallback_indexes(master_cv_data)

    @staticmethod
    def _build_selection_prompt(
        analysis: dict,
        positioning: str,
        master_cv_data: dict,
    ) -> str:
        """Build prompt that scores relevance WITHOUT exposing bullet text.

        This is the CRITICAL difference from V1/V2:
        OpenAI sees only METADATA (titles, dates, company, bullet count).
        OpenAI NEVER sees actual bullet content.
        """

        # Format experiences (metadata only, NO bullet text)
        exp_text = "\n".join(
            [
                f"Experience #{i}: {e['title']} @ {e['company']} ({e['dates']})\n"
                f"  {len(e.get('bullets', []))} bullets available"
                for i, e in enumerate(master_cv_data.get("experiences", []))
            ]
        )

        # Format projects (metadata only, NO bullet text)
        proj_text = "\n".join(
            [
                f"Project #{i}: {p['title']}\n"
                f"  Stack: {p.get('stack', 'N/A')}\n"
                f"  {len(p.get('bullets', []))} bullets available"
                for i, p in enumerate(master_cv_data.get("projects", []))
            ]
        )

        # Format skills (labels only, NO content)
        skill_text = "\n".join(
            [f"Skill #{i}: {s.get('label', 'N/A')}" for i, s in enumerate(master_cv_data.get("skills", []))]
        )

        return f"""TASK: Select relevant Master CV sections by INDEX.

CRITICAL CONSTRAINT: You NEVER see or return bullet text.
You ONLY return indexes (which_experience, which_bullets, which_projects).

Python will fetch actual text from Master CV using your indexes.

---

JOB CONTEXT

Position: {analysis.get('job_title', 'N/A')} @ {analysis.get('company', 'N/A')}
Candidate positioning: {positioning}

Missions: {', '.join(analysis.get('missions', [])[:3])}
Required skills: {', '.join(analysis.get('required_skills', [])[:5])}

---

CANDIDATE MASTER CV STRUCTURE (METADATA ONLY)

Experiences:
{exp_text}

Projects:
{proj_text}

Skills:
{skill_text}

---

TASK

For each experience/project/skill, decide:
1. Is it relevant? (yes/no)
2. If yes, which bullets should be included? (provide indexes)
3. What order? (1, 2, 3...)

IMPORTANT:
- You do NOT see bullet content
- You only see "X bullets available"
- You return: include_this_experience, these_bullet_indexes
- Python fetches the actual text using your indexes

Return JSON ONLY:

{{
  "experiences": [
    {{
      "experience_index": 0,
      "bullet_count_available": 7,
      "selected_bullet_indices": [0, 1, 2, 4, 5],
      "order": 1,
      "reason": "Sidel has BI/dashboards/data analysis - direct match"
    }},
    {{
      "experience_index": 1,
      "bullet_count_available": 5,
      "selected_bullet_indices": [0, 1, 2, 3],
      "order": 2,
      "reason": "MadeByAkim automation and APIs relevant"
    }},
    {{
      "experience_index": 2,
      "bullet_count_available": 3,
      "selected_bullet_indices": [],
      "order": 3,
      "reason": "Vassard sales-focused, not relevant"
    }}
  ],
  "projects": [
    {{
      "project_index": 0,
      "bullet_count_available": 3,
      "selected_bullet_indices": [0, 1],
      "order": 1,
      "reason": "Elevia data + AI project"
    }},
    {{
      "project_index": 1,
      "bullet_count_available": 1,
      "selected_bullet_indices": [0],
      "order": 2,
      "reason": "Job Apply Assistant automation"
    }},
    {{
      "project_index": 2,
      "bullet_count_available": 1,
      "selected_bullet_indices": [],
      "reason": "V.I.E Matcher less relevant"
    }}
  ],
  "skills": [0, 1, 2, 3, 4]
}}
"""

    @staticmethod
    def _validate_experience_indexes(
        experience_list: list,
        num_experiences: int,
    ) -> list:
        """Validate and sanitize experience selection from OpenAI.

        Returns list of {experience_index, bullet_indices, order, relevance}.
        """
        validated = []

        for idx, exp in enumerate(experience_list):
            if not isinstance(exp, dict):
                continue

            exp_idx = exp.get("experience_index")
            if not isinstance(exp_idx, int) or exp_idx < 0 or exp_idx >= num_experiences:
                continue

            bullet_indices = exp.get("selected_bullet_indices", [])
            if not isinstance(bullet_indices, list):
                continue

            # Validate each bullet index
            valid_bullets = []
            for bi in bullet_indices:
                if isinstance(bi, int) and bi >= 0:
                    valid_bullets.append(bi)

            validated.append(
                {
                    "experience_index": exp_idx,
                    "bullet_indices": valid_bullets,
                    "order": exp.get("order", idx + 1),
                    "relevance": exp.get("relevance", 1.0 - (idx * 0.1)),
                }
            )

        return validated

    @staticmethod
    def _validate_project_indexes(
        project_list: list,
        num_projects: int,
    ) -> list:
        """Validate and sanitize project selection from OpenAI.

        Returns list of {project_index, bullet_indices, order, relevance}.
        """
        validated = []

        for idx, proj in enumerate(project_list):
            if not isinstance(proj, dict):
                continue

            proj_idx = proj.get("project_index")
            if not isinstance(proj_idx, int) or proj_idx < 0 or proj_idx >= num_projects:
                continue

            bullet_indices = proj.get("selected_bullet_indices", [])
            if not isinstance(bullet_indices, list):
                continue

            valid_bullets = [bi for bi in bullet_indices if isinstance(bi, int) and bi >= 0]

            validated.append(
                {
                    "project_index": proj_idx,
                    "bullet_indices": valid_bullets,
                    "order": proj.get("order", idx + 1),
                    "relevance": proj.get("relevance", 1.0 - (idx * 0.15)),
                }
            )

        return validated

    @staticmethod
    def _validate_skill_indexes(skill_list: list, num_skills: int) -> list:
        """Validate and sanitize skill selection from OpenAI."""
        validated = []
        seen = set()

        for skill_idx in skill_list:
            if isinstance(skill_idx, int) and 0 <= skill_idx < num_skills:
                if skill_idx not in seen:
                    validated.append(skill_idx)
                    seen.add(skill_idx)

        return validated

    @staticmethod
    def _get_safe_summary(positioning: str, master_cv_data: dict) -> str:
        """Get summary from Master CV, not generated.

        Two options:
        1. Use existing Master CV summary if available
        2. Build minimal template from positioning only
        """
        # Option: Check if Master CV has a pre-written summary
        # (For now, use minimal template)

        parts = positioning.split("|")
        primary = parts[0].strip()
        secondary = parts[1].strip() if len(parts) > 1 else ""

        if secondary:
            summary = f"Data-oriented professional with expertise in {primary.lower()} and {secondary.lower()}."
        else:
            summary = f"Experienced {primary.lower()} professional."

        return summary

    @staticmethod
    def _build_fallback_indexes(master_cv_data: dict) -> dict:
        """Build safe fallback when OpenAI selection fails.

        Shows all experiences with all bullets, all projects with all bullets.
        Returns normalized format compatible with adapt_cv output.
        """
        num_exp = len(master_cv_data.get("experiences", []))
        num_proj = len(master_cv_data.get("projects", []))
        num_skills = len(master_cv_data.get("skills", []))

        # Normalized format (experience_index not source_id, since we use it internally)
        selected_experiences = [
            {
                "experience_index": i,
                "bullet_indices": list(range(len(master_cv_data["experiences"][i].get("bullets", [])))),
                "order": i + 1,
                "relevance": 1.0 - (i * 0.1),
            }
            for i in range(num_exp)
        ]

        selected_projects = [
            {
                "project_index": i,
                "bullet_indices": list(range(len(master_cv_data["projects"][i].get("bullets", [])))),
                "order": i + 1,
                "relevance": 1.0 - (i * 0.15),
            }
            for i in range(num_proj)
        ]

        selected_skills = list(range(num_skills))

        logger.warning("Using fallback selection (OpenAI unavailable)")
        return {
            "selected_experiences": selected_experiences,
            "selected_projects": selected_projects,
            "selected_skills": selected_skills,
        }

"""CV Adaptation Agent V2: Source-preserving selection (no content generation).

PHILOSOPHY: Master CV is the single source of truth. This agent selects and orders
sections by relevance to the job, but NEVER rewrites experience/project bullets or
generates new summary content.

Pipeline:
1. Load Master CV (locked, authoritative)
2. Score each section for job relevance (via OpenAI)
3. Select top N sections
4. Suggest ordering by relevance
5. Return source block IDs only
6. Renderer fetches actual text from source
7. QualityAgent validates result against sources
"""

import logging
import json
from typing import Dict, List, Optional
from app.services.openai_service import call_openai
from app.services.summary_service import build_deterministic_summary
from app.prompts.cv_selection_prompt import get_cv_selection_prompt

logger = logging.getLogger(__name__)


class CVAdaptationAgent:
    """Select and order Master CV sections by job relevance.

    Never generates new factual content. Uses OpenAI ONLY for scoring relevance.
    Actual CV text comes directly from Master CV source.
    """

    @staticmethod
    async def adapt_cv(
        analysis: dict,
        positioning: str,
        master_cv_data: dict,
    ) -> dict:
        """Adapt Master CV by selecting and ordering relevant sections.

        CRITICAL: Output contains source block IDs, not generated text.
        Renderer must fetch actual text from master_cv_data using these IDs.

        Args:
            analysis: Job offer analysis (company, missions, skills, keywords)
            positioning: Selected positioning angle (validated, safe)
            master_cv_data: Master CV structure with all content locked

        Returns:
            Adaptation JSON with source block references:
            {
              "title": "Validated positioning title",
              "summary": "Deterministic summary from positioning + skills",
              "selected_experience_blocks": [
                {"source_id": 0, "relevance": 0.95, "show": true, "order": 1},
                {"source_id": 1, "relevance": 0.85, "show": true, "order": 2},
                ...
              ],
              "selected_project_blocks": [...],
              "selected_skill_blocks": [...],
              "metadata": {
                "source": "cv_adaptation_agent_v2",
                "strategy": "source_preserving_selection"
              }
            }
        """
        try:
            # Step 1: Use OpenAI to score relevance (METADATA ONLY)
            selection = await CVAdaptationAgent._score_and_select(
                analysis, positioning, master_cv_data
            )

            # Step 2: Extract selected skill IDs for deterministic summary
            selected_skill_ids = [
                block["source_id"]
                for block in selection.get("selected_skill_blocks", [])
                if block.get("show", True)
            ]

            # Step 3: Build deterministic summary (no OpenAI)
            summary = build_deterministic_summary(
                positioning,
                master_cv_data.get("skills", []),
                selected_skill_ids,
            )

            # Step 4: Assemble final adaptation
            adaptation = {
                "title": positioning,
                "summary": summary,
                "selected_experience_blocks": selection.get("selected_experience_blocks", []),
                "selected_project_blocks": selection.get("selected_project_blocks", []),
                "selected_skill_blocks": selection.get("selected_skill_blocks", []),
                "metadata": {
                    "source": "cv_adaptation_agent_v2",
                    "strategy": "source_preserving_selection",
                    "num_experiences": len(selection.get("selected_experience_blocks", [])),
                    "num_projects": len(selection.get("selected_project_blocks", [])),
                    "num_skills": len(selection.get("selected_skill_blocks", [])),
                },
            }

            logger.info(
                f"CV adapted (source-preserving): title={positioning}, "
                f"experiences={len(selection.get('selected_experience_blocks', []))}, "
                f"projects={len(selection.get('selected_project_blocks', []))}"
            )
            return adaptation

        except Exception as e:
            logger.error(f"CV adaptation failed: {e}", exc_info=True)
            raise

    @staticmethod
    async def _score_and_select(
        analysis: dict,
        positioning: str,
        master_cv_data: dict,
    ) -> dict:
        """Use OpenAI to score sections by relevance (metadata only).

        OpenAI returns scores and ordering, NOT content rewrites.
        All text will come from master_cv_data.

        Returns:
            {
              "selected_experience_blocks": [{"source_id": 0, "relevance": ..., "show": True, "order": 1}, ...],
              "selected_project_blocks": [...],
              "selected_skill_blocks": [...]
            }
        """
        prompt = get_cv_selection_prompt(analysis, positioning, master_cv_data)

        try:
            # Call OpenAI to score relevance (returns JSON metadata)
            response_text = await call_openai(prompt, json_mode=True)
            response = json.loads(response_text)

            # Validate response structure
            if not isinstance(response, dict):
                logger.error(f"Invalid selection response type: {type(response)}")
                return CVAdaptationAgent._build_fallback_selection(master_cv_data)

            # Extract sections, apply safety checks
            selection = {
                "selected_experience_blocks": CVAdaptationAgent._validate_section(
                    response.get("experiences", []),
                    max_sections=len(master_cv_data.get("experiences", [])),
                ),
                "selected_project_blocks": CVAdaptationAgent._validate_section(
                    response.get("projects", []),
                    max_sections=len(master_cv_data.get("projects", [])),
                ),
                "selected_skill_blocks": CVAdaptationAgent._validate_section(
                    response.get("skills", []),
                    max_sections=len(master_cv_data.get("skills", [])),
                ),
            }

            logger.info(
                f"Selection scored: "
                f"{len(selection['selected_experience_blocks'])} experiences, "
                f"{len(selection['selected_project_blocks'])} projects, "
                f"{len(selection['selected_skill_blocks'])} skills"
            )
            return selection

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse selection response as JSON: {e}")
            return CVAdaptationAgent._build_fallback_selection(master_cv_data)
        except Exception as e:
            logger.error(f"Selection scoring failed: {e}")
            return CVAdaptationAgent._build_fallback_selection(master_cv_data)

    @staticmethod
    def _validate_section(
        section_data: list,
        max_sections: int,
    ) -> list:
        """Validate and sanitize section data from OpenAI.

        Ensures:
        - source_id is within bounds
        - relevance is 0-1
        - show is boolean
        - order is positive integer

        Returns:
            List of validated section blocks
        """
        validated = []
        seen_ids = set()

        for block in section_data:
            if not isinstance(block, dict):
                continue

            source_id = block.get("id")
            if not isinstance(source_id, int) or source_id < 0 or source_id >= max_sections:
                logger.warning(f"Invalid source_id: {source_id} (max={max_sections})")
                continue

            if source_id in seen_ids:
                logger.warning(f"Duplicate source_id: {source_id}")
                continue

            relevance = block.get("relevance", 0.0)
            if not isinstance(relevance, (int, float)):
                relevance = 0.0
            relevance = max(0.0, min(1.0, float(relevance)))

            show = block.get("show", True)
            if not isinstance(show, bool):
                show = True

            order = block.get("order", len(validated) + 1)
            if not isinstance(order, int):
                order = len(validated) + 1

            validated.append(
                {
                    "source_id": source_id,
                    "relevance": relevance,
                    "show": show,
                    "order": order,
                }
            )
            seen_ids.add(source_id)

        return validated

    @staticmethod
    def _build_fallback_selection(master_cv_data: dict) -> dict:
        """Build safe fallback when OpenAI selection fails.

        Shows all experiences (main to secondary order).
        Shows top 3 projects.
        Shows all skill sections.
        """
        num_experiences = len(master_cv_data.get("experiences", []))
        num_projects = len(master_cv_data.get("projects", []))
        num_skills = len(master_cv_data.get("skills", []))

        # All experiences, in order
        exp_blocks = [
            {"source_id": i, "relevance": 1.0 - (i * 0.1), "show": True, "order": i + 1}
            for i in range(num_experiences)
        ]

        # Top 3 projects
        proj_blocks = [
            {"source_id": i, "relevance": 1.0 - (i * 0.15), "show": i < 3, "order": i + 1}
            for i in range(num_projects)
        ]

        # All skills
        skill_blocks = [
            {"source_id": i, "relevance": 1.0 - (i * 0.05), "show": True, "order": i + 1}
            for i in range(num_skills)
        ]

        logger.warning("Using fallback selection (OpenAI unavailable)")
        return {
            "selected_experience_blocks": exp_blocks,
            "selected_project_blocks": proj_blocks,
            "selected_skill_blocks": skill_blocks,
        }

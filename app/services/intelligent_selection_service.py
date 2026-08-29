"""Intelligent fallback selection based on job offer relevance.

NOT first-N selection. NOT exhaustive.

Scores each Master CV bullet against job offer requirements and ranks by relevance.
Selects strongest bullets while preserving experience diversity.
Different job offers produce different selections.
"""

import logging
from typing import Dict, List, Tuple
import re

logger = logging.getLogger(__name__)


class RelevanceScorer:
    """Score Master CV bullets against job offer."""

    @staticmethod
    def score_bullet(
        bullet: str,
        job_title: str,
        required_skills: List[str],
        missions: List[str],
        company: str = "",
    ) -> float:
        """Score a Master CV bullet for relevance to job offer.

        Returns 0.0-1.0 score based on:
        - Keyword overlap (missions, skills)
        - Technology mentions
        - Business domain alignment
        - Quantifiable results
        """
        if not bullet:
            return 0.0

        score = 0.0
        bullet_lower = bullet.lower()

        # 1. Mission/skill keyword matching (weighted heavily)
        skill_matches = sum(
            1 for skill in required_skills
            if skill.lower() in bullet_lower
        )
        score += min(skill_matches * 0.15, 0.3)

        mission_matches = sum(
            1 for mission in missions
            if mission.lower() in bullet_lower
        )
        score += min(mission_matches * 0.1, 0.25)

        # 2. Technology mentions (strong signal)
        tech_keywords = [
            "power bi", "sql", "python", "fastapi", "postgresql",
            "docker", "api", "automation", "dashboard", "reporting",
            "data", "analytics", "etl", "pipeline", "integration"
        ]
        tech_hits = sum(1 for tech in tech_keywords if tech in bullet_lower)
        score += min(tech_hits * 0.08, 0.25)

        # 3. Business impact/results (strong signal - numbers, reductions, etc)
        if re.search(r'\d+\+|\d+\%|reduction|increase|improvement|automated', bullet_lower):
            score += 0.15

        # 4. Avoid obviously irrelevant bullets
        irrelevant_keywords = [
            "sales", "management", "hr", "recruitment", "finance",
            "legal", "support", "customer service"
        ]
        if any(kw in bullet_lower for kw in irrelevant_keywords):
            score = max(0, score - 0.2)

        # 5. Recency/relevance boost for recent technologies
        modern_keywords = [
            "fastapi", "postgres", "docker", "kubernetes", "ai", "llm",
            "openai", "langchain", "automation", "orchestration"
        ]
        if any(kw in bullet_lower for kw in modern_keywords):
            score += 0.1

        return min(score, 1.0)

    @staticmethod
    def select_relevant_bullets(
        experience_bullets: List[str],
        job_analysis: dict,
        max_bullets: int = 4,
    ) -> List[int]:
        """Select most relevant bullets (by index) from an experience.

        Args:
            experience_bullets: All Master CV bullets for this experience
            job_analysis: Job offer analysis with required_skills, missions, etc.
            max_bullets: Maximum bullets to select (default 4)

        Returns:
            List of selected bullet indices (sorted by relevance desc)
        """
        if not experience_bullets:
            return []

        job_title = job_analysis.get("job_title", "")
        required_skills = job_analysis.get("required_skills", [])
        missions = job_analysis.get("missions", [])
        company = job_analysis.get("company", "")

        # Score each bullet
        scores = []
        for idx, bullet in enumerate(experience_bullets):
            score = RelevanceScorer.score_bullet(
                bullet, job_title, required_skills, missions, company
            )
            scores.append((idx, score))

        # Sort by score descending
        scores.sort(key=lambda x: x[1], reverse=True)

        # Select top N, but only if score > 0.1 (avoid low-relevance bullets)
        selected = []
        for idx, score in scores[:max_bullets]:
            if score > 0.1:  # Relevance threshold
                selected.append(idx)

        # If we got nothing, at least take the top 1
        if not selected and scores:
            selected = [scores[0][0]]

        # Return sorted by original order (for readability)
        selected.sort()

        logger.debug(
            f"Selected {len(selected)}/{len(experience_bullets)} bullets "
            f"(scores: {[round(s, 2) for _, s in scores[:len(selected)]]})"
        )

        return selected

    @staticmethod
    def should_include_experience(
        experience: dict,
        job_analysis: dict,
    ) -> bool:
        """Determine if an experience should be included.

        Include if experience has at least 1 relevant bullet (score > 0.1).
        Do NOT exclude entire experiences by domain classification.
        Bullet-level selection determines relevance.
        """
        title = experience.get("title", "").lower()
        company = experience.get("company", "").lower()
        bullets = experience.get("bullets", [])

        job_title = job_analysis.get("job_title", "").lower()
        required_skills = job_analysis.get("required_skills", [])
        missions = job_analysis.get("missions", [])

        # Score each bullet
        for bullet in bullets:
            score = RelevanceScorer.score_bullet(
                bullet,
                job_analysis.get("job_title", ""),
                required_skills,
                missions,
                job_analysis.get("company", ""),
            )
            # If ANY bullet scores above threshold, include experience
            if score > 0.1:
                logger.debug(
                    f"Including {title} @ {company}: found relevant bullet (score {score:.2f})"
                )
                return True

        # No relevant bullets found
        logger.debug(f"Excluding {title} @ {company}: no bullets score above threshold")
        return False


def build_intelligent_fallback_selection(
    master_cv: dict,
    job_analysis: dict,
) -> Tuple[List[int], Dict[str, List[int]]]:
    """Build intelligent fallback selection (not first-N, not exhaustive).

    Returns:
        (experience_order, experience_bullet_indices)
        Where bullet_indices is {exp_id: [bullet_indices]}
    """
    experience_order = []
    experience_bullet_indices = {}

    # Score and select experiences
    for exp_idx, experience in enumerate(master_cv.get("experiences", [])):
        if not RelevanceScorer.should_include_experience(experience, job_analysis):
            continue

        selected_bullets = RelevanceScorer.select_relevant_bullets(
            experience.get("bullets", []),
            job_analysis,
            max_bullets=4 if exp_idx == 0 else 3,  # Strongest exp gets more bullets
        )

        if selected_bullets:
            experience_order.append(exp_idx)
            experience_bullet_indices[str(exp_idx)] = selected_bullets

    logger.info(
        f"Intelligent fallback: selected {len(experience_order)} experiences "
        f"with {sum(len(v) for v in experience_bullet_indices.values())} total bullets"
    )

    return experience_order, experience_bullet_indices

"""Skills grouping and selection for CV rendering.

Principles:
- Select only relevant skills based on job analysis + Master CV + locked levels
- Group into semantic categories (Data & BI, Automation, etc.)
- Never include excluded skills (level 0: Jira, Confluence, GCP, Looker)
- Never auto-promote skill levels
- Render as grouped blocks, not individual cards
"""

import logging
from typing import List, Dict, Tuple

logger = logging.getLogger(__name__)


# Semantic skill categories and keywords
SKILL_CATEGORIES = {
    "Data & BI": {
        "keywords": ["power bi", "sql", "data", "analytics", "dashboard", "reporting", "dax", "excel", "query", "viz"],
        "skills": ["Power BI", "Power Query", "SQL", "Python", "Excel avancé", "DAX (mesures et KPI)"]
    },
    "Automation & Backend": {
        "keywords": ["automation", "api", "backend", "fastapi", "database", "postgresql", "rest", "webhooks", "docker", "deploy"],
        "skills": ["FastAPI", "PostgreSQL", "REST APIs", "n8n", "Make", "Google Apps Script", "Docker", "Coolify", "SQLAlchemy", "Alembic"]
    },
    "AI & LLM": {
        "keywords": ["ai", "llm", "openai", "agent", "orca", "langchain", "orchestration", "ml", "nlp", "gpt"],
        "skills": ["OpenAI API", "agents IA", "orchestration multi-agent", "LangChain", "AI Workflows"]
    },
    "Project & Business": {
        "keywords": ["project", "agile", "scrum", "kanban", "delivery", "business", "stakeholder", "analysis", "pm"],
        "skills": ["Agile", "Scrum", "Kanban", "Business Analysis", "Stakeholder Communication"]
    },
}

# Excluded skills (level 0 in Master CV)
EXCLUDED_SKILLS = {"Jira", "Confluence", "GCP", "Looker Studio"}


def select_relevant_skills(
    job_analysis: dict,
    master_cv_skills: List[Dict],
) -> List[str]:
    """Select skills relevant to the job from Master CV.

    Args:
        job_analysis: Job offer analysis with required_skills, missions, etc.
        master_cv_skills: List of available skills with levels from Master CV

    Returns:
        List of skill labels (subsets of Master CV, no new skills)
    """
    if not job_analysis or not master_cv_skills:
        return []

    # Required and preferred skills from job
    job_required = set(s.lower() for s in job_analysis.get("required_skills", []))
    job_missions = " ".join(job_analysis.get("missions", [])).lower()

    # Build Master CV skill index
    master_by_label = {s["label"]: s for s in master_cv_skills}
    master_by_lower = {s["label"].lower(): s["label"] for s in master_cv_skills}

    selected = []

    # Match job requirements against Master CV skills
    for job_skill in job_required:
        # Try exact match (case-insensitive)
        master_skill = master_by_lower.get(job_skill)
        if master_skill:
            skill_info = master_by_label[master_skill]
            # Only include if not excluded (level != 0)
            if skill_info.get("level", 3) > 0 and master_skill not in EXCLUDED_SKILLS:
                if master_skill not in selected:
                    selected.append(master_skill)
            continue

        # Try partial match
        for master_label in master_by_label.keys():
            if master_label in EXCLUDED_SKILLS:
                continue
            if job_skill in master_label.lower() or master_label.lower() in job_skill:
                skill_info = master_by_label[master_label]
                if skill_info.get("level", 3) > 0:
                    if master_label not in selected:
                        selected.append(master_label)
                    break

    # Add complementary skills based on mission context
    for master_label, skill_info in master_by_label.items():
        if master_label in EXCLUDED_SKILLS or master_label in selected:
            continue

        if skill_info.get("level", 3) == 0:
            continue

        # Check if this skill complements the missions
        skill_keywords = master_label.lower().split()
        if any(keyword in job_missions for keyword in skill_keywords):
            selected.append(master_label)

    logger.info(f"SKILLS: Selected {len(selected)} skills from {len(master_cv_skills)} available")
    return selected[:15]  # Limit to reasonable number


def group_skills_by_category(selected_skills: List[str]) -> Dict[str, List[str]]:
    """Group selected skills into semantic categories.

    Returns dict: {category_name: [skill1, skill2, ...]}
    Only includes non-empty categories.
    """
    grouped = {}

    for category, config in SKILL_CATEGORIES.items():
        category_skills = []
        for skill in selected_skills:
            if skill in config["skills"]:
                category_skills.append(skill)

        if category_skills:
            grouped[category] = category_skills

    logger.info(f"SKILLS: Grouped into {len(grouped)} categories")
    return grouped


def build_skill_groups_for_template(
    job_analysis: dict,
    master_cv_skills: List[Dict],
) -> Dict[str, List[str]]:
    """Build skill groups for CV template rendering.

    Returns: {category: [skills...]}
    """
    # Select relevant skills
    selected = select_relevant_skills(job_analysis, master_cv_skills)

    # Group into categories
    grouped = group_skills_by_category(selected)

    if not grouped:
        logger.warning("No skills selected, using complementary defaults")
        # Fallback: include at least fundamental skills
        default_skills = ["Python", "SQL", "FastAPI", "PostgreSQL", "Agile", "Business Analysis"]
        master_labels = {s["label"] for s in master_cv_skills}
        default_selected = [s for s in default_skills if s in master_labels]
        grouped = group_skills_by_category(default_selected)

    return grouped

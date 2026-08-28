"""Generate deterministic, source-based summaries for adapted CVs.

Never generate new content. Assemble from verified positioning + verified skills.
"""

import logging

logger = logging.getLogger(__name__)


def build_deterministic_summary(
    positioning: str,
    master_cv_skills: list,
    selected_skill_ids: list,
) -> str:
    """Build CV summary from positioning + selected skills.

    STRICTLY DETERMINISTIC: No OpenAI, no free-form generation.
    Only assembles from verified candidate positioning and skill blocks.

    Args:
        positioning: Selected positioning (e.g., "Data Analyst | Business Intelligence")
        master_cv_skills: All skill sections from Master CV
        selected_skill_ids: IDs of skills that will appear in this CV

    Returns:
        Safe, sourced summary (max 70 words)
    """

    # Extract positioning base
    pos_parts = positioning.split("|")
    primary_role = pos_parts[0].strip()
    secondary_spec = pos_parts[1].strip() if len(pos_parts) > 1 else ""

    # Get selected skill labels for reference
    selected_skill_labels = []
    for skill_id in selected_skill_ids:
        if skill_id < len(master_cv_skills):
            label = master_cv_skills[skill_id].get("label", "").lower()
            selected_skill_labels.append(label)

    # Build summary from positioning + skill emphasis
    if secondary_spec:
        # Positioning has explicit specialization
        summary = f"Professional with expertise in {primary_role.lower()} and {secondary_spec.lower()}."
    else:
        # Just primary role
        summary = f"Experienced {primary_role.lower()} professional."

    # Add skill area emphasis if available
    if "data & analytics" in selected_skill_labels:
        summary += " Combines data analysis, reporting and business intelligence."
    elif "automation & apis" in selected_skill_labels:
        summary += " Skilled in automation, workflow design and integration."

    if "business systems" in selected_skill_labels:
        summary += " Proficient with CRM platforms and business tools."

    # Trim to reasonable length
    if len(summary) > 140:
        summary = summary[:137] + "..."

    logger.info(f"Built deterministic summary ({len(summary)} chars) from positioning={positioning}")
    return summary

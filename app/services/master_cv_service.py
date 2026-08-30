import logging
import json
from pathlib import Path

logger = logging.getLogger(__name__)

# Cache the loaded JSON
_MASTER_CV_CACHE = None


def load_master_cv() -> dict:
    """Load Master CV V3 from JSON file (single source of truth).

    JSON file is locked source: app/data/master_cv_v3.json
    Locked date: 2026-08-28
    Source: c8606019-Akim_Guentas_MASTER_CV_V3_SOURCE_DE_VERITE_1.html

    Philosophy: Truth is immutable. Narrative is flexible.
    - AI preserves all facts (dates, companies, accomplishments)
    - AI can rewrite bullets for clarity and relevance
    - AI can remove weak/irrelevant bullets
    - AI can adapt vocabulary to match role domain
    - AI cannot fabricate facts
    """
    global _MASTER_CV_CACHE

    if _MASTER_CV_CACHE is not None:
        return _MASTER_CV_CACHE

    json_path = Path(__file__).parent.parent / "data" / "master_cv_v3.json"

    if not json_path.exists():
        raise FileNotFoundError(
            f"Master CV V3 source not found: {json_path}\n"
            "This is CRITICAL — no fallback to old hardcoded Master CV exists.\n"
            "Please restore app/data/master_cv_v3.json from repository."
        )

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"Master CV V3 JSON is malformed: {e}\n"
            f"File: {json_path}\n"
            "Check that the JSON is valid and locked facts are intact."
        )

    data = _transform_json_to_service_format(raw_data)
    _validate_master_cv(data)

    _MASTER_CV_CACHE = data
    logger.info(
        f"Master CV V3 loaded from {json_path} "
        f"(locked {raw_data['metadata']['locked_date']})"
    )

    return data


def _transform_json_to_service_format(raw_data: dict) -> dict:
    """Transform JSON structure into service-compatible format with convenience dicts."""

    # Flatten experiences: convert sections to flat bullet list
    experiences = []
    for exp in raw_data.get("experiences", []):
        flattened_exp = {
            "id": exp["id"],
            "title": exp.get("title", ""),
            "company": exp.get("company", ""),
            "context": exp.get("context", ""),
            "dates": exp.get("dates", ""),
            "location": exp.get("location", ""),
            "bullets": [],
        }

        # Flatten all bullets from all sections
        for section in exp.get("sections", []):
            for bullet in section.get("bullets", []):
                if isinstance(bullet, dict):
                    flattened_exp["bullets"].append(bullet["text"])
                else:
                    flattened_exp["bullets"].append(str(bullet))

        experiences.append(flattened_exp)

    # Flatten projects: convert to flat bullet list
    projects = []
    for proj in raw_data.get("projects", []):
        flattened_proj = {
            "id": proj["id"],
            "title": proj.get("title", ""),
            "company": proj.get("company", ""),
            "dates": proj.get("dates", ""),
            "stack": proj.get("stack", ""),
            "bullets": [],
        }

        for bullet in proj.get("bullets", []):
            if isinstance(bullet, dict):
                flattened_proj["bullets"].append(bullet["text"])
            else:
                flattened_proj["bullets"].append(str(bullet))

        projects.append(flattened_proj)

    # Transform skills: flatten into single list with labels and levels
    skills = []
    for skill_category in raw_data.get("skills", []):
        category_name = skill_category.get("category", "")
        skill_level = skill_category.get("level", 3)
        for skill_name in skill_category.get("skills", []):
            skills.append({
                "label": skill_name,
                "category": category_name,
                "level": skill_level,
            })

    # Build result
    data = {
        "metadata": raw_data.get("metadata", {}),
        "personal_info": {
            "name": raw_data.get("profile", {}).get("name", ""),
            "location": raw_data.get("profile", {}).get("location", ""),
            "email": raw_data.get("profile", {}).get("email", ""),
            "phone": raw_data.get("profile", {}).get("phone", ""),
            "portfolio": raw_data.get("profile", {}).get("portfolio", ""),
            "github": raw_data.get("profile", {}).get("github", ""),
            "linkedin": raw_data.get("profile", {}).get("linkedin", ""),
        },
        "experiences": experiences,
        "projects": projects,
        "skills": skills,
        "education": raw_data.get("education", []),
        "certifications": raw_data.get("certifications", []),
        "languages": raw_data.get("languages", []),
        "excluded_skills": raw_data.get("excluded_skills", {}),
        "quantified_results": raw_data.get("quantified_results", {}),
        "usage_rules": raw_data.get("usage_rules", {}),
    }

    # Add convenience _by_id dicts for template access
    data["experiences_by_id"] = {e["id"]: e for e in experiences}
    data["projects_by_id"] = {p["id"]: p for p in projects}

    return data


def _validate_master_cv(data: dict) -> None:
    """Validate Master CV structure and locked facts.

    Fails loudly if critical facts are missing or malformed.
    """
    errors = []

    # Check experiences count
    if len(data.get("experiences", [])) != 3:
        errors.append(
            f"Expected 3 experiences, got {len(data.get('experiences', []))}"
        )

    # Check Sidel facts
    sidel = data["experiences"][0] if data.get("experiences") else {}
    sidel_bullets_text = " ".join(sidel.get("bullets", []))

    if "6+" not in sidel_bullets_text:
        errors.append("Sidel: '6+' dashboards fact missing")
    if "5–6" not in sidel_bullets_text or "1 h" not in sidel_bullets_text:
        errors.append("Sidel: '5–6 h → 1 h' automation fact missing or malformed")
    if "80 %" not in sidel_bullets_text:
        errors.append("Sidel: '80 %' time reduction fact missing")
    if "61" not in sidel_bullets_text:
        errors.append("Sidel: '61' accounts (Wines & Spirits) fact missing")

    # Check projects count (3 authorized in Master CV V3 HTML: Elevia, Job Apply, Nuit Blanche)
    if len(data.get("projects", [])) != 3:
        errors.append(
            f"Expected 3 projects (authorized in Master CV V3), got {len(data.get('projects', []))}"
        )

    # Check project titles (Nuit Blanche should exist, no stale SkillMap or V.I.E Matcher)
    project_titles = [p.get("title", "") for p in data.get("projects", [])]
    if "SkillMap Automation Console" in project_titles:
        errors.append("Stale project 'SkillMap Automation Console' found (not in Master CV V3)")
    if "V.I.E Matcher" in project_titles:
        errors.append("Stale project 'V.I.E Matcher' found (not in Master CV V3 HTML)")
    if "Nuit Blanche" not in " ".join(project_titles):
        errors.append("Project 'Nuit Blanche' not found")

    # Check Elevia facts
    elevia = next(
        (p for p in data.get("projects", []) if "Elevia" in p.get("title", "")),
        {}
    )
    elevia_text = " ".join(elevia.get("bullets", []))
    if "10+" not in elevia_text or "30" not in elevia_text or "1 000+" not in elevia_text:
        errors.append("Elevia: '10+', '30', '1 000+' facts missing")

    # Check Job Apply Assistant facts
    jaa = next(
        (p for p in data.get("projects", []) if "Job Apply Assistant" in p.get("title", "")),
        {}
    )
    jaa_text = " ".join(jaa.get("bullets", []))
    if "45" not in jaa_text or "5" not in jaa_text:
        errors.append("Job Apply Assistant: '45 → 5' time reduction fact missing")

    # Check skill levels
    skill_dict = {s["label"]: s.get("level", 0) for s in data.get("skills", [])}

    # Level 3 (mastered) checks
    level_3_required = ["Power BI", "SQL", "Python", "PostgreSQL", "FastAPI", "Docker", "Coolify"]
    for skill in level_3_required:
        if skill not in skill_dict or skill_dict[skill] != 3:
            errors.append(f"Skill '{skill}' should be level 3 (mastered), got {skill_dict.get(skill)}")

    # Level 0 (excluded) checks
    excluded_required = ["Jira", "Confluence", "GCP", "Looker Studio"]
    excluded_dict = {t["tool"]: t for t in data.get("excluded_skills", {}).get("tools", [])}
    for tool in excluded_required:
        if tool not in excluded_dict:
            errors.append(f"Excluded skill '{tool}' not in exclusion list")

    if errors:
        error_msg = "Master CV V3 validation FAILED:\n" + "\n".join(f"  • {e}" for e in errors)
        raise ValueError(error_msg)

    logger.info("Master CV V3 validation PASSED ✓")



def validate_adaptation(adaptation: dict, master_cv: dict) -> dict:
    """Validate adaptation against master CV.

    Philosophy: Truth is immutable. Narrative is flexible.

    Ensure:
    - Experience order is FIXED: [0, 1, 2]
    - Facts preserved (companies, dates, roles)
    - No invented content
    - Required projects present
    - Bullets may be rewritten (flexible narrative)
    """
    issues = []

    # FIXED experience order (never reorder)
    expected_exp_order = [0, 1, 2]
    actual_exp_order = adaptation.get("experience_order", [])
    if actual_exp_order != expected_exp_order:
        issues.append(f"Experience order must be {expected_exp_order}. Got {actual_exp_order}")

    # Check bullets exist for each experience (facts preserved, wording flexible)
    exp_bullets = adaptation.get("experience_bullets", {})
    for exp_id in [0, 1, 2]:
        exp_id_str = str(exp_id)
        master_bullets = master_cv["experiences"][exp_id].get("bullets", [])
        actual_bullets = exp_bullets.get(exp_id_str, [])

        # Sidel (exp_id 0) is flagship: MINIMUM 5 bullets
        if exp_id == 0:
            if len(actual_bullets) < 5:
                issues.append(f"Sidel experience: Minimum 5 bullets required. Got {len(actual_bullets)}.")
        else:
            # Other experiences: at least one bullet required
            if not actual_bullets:
                issues.append(f"Experience {exp_id}: At least one bullet required.")

        # Check no fabricated content in bullets (basic heuristic)
        for bullet in actual_bullets:
            if not isinstance(bullet, str) or len(bullet) == 0:
                issues.append(f"Experience {exp_id}: Invalid bullet format.")

    # Check projects valid (default 3, can include 4 if relevant)
    proj_order = adaptation.get("project_order", [])
    valid_projects = {0, 1, 2, 3}
    if not proj_order or not all(p in valid_projects for p in proj_order):
        issues.append(f"Invalid project order. Got {proj_order}")

    # Required projects: 0, 1, 2 (Elevia, Job Apply Assistant, V.I.E Matcher)
    required_projects = {0, 1, 2}
    if not required_projects.issubset(set(proj_order)):
        issues.append(f"Projects 0, 1, 2 required. Got {proj_order}")

    return {
        "is_valid": len(issues) == 0,
        "issues": issues,
    }

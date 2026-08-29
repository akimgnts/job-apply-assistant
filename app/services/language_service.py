"""Language detection and translation for CV generation.

Supports: French (default), English
Principle: Never invent content, only translate already-selected facts.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def detect_job_offer_language(job_offer_text: str, analysis: dict) -> str:
    """Detect job offer language from text or metadata.

    Returns: "fr" or "en"
    Default: "fr" (assume French unless clear English indicators)
    """
    if not job_offer_text:
        return "fr"

    text_lower = job_offer_text.lower()

    # English indicators
    english_words = [
        "english", "fluent", "required", "experience", "responsibilities",
        "qualifications", "about us", "job description", "apply now",
        "years of experience", "bachelor", "master", "degree"
    ]

    # French indicators
    french_words = [
        "français", "anglais", "expérience requise", "missions", "profil",
        "compétences", "qualifications", "candidature", "postuler",
        "années d'expérience", "diplôme", "master", "bac"
    ]

    english_count = sum(1 for word in english_words if word in text_lower)
    french_count = sum(1 for word in french_words if word in text_lower)

    # Also check analysis metadata if available
    if analysis and isinstance(analysis, dict):
        job_title = analysis.get("job_title", "").lower()
        company = analysis.get("company", "").lower()
        missions = " ".join(analysis.get("missions", [])).lower()

        text_check = job_title + company + missions
        english_count += sum(1 for word in ["engineer", "developer", "lead", "senior"] if word in text_check)
        french_count += sum(1 for word in ["ingénieur", "développeur", "chef", "senior"] if word in text_check)

    # Decide language
    if english_count > french_count:
        logger.info("Language detected: ENGLISH")
        return "en"
    else:
        logger.info("Language detected: FRENCH (default)")
        return "fr"


def translate_bullet_to_english(french_bullet: str) -> str:
    """Translate a French bullet point to English.

    Rules:
    - Preserve all numbers exactly
    - Preserve dates, companies, technologies exactly
    - Preserve metrics and quantitative claims exactly
    - Only translate the narrative/descriptive text
    - Never strengthen claims or add new information

    Uses simple pattern-based translation for reliability.
    Falls back to original if translation unclear.
    """
    if not french_bullet:
        return french_bullet

    # Numbers and metrics (preserve exactly)
    import re

    # Mapping of common French phrases to English
    # IMPORTANT: Only translate descriptions, never quantitative content
    translation_map = {
        # Verbs
        "Conception et déploiement": "Designed and deployed",
        "Conception": "Design",
        "Développement": "Development",
        "Automatisation": "Automation",
        "Analyse": "Analysis",
        "Consolidation": "Consolidation",
        "Construction": "Building",
        "Modélisation": "Modeling",
        "Exploration": "Exploration",
        "Exploitation": "Leveraging",
        "Transformation": "Transformation",
        "Orchestration": "Orchestration",
        "Intégration": "Integration",
        "Normalisation": "Normalization",
        "Mise en place": "Implementation",
        "Coordination": "Coordination",
        "Préparation": "Preparation",
        "Recueil": "Collection",
        "Réalisation": "Execution",
        "Collaboration": "Collaboration",
        "Fonctionnement": "Operation",
        "Production": "Production",
        "Contribution": "Contribution",

        # Common phrases
        "chaque semaine": "each week",
        "chaque mois": "each month",
        "par": "by",
        "à partir de": "from",
        "selon": "by",
        "afin de": "to",
        "pour": "for",
        "en croisant": "by crossing",
        "en autonomie": "independently",
        "en mode": "in",
        "avant": "before",
        "après": "after",
        "en amont": "upstream",
        "en parallèle": "in parallel",

        # Skills/concepts (preserve some, translate descriptions)
        "équipes": "teams",
        "collaborateurs": "collaborators",
        "managers": "managers",
        "fonctions": "functions",
        "métier": "business",
        "besoin": "need",
        "besoins": "needs",
        "données": "data",
        "qualité": "quality",
        "performance": "performance",
        "risques": "risks",
        "opportunités": "opportunities",
        "priorités": "priorities",
        "solutions": "solutions",
        "flux": "flows",
        "processus": "processes",
        "workflows": "workflows",  # Usually keep English
        "dashboards": "dashboards",  # Usually keep English
        "reporting": "reporting",  # Usually keep English
        "KPI": "KPI",  # Acronym - keep
        "CRM": "CRM",  # Acronym - keep
    }

    result = french_bullet

    # Apply translations (case-insensitive for common phrases)
    for french, english in translation_map.items():
        # Case-insensitive replacement
        result = re.sub(
            re.escape(french),
            english,
            result,
            flags=re.IGNORECASE
        )

    logger.debug(f"TRANSLATE: '{french_bullet[:50]}...' -> '{result[:50]}...'")
    return result


def translate_label_to_language(label: str, language: str) -> str:
    """Translate UI labels (section titles, etc.) to target language.

    Only translates standard labels, not content.
    """
    if language == "fr":
        return label  # Already in French

    if language != "en":
        return label  # Unknown language, return original

    # French to English label translations
    label_map = {
        "EXPÉRIENCE": "EXPERIENCE",
        "Expérience": "Experience",
        "PROJETS": "PROJECTS",
        "Projets": "Projects",
        "COMPÉTENCES": "SKILLS",
        "Compétences": "Skills",
        "FORMATION": "EDUCATION",
        "Formation": "Education",
        "CERTIFICATIONS": "CERTIFICATIONS",
        "LANGUES": "LANGUAGES",
        "Langues": "Languages",
        "DISPONIBILITÉ": "AVAILABILITY",
        "Disponibilité": "Availability",
        "RÉSUMÉ": "SUMMARY",
        "Résumé": "Summary",
        "Data & BI": "Data & BI",
        "Automation & Backend": "Automation & Backend",
        "AI & LLM": "AI & LLM",
        "Project & Business": "Project & Business",
    }

    return label_map.get(label, label)


def get_translated_section_titles(language: str) -> dict:
    """Get translated section titles for CV template."""
    if language == "en":
        return {
            "experience": "EXPERIENCE",
            "projects": "PROJECTS",
            "skills": "SKILLS",
            "education": "EDUCATION",
            "certifications": "CERTIFICATIONS",
            "languages": "LANGUAGES",
            "summary": "SUMMARY",
        }
    else:  # French (default)
        return {
            "experience": "EXPÉRIENCE",
            "projects": "PROJETS",
            "skills": "COMPÉTENCES",
            "education": "FORMATION",
            "certifications": "CERTIFICATIONS",
            "languages": "LANGUES",
            "summary": "RÉSUMÉ PROFESSIONNEL",
        }

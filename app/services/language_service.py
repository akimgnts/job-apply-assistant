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

    Pipeline:
    1. Extract protected invariants (numbers, dates, techs, companies)
    2. Translate narrative text only using phrase-based mapping
    3. Validate that all invariants are preserved exactly
    4. Reject translation if any invariant is missing/modified

    Rules:
    - Preserve all numbers exactly (6+, 61, 80%, 5–6 h/semaine)
    - Preserve all dates, companies, technologies, metrics exactly
    - Only translate descriptive/narrative text
    - Never strengthen claims or add new information
    - Return original if translation validation fails

    Uses controlled translation service with invariant validation.
    """
    if not french_bullet:
        return french_bullet

    from app.services.translation_service import translate_bullet_to_english_v2

    result = translate_bullet_to_english_v2(french_bullet)
    logger.debug(f"TRANSLATE: '{french_bullet[:50]}...' → '{result[:50]}...'")
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

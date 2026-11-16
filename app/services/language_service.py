"""Language detection and translation for CV generation.

Supports: French (default), English
Principle: Never invent content, only translate already-selected facts.
"""

import logging
import re
import unicodedata
from typing import Optional

logger = logging.getLogger(__name__)


def detect_job_offer_language(job_offer_text: str, analysis: dict) -> str:
    """Detect job offer language from text or metadata.

    Returns: "fr" or "en"
    Default: "fr" (assume French unless clear English indicators)
    """
    source_text = job_offer_text or ""
    if not source_text and isinstance(analysis, dict):
        missions = analysis.get("missions") or []
        source_text = " ".join(str(item) for item in missions)
    normalized = unicodedata.normalize("NFKD", source_text.lower())
    text = "".join(char for char in normalized if not unicodedata.combining(char))
    tokens = re.findall(r"[a-z]+", text)
    english_markers = {
        "the", "and", "with", "you", "your", "will", "within", "from", "our",
        "who", "this", "team", "role", "responsibilities", "qualifications", "degree",
        "skills", "apply", "support", "based", "looking", "join", "provide", "develop",
        "manage", "ensure", "reporting", "experience", "required", "bachelor",
    }
    french_markers = {
        "nous", "vous", "pour", "dans", "avec", "au", "aux", "de", "des", "les",
        "une", "un", "est", "sont", "vos", "votre", "missions", "profil", "competences",
        "formation", "poste", "entreprise", "recherche", "recherchons", "participer",
        "assurer", "contribuer", "mettre", "place", "accompagner", "afin", "ainsi",
        "plusieurs", "charge", "travail", "equipe", "offre", "candidature", "postuler",
    }
    english_count = sum(token in english_markers for token in tokens)
    french_count = sum(token in french_markers for token in tokens)

    # Require a clear textual signal. Titles, company names and technical skills
    # (e.g. "Data Engineer", "Data Quality") are not language evidence.
    if english_count >= french_count + 2:
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


"""Controlled translation with invariant preservation and validation.

Pipeline:
1. Extract and protect all invariants (numbers, dates, technologies, companies)
2. Translate narrative text only
3. Validate that all invariants are present and unchanged in translated text
4. Reject translation if any invariant is missing or modified
"""

import re
import logging
from typing import Dict, List, Tuple, Optional

logger = logging.getLogger(__name__)


class InvariantExtractor:
    """Extract and protect quantitative facts from French bullets."""

    # Patterns for protected invariants
    PATTERNS = {
        "numbers": r'(?:\d+\+|\d+(?:[,.]?\d+)*)',  # 6+, 6, 61, 1.5
        "percentages": r'\d+\s*%',  # 80%, 50 %
        "dates": r'\d{1,2}\s*[–—-]\s*\d{1,2}',  # 5–6, 2-3, date ranges
        "times": r'\d+\s*h(?:/\w+)?',  # 5 h, 5 h/semaine
        "technologies": r'\b(?:Power\s+BI|SQL|Python|PostgreSQL|FastAPI|Docker|n8n|Make|Coolify|LangChain|OpenAI|GPT|DAX|Excel|REST|APIs?|JSON|YAML|CI/CD|AWS|GCP|Azure|Kubernetes|Terraform)\b',
        "company_names": r'\b(?:Sidel|MadeByAkim|Vassard|Elevia|Orange|Google|Microsoft|Amazon)\b',  # Explicit company list
        "project_status": r'\b(?:en\s+production|in\s+production|en\s+cours|in\s+progress|déployé|deployed|live|beta)\b',
    }

    @classmethod
    def extract_invariants(cls, text: str) -> Dict[str, List[str]]:
        """Extract all protected invariants from text."""
        invariants = {}
        for category, pattern in cls.PATTERNS.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                invariants[category] = matches
        return invariants

    @classmethod
    def validate_invariants_preserved(
        cls,
        original_text: str,
        translated_text: str,
    ) -> Tuple[bool, List[str]]:
        """Validate that all invariants from original are present in translation.

        Returns:
            (is_valid, list_of_missing_invariants)
        """
        original_invariants = cls.extract_invariants(original_text)
        translated_invariants = cls.extract_invariants(translated_text)

        missing = []

        for category, original_values in original_invariants.items():
            translated_values = translated_invariants.get(category, [])

            for value in original_values:
                # Numbers/percentages/times must be exact
                if category in ["numbers", "percentages", "times", "dates"]:
                    if value not in translated_values:
                        missing.append(f"{category}: '{value}' missing")
                # Technologies/companies must be present (case-insensitive for some)
                elif category in ["technologies", "company_names"]:
                    found = any(v.lower() == value.lower() for v in translated_values)
                    if not found:
                        missing.append(f"{category}: '{value}' missing")

        return len(missing) == 0, missing


class ControlledTranslator:
    """Translate French to English while preserving all invariants."""

    # Structured translation mappings (phrases, not single words)
    PHRASE_TRANSLATIONS = {
        # Action verbs (descriptive, can be translated)
        "Conception et déploiement": "Designed and deployed",
        "Conception de": "Design of",
        "Conception": "Design",
        "Développement": "Development",
        "Automatisation": "Automation",
        "Automatisation d'": "Automation of",
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
        "Mise en œuvre": "Implementation",
        "Coordination": "Coordination",
        "Préparation": "Preparation",
        "Recueil": "Collection",
        "Réalisation": "Execution",
        "Collaboration": "Collaboration",
        "Fonctionnement": "Operation",
        "Production": "Production",
        "Contribution": "Contribution",

        # Common prepositions/connectors (change narrative, not facts)
        "chaque semaine": "each week",
        "chaque mois": "each month",
        "chaque jour": "each day",
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
        "en production": "in production",
        "en cours": "in progress",

        # Business concepts (translation acceptable)
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

        # Units/metrics (preserve exact value, translate label only)
        "heure": "hour",
        "heures": "hours",
        "semaine": "week",
        "semaines": "weeks",
        "mois": "month",
        "mois": "months",
        "jour": "day",
        "jours": "days",
        "réduction": "reduction",
        "augmentation": "increase",
    }

    @classmethod
    def translate_bullet(cls, french_bullet: str) -> str:
        """Translate French bullet to English while preserving invariants.

        Process:
        1. Extract and protect all invariants
        2. Apply phrase-based translation
        3. Validate invariants still present
        4. Return translation or original if validation fails
        """
        if not french_bullet:
            return french_bullet

        # Step 1: Extract invariants
        extractor = InvariantExtractor()
        invariants = extractor.extract_invariants(french_bullet)

        # Step 2: Translate using phrase mappings (case-insensitive)
        translated = french_bullet
        for french_phrase, english_phrase in cls.PHRASE_TRANSLATIONS.items():
            # Replace with word boundaries where possible
            pattern = r'\b' + re.escape(french_phrase) + r'\b'
            translated = re.sub(
                pattern,
                english_phrase,
                translated,
                flags=re.IGNORECASE,
                count=1
            )

        # Step 3: Validate all invariants preserved
        is_valid, missing = extractor.validate_invariants_preserved(
            french_bullet, translated
        )

        if not is_valid:
            logger.warning(
                f"TRANSLATION VALIDATION FAILED: {missing}\n"
                f"  Original: {french_bullet[:80]}\n"
                f"  Translated: {translated[:80]}"
            )
            # Reject translation if critical facts are lost
            return french_bullet

        logger.debug(
            f"TRANSLATION OK: '{french_bullet[:60]}...' → '{translated[:60]}...'"
        )
        return translated


def translate_bullet_to_english_v2(french_bullet: str) -> str:
    """Translate French bullet to English with invariant validation.

    Uses ControlledTranslator with full validation pipeline.
    Returns original if translation fails validation.
    """
    return ControlledTranslator.translate_bullet(french_bullet)


def validate_translation_quality(
    original: str,
    translated: str,
) -> Dict:
    """Validate translation quality (invariant preservation + language check).

    Returns:
        {
          "is_valid": bool,
          "french_remaining": bool (are there French words?),
          "missing_invariants": list,
          "quality_score": 0-100,
        }
    """
    extractor = InvariantExtractor()
    is_valid, missing = extractor.validate_invariants_preserved(original, translated)

    # Check for remaining French words (simple heuristic)
    french_words = ["et", "de", "d'", "la", "le", "en", "pour", "avec", "dans"]
    translated_lower = translated.lower()
    french_remaining = sum(
        1 for word in french_words
        if re.search(r'\b' + word + r'\b', translated_lower)
    ) > 3  # More than 3 French words left = problem

    quality_score = 100
    if missing:
        quality_score -= len(missing) * 20
    if french_remaining:
        quality_score -= 30

    return {
        "is_valid": is_valid and not french_remaining,
        "french_remaining": french_remaining,
        "missing_invariants": missing,
        "quality_score": max(0, quality_score),
    }

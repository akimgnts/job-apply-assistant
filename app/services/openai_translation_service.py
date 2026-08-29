"""OpenAI-powered translation with deterministic invariant validation.

Pipeline:
1. Send French Master CV bullet to OpenAI with translation prompt
2. Prompt explicitly forbids adding facts, technologies, scope changes
3. OpenAI returns English translation
4. Deterministic validation ensures ALL protected invariants preserved
5. Accept translation or FAIL the document (never return mixed FR/EN)

If translation fails: document generation FAILS for English CV.
No fallback to French text (which would corrupt bilingual output).
"""

import logging
from typing import Optional, Tuple, List

logger = logging.getLogger(__name__)


TRANSLATION_PROMPT_TEMPLATE = """Translate this French professional bullet point to natural English.

CRITICAL CONSTRAINTS:
- Translate ONLY the language, not the content
- NEVER add facts, technologies, or scope
- NEVER change metrics, numbers, or project status
- NEVER strengthen seniority or expertise claims
- NEVER add business domain vocabulary
- NEVER change time measurements

Protected facts (must remain IDENTICAL):
- Numbers: 6, 6+, 61, 1.5, etc.
- Percentages: 80%, 50%, etc.
- Times: 5–6 h/semaine, 1 h/semaine, etc.
- Technologies: Power BI, SQL, Python, PostgreSQL, FastAPI, Docker, etc.
- Company names: Sidel, MadeByAkim, Vassard, Elevia, etc.
- Project names: Job Apply Assistant, Nuit Blanche, etc.
- Project status: en production, in progress, etc.
- Business units: comptes, clients, collaborators, teams, etc.

Acceptable changes:
- Grammar and natural word order
- Professional English phrasing
- Removing French articles (le, la, un, une)
- Active/passive voice if meaning unchanged

FRENCH BULLET:
{french_bullet}

ENGLISH TRANSLATION (natural professional English, facts unchanged):"""


async def translate_with_openai(
    french_bullet: str,
    openai_service,
) -> Optional[str]:
    """Translate French bullet to English using OpenAI.

    Args:
        french_bullet: Master CV French bullet
        openai_service: OpenAI service client (with API key)

    Returns:
        English translation, or None if translation unavailable
    """
    if not french_bullet:
        return None

    prompt = TRANSLATION_PROMPT_TEMPLATE.format(french_bullet=french_bullet)

    try:
        # Use OpenAI text generation (not JSON mode, we want natural output)
        from app.services.openai_service import generate_text

        english_bullet = await generate_text(prompt)
        logger.debug(f"TRANSLATE: OpenAI translation complete")
        return english_bullet

    except Exception as e:
        logger.error(f"TRANSLATE: OpenAI failed: {e}")
        return None


def validate_translation_acceptable(
    original_fr: str,
    translated_en: str,
) -> Tuple[bool, List[str]]:
    """Validate that translation preserves all protected facts.

    Returns:
        (is_acceptable, list_of_issues)
    """
    from app.services.translation_service import InvariantExtractor

    extractor = InvariantExtractor()
    is_valid, missing = extractor.validate_invariants_preserved(
        original_fr, translated_en
    )

    if not is_valid:
        return False, missing

    # Additional check: no excessive French remnants
    french_words = ["et", "de", "d'", "la", "le", "en", "pour", "avec", "dans", "à"]
    import re
    french_count = sum(
        1 for word in french_words
        if re.search(r'\b' + word + r'\b', translated_en.lower())
    )

    if french_count > 3:
        return False, [f"Too many French words remain ({french_count})"]

    return True, []


async def translate_bullet_with_retry(
    french_bullet: str,
    openai_service,
    max_retries: int = 1,
) -> Optional[str]:
    """Translate bullet with retry if validation fails.

    Returns:
        English translation (validated), or None if all attempts fail
    """
    for attempt in range(max_retries + 1):
        # Get translation from OpenAI
        english = await translate_with_openai(french_bullet, openai_service)

        if not english:
            logger.warning(f"TRANSLATE attempt {attempt + 1}: OpenAI unavailable")
            continue

        # Validate
        is_valid, issues = validate_translation_acceptable(french_bullet, english)

        if is_valid:
            logger.info(f"TRANSLATE: Valid translation on attempt {attempt + 1}")
            return english
        else:
            logger.warning(
                f"TRANSLATE attempt {attempt + 1} failed: {issues}\n"
                f"  Original: {french_bullet[:60]}...\n"
                f"  Translated: {english[:60]}..."
            )

            if attempt < max_retries:
                # Could retry with feedback to OpenAI here
                continue
            else:
                # All retries exhausted
                return None

    return None

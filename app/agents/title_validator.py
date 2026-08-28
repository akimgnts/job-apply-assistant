"""Title validation for CV generation.

Ensures public CV titles are factually supported and don't introduce
unsupported domains, seniority levels, or specializations.

Philosophy:
- Titles must be consistent with verified positioning + Master CV
- No unsupported domain specialization (e.g., "Supply Chain Specialist")
- No unsupported seniority (e.g., "Senior", "Lead")
- Deterministic allowlist-first approach
"""

import logging
from typing import Tuple, Set

logger = logging.getLogger(__name__)

# SAFE: Supported title components (from Master CV + safe generics)
SAFE_TITLE_TOKENS: Set[str] = {
    # Generic role families
    "analyst",
    "data analyst",
    "business analyst",
    "data & ai analyst",
    "data & business analyst",
    "business & data analyst",

    # Skill descriptors (safe)
    "data",
    "analytics",
    "business",
    "intelligence",
    "automation",
    "automation specialist",

    # Industry/domain descriptors (safe from Master CV)
    "industrial",
    "b2b",
    "marketing",
    "communication",
    "reporting",
    "operations",
    "operational",

    # Modifiers (safe)
    "junior",  # Explicit seniority is OK if honest
    "entry-level",
    "internship",

    # Separators
    "|",
    "–",
    "—",
    "&",
    "and",
}

# UNSAFE: Forbidden title components (unsupported domains, seniority)
UNSAFE_TITLE_TOKENS: Set[str] = {
    # Unsupported specializations
    "supply chain",
    "supply-chain",
    "aps",
    "advanced planning",
    "scheduling",
    "planning & scheduling",
    "production planning",
    "ordonnancement",

    # Unsupported seniority (unless explicitly justified)
    "senior",
    "lead",
    "principal",
    "staff",
    "distinguished",
    "director",
    "manager",
    "head of",

    # Unsupported roles
    "engineer",
    "architect",
    "specialist",  # Too vague and implies deep expertise
    "expert",
    "consultant",

    # Unsupported domains (user has no experience)
    "machine learning",
    "ml",
    "ai engineer",
    "cloud engineer",
    "devops",
    "infrastructure",
    "backend engineer",
    "frontend engineer",
    "full stack",
    "software engineer",
    "data engineer",
}

# Safe title mappings from internal positioning to candidate-facing titles
POSITIONING_TO_SAFE_TITLE = {
    "Data Analyst BI": "Data Analyst | Business Intelligence",
    "Marketing Data Analyst": "Data Analyst | Marketing & Analytics",
    "Data Steward / Data Quality": "Data Analyst | Data Quality & Governance",
    "Business Analyst orienté data": "Business & Data Analyst",
    "Data & AI Consultant": "Data Analyst | AI & Automation",
    "Product / Ops Analyst": "Data Analyst | Operations & Analytics",
    "Business Intelligence Analyst": "Data Analyst | Business Intelligence",
}

# Fallback title if validation fails
FALLBACK_TITLE = "Data Analyst | Business Intelligence & Automation"


class TitleValidator:
    """Validate and rewrite CV titles for factual consistency."""

    @staticmethod
    def validate_title(title: str, positioning: str = None) -> Tuple[bool, str]:
        """Validate a generated title.

        Args:
            title: Generated title from CVAdaptationAgent
            positioning: Internal positioning angle (from PositioningAgent)

        Returns:
            (is_valid, rewritten_title_if_invalid)
            - is_valid=True: title is factually supported, use as-is
            - is_valid=False: title needs rewrite, use rewritten_title
        """
        if not title or not isinstance(title, str):
            logger.warning(f"Invalid title type: {type(title)}")
            return (False, FALLBACK_TITLE)

        title_clean = title.strip().lower()

        # Check for forbidden tokens
        for unsafe_token in UNSAFE_TITLE_TOKENS:
            if unsafe_token.lower() in title_clean:
                logger.warning(
                    f"Title contains unsafe token '{unsafe_token}': {title}"
                )
                rewritten = TitleValidator._rewrite_title(title, positioning)
                return (False, rewritten)

        # Check if title has at least one safe component
        has_safe_component = any(
            safe_token.lower() in title_clean for safe_token in SAFE_TITLE_TOKENS
        )

        if not has_safe_component:
            logger.warning(f"Title has no safe components: {title}")
            rewritten = TitleValidator._rewrite_title(title, positioning)
            return (False, rewritten)

        # Additional check: title should not be longer than typical roles
        # (rules out overly complex or fabricated titles)
        if len(title) > 80:
            logger.warning(f"Title too long (>80 chars): {title}")
            rewritten = TitleValidator._rewrite_title(title, positioning)
            return (False, rewritten)

        logger.info(f"Title validation passed: {title}")
        return (True, title)

    @staticmethod
    def _rewrite_title(original: str, positioning: str = None) -> str:
        """Rewrite unsupported title to safe fallback.

        Strategy:
        1. If positioning provided, use mapping to safe title
        2. Otherwise use generic fallback
        """
        if positioning and positioning in POSITIONING_TO_SAFE_TITLE:
            safe_title = POSITIONING_TO_SAFE_TITLE[positioning]
            logger.info(
                f"Rewrote title '{original}' to safe mapping: {safe_title}"
            )
            return safe_title

        logger.info(f"Rewrote title '{original}' to fallback: {FALLBACK_TITLE}")
        return FALLBACK_TITLE

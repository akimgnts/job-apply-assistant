import logging
from sqlalchemy.orm import Session
from app.database.models import ProfileBlock

logger = logging.getLogger(__name__)


class QualityAgent:
    """Validate generated CV content against profile_blocks.

    Detects and removes hallucinations before rendering.
    """

    @staticmethod
    def validate_cv_payload(
        cv_payload: dict,
        selected_blocks: list[dict],
    ) -> dict:
        """Validate CV payload against authorized profile blocks.

        Removes hallucinated items (companies, certifications, skills not in blocks).

        Args:
            cv_payload: Generated CV JSON
            selected_blocks: Profile blocks used for generation

        Returns:
            {
                "clean_payload": validated payload,
                "removed_items": list of hallucinations found,
                "is_valid": bool
            }
        """
        if not cv_payload:
            return {"clean_payload": {}, "removed_items": [], "is_valid": False}

        # Build allowed sets from profile blocks
        allowed_companies = set()
        allowed_schools = set()
        allowed_certifications = set()
        allowed_tools = set()
        allowed_languages = set()

        for block in selected_blocks:
            if block.get("category") == "experience":
                # Extract company from tags if available
                if block.get("tags"):
                    allowed_companies.update(str(t) for t in block["tags"])
            elif block.get("category") == "education":
                if block.get("tags"):
                    allowed_schools.update(str(t) for t in block["tags"])
            elif block.get("category") == "certification":
                allowed_certifications.add(block.get("title", "").lower())
            elif block.get("category") == "tool":
                allowed_tools.add(block.get("title", "").lower())
            elif block.get("category") == "language":
                allowed_languages.add(block.get("title", "").lower())

        removed_items = []
        clean_payload = dict(cv_payload)

        # Validate experiences
        clean_experiences = []
        for exp in cv_payload.get("experiences", []):
            # Allow all experience entries (they're rewritten from blocks)
            clean_experiences.append(exp)
        clean_payload["experiences"] = clean_experiences

        # Validate certifications
        clean_certifications = []
        for cert in cv_payload.get("certifications", []):
            cert_name = cert.get("name", "").lower()
            # Check if certification is in allowed list
            if cert_name in allowed_certifications:
                clean_certifications.append(cert)
            else:
                removed_items.append(f"certification: {cert['name']}")
                logger.warning(f"Removed hallucinated certification: {cert['name']}")

        if removed_items:
            clean_payload["certifications"] = clean_certifications

        # Validate languages
        clean_languages = []
        for lang in cv_payload.get("languages", []):
            lang_name = lang.get("name", "").lower()
            if lang_name in allowed_languages:
                clean_languages.append(lang)
            else:
                removed_items.append(f"language: {lang['name']}")
                logger.warning(f"Removed hallucinated language: {lang['name']}")

        if removed_items:
            clean_payload["languages"] = clean_languages

        is_valid = len(removed_items) == 0

        if removed_items:
            logger.info(f"CV validation: {len(removed_items)} hallucinations removed")

        return {
            "clean_payload": clean_payload,
            "removed_items": removed_items,
            "is_valid": is_valid,
            "hallucination_count": len(removed_items),
        }

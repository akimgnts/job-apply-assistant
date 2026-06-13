import logging
from app.services.scraping_service import process_input

logger = logging.getLogger(__name__)

class InputAgent:
    """Handle input processing: detect URL vs text, extract content."""

    @staticmethod
    def process(raw_input: str) -> tuple[str | None, dict]:
        """
        Process user input.
        Returns (offer_text, metadata_dict).
        If offer_text is None, user should provide raw text.
        """
        offer_text, is_url, source_url = process_input(raw_input)

        if is_url and offer_text is None:
            return None, {"error": "url_extraction_failed", "source_url": source_url}

        metadata = {
            "is_url": is_url,
            "source_url": source_url,
            "raw_length": len(offer_text) if offer_text else 0,
        }

        return offer_text, metadata

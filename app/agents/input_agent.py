import logging
from app.services.job_ingestion_service import ingest_job_input, is_url

logger = logging.getLogger(__name__)

class InputAgent:
    """Handle input processing: detect URL vs text, extract content."""

    @staticmethod
    async def process(raw_input: str) -> tuple[str | None, dict]:
        """
        Process user input via JobIngestionService.

        Returns (offer_text, metadata_dict).
        If offer_text is None, user should provide raw text.
        """
        # Use JobIngestionService to ingest input
        result = await ingest_job_input(raw_input)

        source_type = result["source_type"]
        source_url = result["source_url"]
        extraction_success = result["extraction_success"]
        clean_text = result["clean_text"]
        error = result["error"]

        # If URL extraction failed, tell user to paste text
        if source_type == "url" and not extraction_success:
            return None, {
                "error": "url_extraction_failed",
                "source_url": source_url,
                "error_detail": error,
            }

        metadata = {
            "source_type": source_type,
            "source_url": source_url,
            "extraction_success": extraction_success,
            "text_length": len(clean_text) if clean_text else 0,
        }

        return clean_text, metadata

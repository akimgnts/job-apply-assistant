import logging
import re
from urllib.parse import urlparse
import trafilatura

logger = logging.getLogger(__name__)


def is_url(text: str) -> bool:
    """Check if text is a URL."""
    try:
        result = urlparse(text.strip())
        return all([result.scheme in ('http', 'https'), result.netloc])
    except Exception:
        return False


def clean_job_text(text: str) -> str:
    """Clean extracted job text by removing noise and normalizing spaces."""
    if not text:
        return ""

    text = text.strip()

    # Remove cookie/footer sections
    text = re.sub(r'(?i)(cookie|accept all|decline|preferences|privacy policy).*?(?=\n\n|\Z)', '', text)

    # Remove navigation/menu sections
    text = re.sub(r'(?i)(menu|navigation|skip to|home|about|contact).*?(?=\n\n|\Z)', '', text)

    # Remove social share sections
    text = re.sub(r'(?i)(share on|follow us|social media|linkedin|facebook|twitter).*?(?=\n\n|\Z)', '', text)

    # Remove legal boilerplate
    text = re.sub(r'(?i)(copyright|all rights reserved|terms of service|disclaimer).*?(?=\n\n|\Z)', '', text)

    # Remove multiple consecutive spaces/newlines
    text = re.sub(r' +', ' ', text)
    text = re.sub(r'\n\n+', '\n\n', text)

    # Clean up whitespace
    text = text.strip()

    return text


async def ingest_job_input(raw_input: str) -> dict:
    """
    Ingest job input: either plain text or URL.

    If URL: extract content using trafilatura
    If text: return as-is

    Returns:
    {
        "source_type": "text" | "url",
        "source_url": str or None,
        "extraction_success": bool,
        "clean_text": str,
        "error": str or None
    }
    """
    raw_input = raw_input.strip()

    # Plain text input
    if not is_url(raw_input):
        return {
            "source_type": "text",
            "source_url": None,
            "extraction_success": True,
            "clean_text": raw_input,
            "error": None,
        }

    # URL input
    url = raw_input
    try:
        # Fetch URL
        downloaded = trafilatura.fetch_url(url, timeout=10)
        if not downloaded:
            raise ValueError("Could not fetch URL")

        # Extract text
        extracted = trafilatura.extract(
            downloaded,
            include_comments=False,
            favor_precision=True
        )
        if not extracted:
            raise ValueError("Could not extract text from URL")

        clean_text = clean_job_text(extracted)

        if not clean_text or len(clean_text) < 100:
            raise ValueError("Extracted text too short or empty")

        logger.info(
            f"URL={url} extraction_success=True length={len(clean_text)}"
        )

        return {
            "source_type": "url",
            "source_url": url,
            "extraction_success": True,
            "clean_text": clean_text,
            "error": None,
        }

    except Exception as e:
        error_msg = str(e)
        logger.error(f"URL={url} extraction_success=False error={error_msg}")

        return {
            "source_type": "url",
            "source_url": url,
            "extraction_success": False,
            "clean_text": None,
            "error": error_msg,
        }

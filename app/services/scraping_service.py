import logging
import trafilatura
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

def is_url(text: str) -> bool:
    """Check if text is a valid URL."""
    try:
        result = urlparse(text)
        return all([result.scheme, result.netloc])
    except Exception:
        return False

def extract_from_url(url: str) -> str:
    """Extract text content from URL using trafilatura."""
    try:
        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            logger.warning(f"Could not fetch URL: {url}")
            return ""

        extracted = trafilatura.extract(downloaded, include_comments=False, favor_precision=True)
        if not extracted:
            logger.warning(f"Could not extract text from URL: {url}")
            return ""

        return extracted.strip()
    except Exception as e:
        logger.error(f"Error extracting from URL {url}: {e}")
        return ""

def process_input(raw_input: str) -> tuple[str, bool, str | None]:
    """
    Process user input and return (offer_text, is_url, source_url).
    Returns None for source_url if it's plain text.
    """
    raw_input = raw_input.strip()

    if is_url(raw_input):
        extracted = extract_from_url(raw_input)
        if len(extracted) > 800:
            return extracted, True, raw_input
        else:
            return None, True, raw_input

    return raw_input, False, None

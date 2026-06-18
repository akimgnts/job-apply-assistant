import logging
import re
from urllib.parse import urlparse
import urllib3
import trafilatura

logger = logging.getLogger(__name__)
urllib3.disable_warnings()

_USER_AGENT = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
    'AppleWebKit/537.36 (KHTML, like Gecko) '
    'Chrome/120.0.0.0 Safari/537.36'
)


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

    # Remove cookie/GDPR banners only (standalone lines)
    text = re.sub(r'(?i)^(accept all cookies?|decline cookies?|cookie preferences?|privacy policy)\s*$', '', text, flags=re.MULTILINE)

    # Remove multiple consecutive spaces/newlines
    text = re.sub(r' +', ' ', text)
    text = re.sub(r'\n\n+', '\n\n', text)

    return text.strip()


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
        # Fetch URL with complete User-Agent to avoid bot-detection blocks
        http = urllib3.PoolManager()
        headers = {
            'User-Agent': _USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7',
        }
        response = http.request('GET', url, headers=headers, timeout=15)
        if response.status != 200:
            raise ValueError(f"HTTP {response.status}")

        html = response.data

        # Try precision first, fall back to recall when content is sparse
        extracted = trafilatura.extract(
            html,
            include_comments=False,
            include_tables=True,
            favor_precision=True,
        )
        if not extracted or len(extracted.strip()) < 200:
            extracted = trafilatura.extract(
                html,
                include_comments=False,
                include_tables=True,
                favor_recall=True,
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

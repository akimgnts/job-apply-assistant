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


def _extract_text(html: bytes) -> str:
    """Try trafilatura extraction with precision, then recall fallback."""
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
    return extracted or ""


async def _extract_with_playwright(url: str) -> str:
    """Fallback extraction using a headless browser for JS-rendered pages."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        try:
            page = await browser.new_page()
            await page.set_extra_http_headers({
                "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
            })
            await page.goto(url, wait_until="networkidle", timeout=20000)
            html = await page.content()
        finally:
            await browser.close()

    return _extract_text(html.encode("utf-8"))


async def ingest_job_input(raw_input: str) -> dict:
    """
    Ingest job input: either plain text or URL.

    If URL: extract content using trafilatura, with Playwright fallback for JS sites.
    If text: return as-is.

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
        # Step 1: static fetch
        http = urllib3.PoolManager()
        headers = {
            'User-Agent': _USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7',
        }
        response = http.request('GET', url, headers=headers, timeout=15)
        if response.status != 200:
            raise ValueError(f"HTTP {response.status}")

        extracted = _extract_text(response.data)

        # Step 2: Playwright fallback for JS-rendered pages
        if not extracted or len(extracted.strip()) < 200:
            logger.info(f"URL={url} static extraction sparse, trying Playwright")
            try:
                extracted = await _extract_with_playwright(url)
            except Exception as pw_err:
                logger.warning(f"URL={url} Playwright fallback failed: {pw_err}")

        if not extracted or len(extracted.strip()) < 100:
            raise ValueError("Extracted text too short or empty (site may require login)")

        clean_text = clean_job_text(extracted)

        if not clean_text or len(clean_text) < 100:
            raise ValueError("Extracted text too short or empty")

        logger.info(f"URL={url} extraction_success=True length={len(clean_text)}")

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

"""Job Offer Scraper Service — Phase 2 MVP.

Minimal extraction layer: URL → raw_text + deterministic metadata only.

Does NOT call AnalysisAgent (that's Phase 3).
Does NOT generate missions/skills/analysis (that's Phase 3).

Responsibility: reliable extraction + minimal metadata + DB layer.
"""
import logging
import re
from typing import Optional
from urllib.parse import urlparse
from app.services.scraping_service import extract_from_url

logger = logging.getLogger(__name__)


def infer_source_from_url(url: str) -> str:
    """Infer job board source from URL (deterministic only)."""
    url_lower = url.lower()
    if "indeed" in url_lower:
        return "indeed"
    elif "linkedin" in url_lower:
        return "linkedin"
    elif "glassdoor" in url_lower:
        return "glassdoor"
    elif "monster" in url_lower:
        return "monster"
    else:
        return "website"


def infer_company_name(raw_text: str, url: str) -> Optional[str]:
    """Infer company name conservatively (no hallucination).

    Priority:
    1. Explicit "Company: X" pattern in text
    2. Domain name from URL (if not a job board)
    3. None (rather than guess)
    """
    # Pattern 1: "Company: Name" format
    match = re.search(r"(?:Company|Employer):\s*([A-Za-z\s&]+?)(?:\n|$)", raw_text, re.IGNORECASE)
    if match:
        company = match.group(1).strip()
        if 2 < len(company) < 100:
            return company

    # Pattern 2: Domain from URL (if not a job board)
    source = infer_source_from_url(url)
    if source == "website":
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.replace("www.", "").split(".")[0]
            if domain and len(domain) > 2:
                return domain.capitalize()
        except Exception:
            pass

    # Rather return None than a weak guess
    return None


def extract_job_title_simple(raw_text: str) -> Optional[str]:
    """Extract job title conservatively.

    Looks for explicit patterns only, does not use NLP/ML.
    """
    # Pattern: "Title: X" or "Position: X"
    match = re.search(
        r"(?:Title|Position|Role|Job Title):\s*([^.\n]+)",
        raw_text,
        re.IGNORECASE
    )
    if match:
        title = match.group(1).strip()
        if 3 < len(title) < 100:
            return title

    # Pattern: First h1 or strong tag content (if HTML remnants exist)
    match = re.search(r"^([A-Z][^.\n]{5,80})$", raw_text, re.MULTILINE)
    if match:
        return match.group(1)

    return None


def scrape_job_offer(url: str) -> dict | None:
    """Scrape one job offer URL → minimal JobOffer dict.

    Returns dict ready for DB insertion (or None if extraction fails).
    Does NOT call OpenAI or AnalysisAgent.
    """
    try:
        logger.info(f"Scraping: {url}")

        # Step 1: Extract raw text
        raw_text = extract_from_url(url)
        if not raw_text or len(raw_text) < 100:
            logger.warning(f"Extraction too short for {url}")
            return None

        # Step 2: Deterministic metadata extraction
        job_title = extract_job_title_simple(raw_text)
        if not job_title:
            logger.warning(f"Could not extract job title from {url}")
            job_title = "Unknown Title"

        company_name = infer_company_name(raw_text, url)
        source = infer_source_from_url(url)

        # Step 3: Build minimal JobOffer dict
        job_offer = {
            "job_url": url,
            "company_name": company_name,
            "job_title": job_title,
            "source": source,
            "raw_text": raw_text,
        }

        logger.info(f"✅ Scraped: {job_title} at {company_name or 'Unknown'}")
        return job_offer

    except Exception as e:
        logger.error(f"Failed to scrape {url}: {e}")
        return None


def scrape_job_offers(urls: list[str]) -> tuple[list[dict], list[dict]]:
    """Scrape multiple URLs; return successes + errors (batch-safe).

    Args:
        urls: List of job posting URLs

    Returns:
        (job_offers, errors)
    """
    job_offers = []
    errors = []

    for url in urls:
        try:
            offer = scrape_job_offer(url)
            if offer:
                job_offers.append(offer)
            else:
                errors.append({"url": url, "error": "Extraction failed (too short or no title)"})
        except Exception as e:
            errors.append({"url": url, "error": str(e)})

    logger.info(f"Scraping complete: {len(job_offers)} success, {len(errors)} errors")
    return job_offers, errors

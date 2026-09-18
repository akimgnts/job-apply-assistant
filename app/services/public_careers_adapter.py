"""Phase 2B: Public careers page adapter.

Scrapes real career pages from well-known companies.
Uses static URLs + HTML parsing. No API keys, no auth.
"""

import logging
from bs4 import BeautifulSoup
import aiohttp

from app.models.job_source_adapter import (
    JobSourceAdapter,
    DiscoveredJobUrl,
    NormalizedJobOffer,
)

logger = logging.getLogger(__name__)

# Real public career sites
PUBLIC_CAREERS = [
    ("https://careers.stripe.com", "Stripe", "stripe"),
    ("https://jobs.lever.co/zapier", "Zapier", "zapier"),
    ("https://boards.greenhouse.io/klarna", "Klarna", "klarna"),
    ("https://careers.vimeo.com", "Vimeo", "vimeo"),
    ("https://jobs.loom.com", "Loom", "loom"),
]


class PublicCareersAdapter(JobSourceAdapter):
    """Discover jobs from public career pages."""

    source_name = "public_careers"
    collection_strategy = "scrape"

    def __init__(self, session: aiohttp.ClientSession = None):
        self.session = session
        self.own_session = session is None

    async def _ensure_session(self):
        if self.session is None:
            self.session = aiohttp.ClientSession()

    async def close(self):
        if self.own_session and self.session:
            await self.session.close()

    async def discover_jobs(self, context: dict) -> list[DiscoveredJobUrl]:
        """Discover jobs from public career pages."""
        await self._ensure_session()

        discovered = []

        for base_url, company_name, company_slug in PUBLIC_CAREERS:
            try:
                logger.info(f"Scraping {company_name} careers page")

                async with self.session.get(base_url, timeout=10) as resp:
                    if resp.status != 200:
                        logger.warning(f"{company_name} returned {resp.status}")
                        continue

                    html = await resp.text()
                    soup = BeautifulSoup(html, "html.parser")

                    # Find job links (generic selectors for common patterns)
                    job_links = soup.find_all("a", href=True)

                    for link in job_links:
                        href = link.get("href", "")
                        text = link.get_text(strip=True)

                        # Filter job-like links
                        if not self._is_job_link(href, text):
                            continue

                        # Normalize URL
                        if href.startswith("/"):
                            full_url = base_url.rstrip("/") + href
                        elif href.startswith("http"):
                            full_url = href
                        else:
                            continue

                        if full_url in [d.url for d in discovered]:
                            continue

                        discovered.append(
                            DiscoveredJobUrl(
                                url=full_url,
                                metadata={
                                    "title": text[:100],
                                    "company_name": company_name,
                                    "company_slug": company_slug,
                                    "source": "public_careers",
                                },
                            )
                        )

                    logger.info(f"Discovered {len(discovered)} jobs from {company_name}")

            except Exception as e:
                logger.error(f"Career page scrape error for {company_name}: {e}")

        return discovered

    def _is_job_link(self, href: str, text: str) -> bool:
        """Heuristic to detect job posting links."""
        href_lower = href.lower()
        text_lower = text.lower()

        job_keywords = [
            "job", "position", "opening", "role", "career",
            "apply", "hiring", "vacancies", "vacancy", "offre"
        ]

        return any(kw in href_lower or kw in text_lower for kw in job_keywords)

    async def extract_job(self, discovered: DiscoveredJobUrl) -> dict:
        """Extract job details from page."""
        await self._ensure_session()

        url = discovered.url

        try:
            async with self.session.get(url, timeout=10) as resp:
                if resp.status != 200:
                    raise Exception(f"HTTP {resp.status}")

                html = await resp.text()
                soup = BeautifulSoup(html, "html.parser")

                result = {
                    "url": url,
                    "source_url": url,
                    "company_name": discovered.metadata.get("company_name"),
                    "company_slug": discovered.metadata.get("company_slug"),
                    "extraction_method": "public_careers_html",
                    "extraction_confidence": 0.6,
                }

                # Extract title
                title = discovered.metadata.get("title", "Unknown Job")
                result["title"] = title

                # Try to extract location
                page_text = soup.get_text().lower()
                if "remote" in page_text:
                    result["location"] = "Remote"
                    result["extraction_confidence"] += 0.15

                # Try to extract job ID if present
                if "/jobs/" in url:
                    parts = url.split("/jobs/")
                    if len(parts) > 1:
                        job_id = parts[-1].split("/")[0]
                        result["external_job_id"] = job_id

                return result

        except Exception as e:
            logger.error(f"Extraction error for {url}: {e}")
            return {
                "url": url,
                "source_url": url,
                "company_name": discovered.metadata.get("company_name"),
                "title": discovered.metadata.get("title", "Unknown Job"),
                "extraction_method": "error",
                "extraction_confidence": 0.0,
            }

    async def normalize_job(self, extracted: dict) -> NormalizedJobOffer:
        """Normalize to canonical schema."""
        return NormalizedJobOffer(
            job_title=extracted.get("title") or "Public Careers Job",
            company_name=extracted.get("company_name") or "Unknown",
            job_url=extracted.get("source_url") or extracted.get("url"),
            source=self.source_name,
            location=extracted.get("location"),
            contract_type=extracted.get("contract_type"),
            external_job_id=extracted.get("external_job_id"),
            raw_text=f"Company: {extracted.get('company_name')}\nSlug: {extracted.get('company_slug')}",
        )

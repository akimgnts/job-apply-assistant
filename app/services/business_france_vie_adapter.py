"""Phase 2B: Business France VIE (Volontariat International en Entreprise) adapter.

VIE is a French international volunteer employment program.
Business France publishes listings via public HTML.
"""

import logging
from urllib.parse import urljoin
from bs4 import BeautifulSoup
import aiohttp

from app.models.job_source_adapter import (
    JobSourceAdapter,
    DiscoveredJobUrl,
    NormalizedJobOffer,
)

logger = logging.getLogger(__name__)

BUSINESS_FRANCE_VIE_URL = "https://www.businessfrance.fr/offres-de-volontariat"


class BusinessFranceVieAdapter(JobSourceAdapter):
    """Discover VIE opportunities from Business France."""

    source_name = "business_france_vie"
    collection_strategy = "search"

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
        """Discover VIE opportunities from Business France.

        Context:
            search_terms: str or list (filter keywords)
            max_results: int (default 50)
        """
        await self._ensure_session()

        search_terms = context.get("search_terms", "")
        max_results = context.get("max_results", 50)

        logger.info(f"Searching Business France VIE")

        discovered = []

        try:
            async with self.session.get(BUSINESS_FRANCE_VIE_URL, timeout=10) as resp:
                if resp.status != 200:
                    logger.warning(f"Business France VIE returned {resp.status}")
                    return discovered

                html = await resp.text()
                soup = BeautifulSoup(html, "html.parser")

                # Find VIE opportunity links
                vie_links = soup.find_all("a", href=lambda x: x and "/volontariat" in x)

                for link in vie_links[:max_results]:
                    href = link.get("href")
                    if not href:
                        continue

                    vie_url = urljoin("https://www.businessfrance.fr", href)
                    title = link.get_text(strip=True) or "Business France VIE"

                    # Extract VIE ID if present
                    vie_id = None
                    if "/volontariat/" in href:
                        parts = href.split("/volontariat/")
                        if len(parts) > 1:
                            vie_id = parts[1].split("/")[0]

                    discovered.append(
                        DiscoveredJobUrl(
                            url=vie_url,
                            metadata={
                                "title": title,
                                "vie_id": vie_id,
                                "source": "business_france_vie",
                                "program": "VIE",
                            },
                        )
                    )

                logger.info(f"Discovered {len(discovered)} VIE opportunities")

        except Exception as e:
            logger.error(f"Business France VIE discovery error: {e}")

        return discovered

    async def extract_job(self, discovered: DiscoveredJobUrl) -> dict:
        """Extract VIE opportunity details."""
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
                    "vie_id": discovered.metadata.get("vie_id"),
                    "program": "VIE",
                    "extraction_method": "business_france_via_html",
                    "extraction_confidence": 0.5,
                }

                # Extract title
                title_elem = soup.find("h1")
                if title_elem:
                    result["title"] = title_elem.get_text(strip=True)
                    result["extraction_confidence"] += 0.15

                # Extract company
                company_elem = soup.find("p", class_=lambda x: x and "company" in x.lower())
                if company_elem:
                    result["company_name"] = company_elem.get_text(strip=True)
                    result["extraction_confidence"] += 0.15

                # Extract location (country/city)
                location_elem = soup.find(
                    "p", class_=lambda x: x and ("location" in x.lower() or "pays" in x.lower())
                )
                if location_elem:
                    result["location"] = location_elem.get_text(strip=True)
                    result["extraction_confidence"] += 0.10

                # VIE is always fixed-term contract (12-24 months)
                result["contract_type"] = "VIE"
                result["extraction_confidence"] += 0.05

                # Extract description
                desc_elem = soup.find(
                    "div", class_=lambda x: x and ("description" in x.lower() or "detail" in x.lower())
                )
                if desc_elem:
                    desc_text = desc_elem.get_text(strip=True)
                    result["description"] = desc_text[:2000]
                    result["extraction_confidence"] += 0.20

                return result

        except Exception as e:
            logger.error(f"Business France VIE extraction error for {url}: {e}")
            return {
                "url": url,
                "source_url": url,
                "vie_id": discovered.metadata.get("vie_id"),
                "title": discovered.metadata.get("title", "Business France VIE"),
                "program": "VIE",
                "extraction_method": "business_france_via_error",
                "extraction_confidence": 0.0,
            }

    async def normalize_job(self, extracted: dict) -> NormalizedJobOffer:
        """Normalize VIE opportunity to canonical schema."""
        return NormalizedJobOffer(
            job_title=extracted.get("title") or "VIE Opportunity",
            company_name=extracted.get("company_name") or "Unknown",
            job_url=extracted.get("source_url") or extracted.get("url"),
            source=self.source_name,
            location=extracted.get("location"),
            contract_type=extracted.get("contract_type", "VIE"),
            raw_text=extracted.get("description"),
            external_job_id=extracted.get("vie_id"),
            description=extracted.get("description"),
        )

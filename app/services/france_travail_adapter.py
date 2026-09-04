"""Phase 2B: France Travail job board adapter.

France Travail (formerly Pôle Emploi) provides job postings.
Uses public search endpoint via HTML parsing.
"""

import logging
from urllib.parse import urljoin, quote
from bs4 import BeautifulSoup
import aiohttp

from app.models.job_source_adapter import (
    JobSourceAdapter,
    DiscoveredJobUrl,
    NormalizedJobOffer,
)

logger = logging.getLogger(__name__)

FRANCE_TRAVAIL_SEARCH_URL = "https://www.pole-emploi.fr/offres-emploi/recherche"


class FranceTravailAdapter(JobSourceAdapter):
    """Discover jobs from France Travail via public HTML."""

    source_name = "france_travail"
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
        """Discover jobs from France Travail search.

        Context:
            search_terms: str or list
            location: str (optional)
            max_results: int (default 50)
        """
        await self._ensure_session()

        search_terms = context.get("search_terms", "Data")
        location = context.get("location")
        max_results = context.get("max_results", 50)

        if isinstance(search_terms, list):
            search_terms = " ".join(search_terms)

        logger.info(f"Searching France Travail: {search_terms}")

        discovered = []

        try:
            # Build search URL
            search_url = f"{FRANCE_TRAVAIL_SEARCH_URL}?motsCles={quote(search_terms)}"
            if location:
                search_url += f"&lieuTravail={quote(location)}"

            async with self.session.get(search_url, timeout=10) as resp:
                if resp.status != 200:
                    logger.warning(f"France Travail returned {resp.status}")
                    return discovered

                html = await resp.text()
                soup = BeautifulSoup(html, "html.parser")

                # Find job links (France Travail structure: /offres-emploi/...)
                job_links = soup.find_all("a", href=lambda x: x and "/offre-" in x)

                for link in job_links[:max_results]:
                    href = link.get("href")
                    if not href:
                        continue

                    job_url = urljoin("https://www.pole-emploi.fr", href)
                    title = link.get_text(strip=True) or "France Travail Job"

                    # Extract job ID
                    job_id = None
                    if "/offre-" in href:
                        parts = href.split("/offre-")
                        if len(parts) > 1:
                            job_id = parts[1].split("/")[0]

                    discovered.append(
                        DiscoveredJobUrl(
                            url=job_url,
                            metadata={
                                "title": title,
                                "job_id": job_id,
                                "source": "france_travail_search",
                            },
                        )
                    )

                logger.info(f"Discovered {len(discovered)} France Travail offers")

        except Exception as e:
            logger.error(f"France Travail discovery error: {e}")

        return discovered

    async def extract_job(self, discovered: DiscoveredJobUrl) -> dict:
        """Extract job details from France Travail job page."""
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
                    "job_id": discovered.metadata.get("job_id"),
                    "extraction_method": "france_travail_html",
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

                # Extract location
                location_elem = soup.find(
                    "p", class_=lambda x: x and ("location" in x.lower() or "lieu" in x.lower())
                )
                if location_elem:
                    result["location"] = location_elem.get_text(strip=True)
                    result["extraction_confidence"] += 0.10

                # Extract contract type
                page_text = soup.get_text().lower()
                if "cdi" in page_text:
                    result["contract_type"] = "CDI"
                    result["extraction_confidence"] += 0.10
                elif "cdd" in page_text:
                    result["contract_type"] = "CDD"
                    result["extraction_confidence"] += 0.10

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
            logger.error(f"France Travail extraction error for {url}: {e}")
            return {
                "url": url,
                "source_url": url,
                "job_id": discovered.metadata.get("job_id"),
                "title": discovered.metadata.get("title", "France Travail Job"),
                "extraction_method": "france_travail_error",
                "extraction_confidence": 0.0,
            }

    async def normalize_job(self, extracted: dict) -> NormalizedJobOffer:
        """Normalize France Travail job to canonical schema."""
        return NormalizedJobOffer(
            job_title=extracted.get("title") or "France Travail Job",
            company_name=extracted.get("company_name") or "Unknown",
            job_url=extracted.get("source_url") or extracted.get("url"),
            source=self.source_name,
            location=extracted.get("location"),
            contract_type=extracted.get("contract_type"),
            raw_text=extracted.get("description"),
            external_job_id=extracted.get("job_id"),
            description=extracted.get("description"),
        )

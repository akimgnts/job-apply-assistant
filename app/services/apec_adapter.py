"""Phase 2B: APEC job board adapter.

APEC (Association pour l'Emploi des Cadres) provides French job postings.
Public HTML scraping via job search results and detail pages.
"""

import asyncio
import logging
from urllib.parse import urljoin
from bs4 import BeautifulSoup
import aiohttp

from app.models.job_source_adapter import (
    JobSourceAdapter,
    DiscoveredJobUrl,
    NormalizedJobOffer,
)
from app.services.url_normalizer import normalize_url

logger = logging.getLogger(__name__)

APEC_SEARCH_URL = "https://www.apec.fr/app/recherche/offres-emploi"


class ApecAdapter(JobSourceAdapter):
    """Discover jobs from APEC via public HTML parsing."""

    source_name = "apec"
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
        """Discover jobs from APEC search results.

        Context:
            search_terms: str or list (e.g., "Data Analyst" or ["Data", "BI"])
            max_results: int (default 100)
            page: int (default 1)
        """
        await self._ensure_session()

        search_terms = context.get("search_terms", "Data")
        max_results = context.get("max_results", 100)

        if isinstance(search_terms, list):
            search_terms = " ".join(search_terms)

        logger.info(f"Searching APEC: {search_terms}")

        discovered = []

        try:
            # APEC search via keywords
            search_url = f"{APEC_SEARCH_URL}?motsCles={search_terms}"

            async with self.session.get(search_url, timeout=10) as resp:
                if resp.status != 200:
                    logger.warning(f"APEC search returned {resp.status}")
                    return discovered

                html = await resp.text()
                soup = BeautifulSoup(html, "html.parser")

                # Find job links (APEC structure: job links with /offre- in href)
                job_links = soup.find_all("a", href=lambda x: x and "/offre-" in x)

                for link in job_links[:max_results]:
                    href = link.get("href")
                    if not href:
                        continue

                    job_url = urljoin("https://www.apec.fr", href)
                    title = link.get_text(strip=True) or "APEC Job"

                    # Extract APEC job ID from URL
                    apec_id = None
                    if "/offre-" in href:
                        parts = href.split("/offre-")
                        if len(parts) > 1:
                            apec_id = parts[1].split("/")[0]

                    discovered.append(
                        DiscoveredJobUrl(
                            url=job_url,
                            metadata={
                                "title": title,
                                "apec_id": apec_id,
                                "source": "apec_search",
                            },
                        )
                    )

                logger.info(f"Discovered {len(discovered)} APEC offers")

        except Exception as e:
            logger.error(f"APEC discovery error: {e}")

        return discovered

    async def extract_job(self, discovered: DiscoveredJobUrl) -> dict:
        """Extract job details from APEC job detail page."""
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
                    "apec_id": discovered.metadata.get("apec_id"),
                    "extraction_method": "apec_html",
                    "extraction_confidence": 0.5,
                }

                # Extract title
                title_elem = soup.find("h1", class_=lambda x: x and "offre" in x.lower())
                if title_elem:
                    result["title"] = title_elem.get_text(strip=True)
                    result["extraction_confidence"] += 0.15

                # Extract company
                company_elem = soup.find(
                    "a", attrs={"data-company": True}
                ) or soup.find("span", class_=lambda x: x and "company" in x.lower())
                if company_elem:
                    result["company_name"] = company_elem.get_text(strip=True)
                    result["extraction_confidence"] += 0.15

                # Extract location
                location_elem = soup.find(
                    "span", class_=lambda x: x and ("location" in x.lower() or "ville" in x.lower())
                )
                if location_elem:
                    result["location"] = location_elem.get_text(strip=True)
                    result["extraction_confidence"] += 0.10

                # Extract contract type (CDI/CDD)
                contract_text = soup.get_text().lower()
                if "cdi" in contract_text:
                    result["contract_type"] = "CDI"
                    result["extraction_confidence"] += 0.10
                elif "cdd" in contract_text:
                    result["contract_type"] = "CDD"
                    result["extraction_confidence"] += 0.10

                # Extract description
                desc_elem = soup.find(
                    "div", class_=lambda x: x and ("description" in x.lower() or "content" in x.lower())
                )
                if desc_elem:
                    desc_text = desc_elem.get_text(strip=True)
                    result["description"] = desc_text[:2000]
                    result["extraction_confidence"] += 0.20

                # Extract skills (if listed)
                skills = []
                skills_section = soup.find(
                    text=lambda x: x and "compétences" in x.lower()
                )
                if skills_section:
                    parent = skills_section.find_parent()
                    if parent:
                        skill_lis = parent.find_all("li")
                        skills = [li.get_text(strip=True) for li in skill_lis[:10]]

                if skills:
                    result["skills"] = skills
                    result["extraction_confidence"] += 0.10

                return result

        except Exception as e:
            logger.error(f"APEC extraction error for {url}: {e}")
            return {
                "url": url,
                "source_url": url,
                "apec_id": discovered.metadata.get("apec_id"),
                "title": discovered.metadata.get("title", "APEC Job"),
                "extraction_method": "apec_error",
                "extraction_confidence": 0.0,
            }

    async def normalize_job(self, extracted: dict) -> NormalizedJobOffer:
        """Normalize APEC job to canonical schema."""
        return NormalizedJobOffer(
            job_title=extracted.get("title") or "APEC Job",
            company_name=extracted.get("company_name") or "Unknown",
            job_url=extracted.get("source_url") or extracted.get("url"),
            source=self.source_name,
            location=extracted.get("location"),
            contract_type=extracted.get("contract_type"),
            raw_text=extracted.get("description"),
            external_job_id=extracted.get("apec_id"),
            required_skills=extracted.get("skills"),
            description=extracted.get("description"),
        )

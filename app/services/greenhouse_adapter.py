"""Phase 2B: Greenhouse job board adapter.

Greenhouse (greenhouse.io) hosts career pages for many companies.
Public API access via structured job board endpoints.
"""

import logging
import json
from typing import Optional
import aiohttp

from app.models.job_source_adapter import (
    JobSourceAdapter,
    DiscoveredJobUrl,
    NormalizedJobOffer,
)

logger = logging.getLogger(__name__)

# Popular companies with Greenhouse boards
GREENHOUSE_BOARDS = [
    ("stripe", "Stripe"),
    ("vercel", "Vercel"),
    ("figma", "Figma"),
    ("notion", "Notion"),
    ("linear", "Linear"),
    ("retool", "Retool"),
    ("supabase", "Supabase"),
    ("chainalysis", "Chainalysis"),
    ("amplitude", "Amplitude"),
    ("miro", "Miro"),
    ("paragon", "Paragon"),
    ("airtable", "Airtable"),
]


class GreenhouseAdapter(JobSourceAdapter):
    """Discover jobs from Greenhouse-powered career boards."""

    source_name = "greenhouse"
    collection_strategy = "api"

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
        """Discover jobs from Greenhouse boards.

        Context:
            company_slugs: list of Greenhouse company slugs (optional, defaults to known)
            max_per_company: int (default 50)
        """
        await self._ensure_session()

        company_slugs = context.get("company_slugs", [slug for slug, _ in GREENHOUSE_BOARDS])
        max_per_company = context.get("max_per_company", 50)

        discovered = []

        for slug in company_slugs[:10]:  # Limit to 10 companies per run
            try:
                logger.info(f"Discovering Greenhouse jobs for {slug}")
                board_url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true"

                async with self.session.get(board_url, timeout=10) as resp:
                    if resp.status != 200:
                        logger.warning(f"Greenhouse {slug} returned {resp.status}")
                        continue

                    data = await resp.json()
                    jobs = data.get("jobs", [])

                    for job in jobs[:max_per_company]:
                        job_id = job.get("id")
                        title = job.get("title", "Unknown")
                        absolute_url = job.get("absolute_url")

                        if not absolute_url:
                            continue

                        discovered.append(
                            DiscoveredJobUrl(
                                url=absolute_url,
                                metadata={
                                    "title": title,
                                    "job_id": job_id,
                                    "company_slug": slug,
                                    "source": "greenhouse",
                                },
                            )
                        )

                    logger.info(f"Discovered {len(jobs[:max_per_company])} jobs from {slug}")

            except Exception as e:
                logger.error(f"Greenhouse discovery error for {slug}: {e}")

        return discovered

    async def extract_job(self, discovered: DiscoveredJobUrl) -> dict:
        """Extract job details from Greenhouse job page."""
        await self._ensure_session()

        url = discovered.url

        try:
            async with self.session.get(url, timeout=10) as resp:
                if resp.status != 200:
                    raise Exception(f"HTTP {resp.status}")

                html = await resp.text()

                result = {
                    "url": url,
                    "source_url": url,
                    "job_id": discovered.metadata.get("job_id"),
                    "company_slug": discovered.metadata.get("company_slug"),
                    "extraction_method": "greenhouse_html",
                    "extraction_confidence": 0.7,
                }

                # Extract title
                title = discovered.metadata.get("title", "Greenhouse Job")
                result["title"] = title

                # Try to extract location and description from HTML
                if "<" in html:
                    # Basic HTML parsing for location markers
                    if "location" in html.lower() or "remote" in html.lower():
                        if "remote" in html.lower():
                            result["location"] = "Remote"
                            result["extraction_confidence"] += 0.1
                        else:
                            result["location"] = "Onsite"

                    # Extract description (simplified)
                    if 'class="description"' in html or 'class="job-description"' in html:
                        result["extraction_confidence"] += 0.15

                return result

        except Exception as e:
            logger.error(f"Greenhouse extraction error for {url}: {e}")
            return {
                "url": url,
                "source_url": url,
                "job_id": discovered.metadata.get("job_id"),
                "company_slug": discovered.metadata.get("company_slug"),
                "title": discovered.metadata.get("title", "Greenhouse Job"),
                "extraction_method": "greenhouse_error",
                "extraction_confidence": 0.0,
            }

    async def normalize_job(self, extracted: dict) -> NormalizedJobOffer:
        """Normalize Greenhouse job to canonical schema."""
        # Map slug to company name
        slug_to_name = dict(GREENHOUSE_BOARDS)
        company_slug = extracted.get("company_slug", "")
        company_name = slug_to_name.get(company_slug, company_slug.title())

        return NormalizedJobOffer(
            job_title=extracted.get("title") or "Greenhouse Job",
            company_name=company_name,
            job_url=extracted.get("source_url") or extracted.get("url"),
            source=self.source_name,
            location=extracted.get("location"),
            contract_type=extracted.get("contract_type"),
            external_job_id=extracted.get("job_id"),
            raw_text=f"Company Slug: {company_slug}",
            description=extracted.get("description"),
        )

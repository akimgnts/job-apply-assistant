"""Phase 2B: Ashby job board adapter.

Ashby (ashby.com) hosts career pages for many companies.
Public GraphQL API access via company job postings.
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

# Popular companies with Ashby boards (verified slug names)
ASHBY_COMPANIES = [
    ("notion", "Notion"),
    ("perplexity", "Perplexity"),
    ("loom", "Loom"),
    ("anthropic", "Anthropic"),
]


class AshbyAdapter(JobSourceAdapter):
    """Discover jobs from Ashby-powered career boards."""

    source_name = "ashby"
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
        """Discover jobs from Ashby job boards.

        Context:
            company_slugs: list of Ashby company board slugs (optional, defaults to known)
            max_per_company: int (default 50)
        """
        await self._ensure_session()

        company_slugs = context.get("company_slugs", [slug for slug, _ in ASHBY_COMPANIES])
        max_per_company = context.get("max_per_company", 50)

        discovered = []

        for slug in company_slugs[:10]:
            try:
                logger.info(f"Discovering Ashby jobs for {slug}")
                # Ashby REST API endpoint
                api_url = f"https://api.ashbyhq.com/posting-api/job-board/{slug}"

                async with self.session.get(api_url, timeout=10) as resp:
                    if resp.status != 200:
                        logger.warning(f"Ashby {slug} returned {resp.status}")
                        continue

                    data = await resp.json()
                    jobs = data.get("jobs", [])

                    for job in jobs[:max_per_company]:
                        job_id = job.get("id")
                        title = job.get("title", "Unknown")
                        job_url = job.get("jobUrl") or job.get("url", "")
                        location = job.get("location", {})
                        location_name = location.get("name") if isinstance(location, dict) else location

                        if not job_url:
                            job_url = f"https://jobs.ashby.com/{slug}/{job_id}"

                        discovered.append(
                            DiscoveredJobUrl(
                                url=job_url,
                                metadata={
                                    "title": title,
                                    "job_id": job_id,
                                    "company_slug": slug,
                                    "location": location_name,
                                    "source": "ashby",
                                },
                            )
                        )

                    logger.info(f"Discovered {len(jobs[:max_per_company])} jobs from {slug}")

            except Exception as e:
                logger.error(f"Ashby discovery error for {slug}: {e}")

        return discovered

    async def extract_job(self, discovered: DiscoveredJobUrl) -> dict:
        """Extract job details from Ashby API metadata."""
        await self._ensure_session()

        url = discovered.url

        result = {
            "url": url,
            "source_url": url,
            "job_id": discovered.metadata.get("job_id"),
            "company_slug": discovered.metadata.get("company_slug"),
            "extraction_method": "ashby_api_metadata",
            "extraction_confidence": 0.95,
        }

        # Extract title from metadata
        title = discovered.metadata.get("title", "Ashby Job")
        result["title"] = title

        # Location from API metadata
        location = discovered.metadata.get("location")
        if location:
            result["location"] = location

        return result

    async def normalize_job(self, extracted: dict) -> NormalizedJobOffer:
        """Normalize Ashby job to canonical schema."""
        # Map company slug to name
        slug_to_name = dict(ASHBY_COMPANIES)
        company_slug = extracted.get("company_slug", "")
        company_name = slug_to_name.get(company_slug, company_slug.title())

        return NormalizedJobOffer(
            job_title=extracted.get("title") or "Ashby Job",
            company_name=company_name,
            job_url=extracted.get("source_url") or extracted.get("url"),
            source=self.source_name,
            location=extracted.get("location"),
            contract_type=extracted.get("contract_type"),
            external_job_id=extracted.get("job_id"),
            raw_text=f"Company Slug: {company_slug}",
            description=extracted.get("description"),
        )

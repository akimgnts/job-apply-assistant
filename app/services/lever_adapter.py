"""Phase 2B: Lever job board adapter.

Lever (lever.co) hosts career pages for many companies.
Public REST API access via company posting endpoints.
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

# Popular companies with Lever boards
LEVER_COMPANIES = [
    ("zapier", "Zapier"),
    ("guidepoint", "GuidePoint"),
    ("deel", "Deel"),
    ("getir", "Getir"),
    ("vanta", "Vanta"),
    ("hopin", "Hopin"),
    ("melio", "Melio"),
    ("tessian", "Tessian"),
    ("guarding", "Guarding"),
    ("talentdesk", "TalentDesk"),
]


class LeverAdapter(JobSourceAdapter):
    """Discover jobs from Lever-powered career boards."""

    source_name = "lever"
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
        """Discover jobs from Lever boards.

        Context:
            company_handles: list of Lever company handles (optional, defaults to known)
            max_per_company: int (default 50)
        """
        await self._ensure_session()

        company_handles = context.get("company_handles", [handle for handle, _ in LEVER_COMPANIES])
        max_per_company = context.get("max_per_company", 50)

        discovered = []

        for handle in company_handles[:10]:
            try:
                logger.info(f"Discovering Lever jobs for {handle}")
                # Lever API: https://api.lever.co/v0/postings/{company_handle}
                api_url = f"https://api.lever.co/v0/postings/{handle}?mode=json"

                async with self.session.get(api_url, timeout=10) as resp:
                    if resp.status != 200:
                        logger.warning(f"Lever {handle} returned {resp.status}")
                        continue

                    data = await resp.json()

                    # API returns list directly, not wrapped in {data: [...]}
                    postings = data if isinstance(data, list) else data.get("data", [])

                    for posting in postings[:max_per_company]:
                        posting_id = posting.get("id")
                        title = posting.get("text", "Unknown")
                        location = posting.get("categories", {}).get("location")
                        posting_url = posting.get("urls", {}).get("posting", "")

                        if not posting_url:
                            posting_url = f"https://jobs.lever.co/{handle}/apply/{posting_id}"

                        discovered.append(
                            DiscoveredJobUrl(
                                url=posting_url,
                                metadata={
                                    "title": title,
                                    "posting_id": posting_id,
                                    "company_handle": handle,
                                    "location": location,
                                    "source": "lever",
                                },
                            )
                        )

                    logger.info(f"Discovered {len(postings[:max_per_company])} jobs from {handle}")

            except Exception as e:
                logger.error(f"Lever discovery error for {handle}: {e}")

        return discovered

    async def extract_job(self, discovered: DiscoveredJobUrl) -> dict:
        """Extract job details from Lever job page."""
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
                    "posting_id": discovered.metadata.get("posting_id"),
                    "company_handle": discovered.metadata.get("company_handle"),
                    "extraction_method": "lever_api_metadata",
                    "extraction_confidence": 0.95,
                }

                # Extract title from metadata
                title = discovered.metadata.get("title", "Lever Job")
                result["title"] = title

                # Extract location from API metadata (not from HTML)
                location = discovered.metadata.get("location")
                if location:
                    result["location"] = location

                return result

        except Exception as e:
            logger.error(f"Lever extraction error for {url}: {e}")
            return {
                "url": url,
                "source_url": url,
                "posting_id": discovered.metadata.get("posting_id"),
                "company_handle": discovered.metadata.get("company_handle"),
                "title": discovered.metadata.get("title", "Lever Job"),
                "location": discovered.metadata.get("location"),
                "extraction_method": "lever_api_metadata",
                "extraction_confidence": 0.95,
            }

    async def normalize_job(self, extracted: dict) -> NormalizedJobOffer:
        """Normalize Lever job to canonical schema."""
        # Map handle to company name
        handle_to_name = dict(LEVER_COMPANIES)
        company_handle = extracted.get("company_handle", "")
        company_name = handle_to_name.get(company_handle, company_handle.title())

        return NormalizedJobOffer(
            job_title=extracted.get("title") or "Lever Job",
            company_name=company_name,
            job_url=extracted.get("source_url") or extracted.get("url"),
            source=self.source_name,
            location=extracted.get("location"),
            contract_type=extracted.get("contract_type"),
            external_job_id=extracted.get("posting_id"),
            raw_text=f"Company Handle: {company_handle}",
            description=extracted.get("description"),
        )

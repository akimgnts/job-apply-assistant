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

# Popular companies with Ashby boards
ASHBY_COMPANIES = [
    ("greenhouse", "Greenhouse"),
    ("notion-company", "Notion"),
    ("stripe-company", "Stripe"),
    ("anthropic", "Anthropic"),
    ("loom", "Loom"),
    ("midjourney", "Midjourney"),
    ("perplexity", "Perplexity"),
    ("figma-company", "Figma"),
    ("retool-company", "Retool"),
    ("vimeo", "Vimeo"),
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
        """Discover jobs from Ashby boards.

        Context:
            company_ids: list of Ashby company IDs (optional, defaults to known)
            max_per_company: int (default 50)
        """
        await self._ensure_session()

        company_ids = context.get("company_ids", [company_id for company_id, _ in ASHBY_COMPANIES])
        max_per_company = context.get("max_per_company", 50)

        discovered = []

        for company_id in company_ids[:10]:
            try:
                logger.info(f"Discovering Ashby jobs for {company_id}")
                # Ashby GraphQL endpoint
                graphql_url = "https://api.ashby.io/graphql.public"

                query = {
                    "query": """
                    query GetJobs($companyId: String!) {
                        jobs(input: {companyId: $companyId}) {
                            edges {
                                node {
                                    id
                                    title
                                    descriptionPlain
                                    jobUrl
                                    location {
                                        name
                                    }
                                }
                            }
                        }
                    }
                    """,
                    "variables": {"companyId": company_id}
                }

                async with self.session.post(
                    graphql_url,
                    json=query,
                    timeout=10,
                    headers={"Content-Type": "application/json"}
                ) as resp:
                    if resp.status != 200:
                        logger.warning(f"Ashby {company_id} returned {resp.status}")
                        continue

                    data = await resp.json()

                    # Handle errors in GraphQL response
                    if "errors" in data:
                        logger.warning(f"Ashby GraphQL error for {company_id}: {data['errors']}")
                        continue

                    edges = data.get("data", {}).get("jobs", {}).get("edges", [])

                    for edge in edges[:max_per_company]:
                        job = edge.get("node", {})
                        job_id = job.get("id")
                        title = job.get("title", "Unknown")
                        job_url = job.get("jobUrl", "")

                        if not job_url:
                            job_url = f"https://jobs.ashby.com/{company_id}/{job_id}"

                        discovered.append(
                            DiscoveredJobUrl(
                                url=job_url,
                                metadata={
                                    "title": title,
                                    "job_id": job_id,
                                    "company_id": company_id,
                                    "location": job.get("location", {}).get("name"),
                                    "source": "ashby",
                                },
                            )
                        )

                    logger.info(f"Discovered {len(edges[:max_per_company])} jobs from {company_id}")

            except Exception as e:
                logger.error(f"Ashby discovery error for {company_id}: {e}")

        return discovered

    async def extract_job(self, discovered: DiscoveredJobUrl) -> dict:
        """Extract job details from Ashby job page."""
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
                    "company_id": discovered.metadata.get("company_id"),
                    "extraction_method": "ashby_html",
                    "extraction_confidence": 0.7,
                }

                # Extract title
                title = discovered.metadata.get("title", "Ashby Job")
                result["title"] = title

                # Location from metadata
                location = discovered.metadata.get("location")
                if location:
                    result["location"] = location
                    result["extraction_confidence"] += 0.1

                return result

        except Exception as e:
            logger.error(f"Ashby extraction error for {url}: {e}")
            return {
                "url": url,
                "source_url": url,
                "job_id": discovered.metadata.get("job_id"),
                "company_id": discovered.metadata.get("company_id"),
                "title": discovered.metadata.get("title", "Ashby Job"),
                "location": discovered.metadata.get("location"),
                "extraction_method": "ashby_error",
                "extraction_confidence": 0.0,
            }

    async def normalize_job(self, extracted: dict) -> NormalizedJobOffer:
        """Normalize Ashby job to canonical schema."""
        # Map company ID to name
        id_to_name = dict(ASHBY_COMPANIES)
        company_id = extracted.get("company_id", "")
        company_name = id_to_name.get(company_id, company_id.title())

        return NormalizedJobOffer(
            job_title=extracted.get("title") or "Ashby Job",
            company_name=company_name,
            job_url=extracted.get("source_url") or extracted.get("url"),
            source=self.source_name,
            location=extracted.get("location"),
            contract_type=extracted.get("contract_type"),
            external_job_id=extracted.get("job_id"),
            raw_text=f"Company ID: {company_id}",
            description=extracted.get("description"),
        )

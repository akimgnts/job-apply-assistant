"""Phase 2B: Business France VIE job board adapter.

Business France VIE (https://mon-vie-via.businessfrance.fr/) — French work-abroad program.
Public REST API at civiweb-api-prd.azurewebsites.net.
"""

import logging
import os
from typing import Optional
import aiohttp

from app.models.job_source_adapter import (
    JobSourceAdapter,
    DiscoveredJobUrl,
    NormalizedJobOffer,
)

logger = logging.getLogger(__name__)

API_URL = "https://civiweb-api-prd.azurewebsites.net/api/Offers/search"
API_KEY = os.getenv("BUSINESS_FRANCE_VIE_API_KEY", "")


class BusinessFranceVieAdapter(JobSourceAdapter):
    """Discover jobs from Business France VIE API."""

    source_name = "business_france_vie"
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
        """Discover jobs from Business France VIE API with pagination.

        Context:
            max_per_company: int (default 500, no limit)
        """
        await self._ensure_session()

        if not API_KEY:
            logger.error("BUSINESS_FRANCE_VIE_API_KEY not set")
            return []

        max_results = context.get("max_per_company", 500)
        discovered = []
        page_size = 100
        skip = 0

        try:
            logger.info("Discovering Business France VIE jobs (paginated)")

            headers = {
                "x-api-key": API_KEY,
                "Content-Type": "application/json"
            }

            while len(discovered) < max_results:
                payload = {
                    "limit": min(page_size, max_results - len(discovered)),
                    "skip": skip,
                    "query": None,
                    "teletravail": ["0"],
                    "porteEnv": ["0"],
                    "activitySectorId": [],
                    "companiesSizes": [],
                    "countriesIds": [],
                    "entreprisesIds": [0],
                    "geographicZones": [],
                    "missionStartDate": None,
                    "missionsDurations": [],
                    "missionsTypesIds": [],
                    "specializationsIds": [],
                    "studiesLevelId": []
                }

                async with self.session.post(API_URL, headers=headers, json=payload, timeout=10) as resp:
                    if resp.status != 200:
                        logger.warning(f"Business France VIE returned {resp.status}")
                        break

                    data = await resp.json()
                    offers = data.get("result", [])

                    if not offers:
                        break

                    for offer in offers:
                        if len(discovered) >= max_results:
                            break

                        offer_id = offer.get("id")
                        title = offer.get("missionTitle", "Unknown")
                        company = offer.get("organizationName", "Unknown")
                        city = offer.get("cityName", "")
                        duration = offer.get("missionDuration")

                        offer_url = f"https://mon-vie-via.businessfrance.fr/offre/{offer_id}"

                        discovered.append(
                            DiscoveredJobUrl(
                                url=offer_url,
                                metadata={
                                    "title": title,
                                    "company": company,
                                    "city": city,
                                    "duration": duration,
                                    "offer_id": offer_id,
                                    "source": "business_france_vie",
                                },
                            )
                        )

                    if len(offers) < page_size:
                        break

                    skip += page_size

            logger.info(f"Discovered {len(discovered)} total jobs from Business France VIE")

        except Exception as e:
            logger.error(f"Business France VIE discovery error: {e}")

        return discovered

    async def extract_job(self, discovered: DiscoveredJobUrl) -> dict:
        """Extract job details from Business France VIE metadata."""
        metadata = discovered.metadata

        result = {
            "url": discovered.url,
            "source_url": discovered.url,
            "offer_id": metadata.get("offer_id"),
            "extraction_method": "bfvie_api_metadata",
            "extraction_confidence": 0.95,
        }

        result["title"] = metadata.get("title", "Business France VIE Job")
        result["company"] = metadata.get("company", "Unknown")
        result["location"] = metadata.get("city")
        result["duration"] = metadata.get("duration")

        return result

    async def normalize_job(self, extracted: dict) -> NormalizedJobOffer:
        """Normalize Business France VIE job to canonical schema."""
        return NormalizedJobOffer(
            job_title=extracted.get("title") or "Business France VIE Job",
            company_name=extracted.get("company") or "Unknown",
            job_url=extracted.get("source_url") or extracted.get("url"),
            source=self.source_name,
            location=extracted.get("location"),
            contract_type="VIE",
            external_job_id=extracted.get("offer_id"),
            raw_text=f"Company: {extracted.get('company')}\nDuration: {extracted.get('duration')} months\nLocation: {extracted.get('location') or 'N/A'}",
            description=None,
        )

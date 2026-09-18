"""Phase 2B: Lever job board adapter."""

import logging
import aiohttp

from app.models.job_source_adapter import JobSourceAdapter, DiscoveredJobUrl, NormalizedJobOffer

logger = logging.getLogger(__name__)

LEVER_COMPANIES = [
    ("zapier", "Zapier"), ("guidepoint", "GuidePoint"), ("deel", "Deel"),
    ("getir", "Getir"), ("vanta", "Vanta"), ("hopin", "Hopin"),
    ("melio", "Melio"), ("tessian", "Tessian"), ("guarding", "Guarding"),
    ("talentdesk", "TalentDesk"),
]


class LeverAdapter(JobSourceAdapter):
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

    async def _fetch_postings(self, handle: str):
        """Try Lever's current public hosts; return postings or raise."""
        urls = [
            f"https://api.lever.co/v0/postings/{handle}?mode=json",
            f"https://api.eu.lever.co/v0/postings/{handle}?mode=json",
        ]
        errors = []
        for api_url in urls:
            try:
                async with self.session.get(api_url, timeout=15) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data if isinstance(data, list) else data.get("data", [])
                    errors.append(f"{api_url} -> HTTP {resp.status}")
            except Exception as exc:
                errors.append(f"{api_url} -> {exc}")
        raise RuntimeError("; ".join(errors))

    async def discover_jobs(self, context: dict) -> list[DiscoveredJobUrl]:
        await self._ensure_session()
        company_handles = context.get("company_handles", [handle for handle, _ in LEVER_COMPANIES])
        max_per_company = context.get("max_per_company", 50)
        discovered = []

        for handle in company_handles[:10]:
            postings = await self._fetch_postings(handle)
            selected = postings if max_per_company is None else postings[:max_per_company]
            for posting in selected:
                posting_id = posting.get("id")
                posting_url = posting.get("hostedUrl") or posting.get("applyUrl") or posting.get("urls", {}).get("posting")
                if not posting_url:
                    posting_url = f"https://jobs.lever.co/{handle}/{posting_id}"
                discovered.append(DiscoveredJobUrl(
                    url=posting_url,
                    metadata={
                        "title": posting.get("text", "Unknown"),
                        "posting_id": posting_id,
                        "company_handle": handle,
                        "location": posting.get("categories", {}).get("location"),
                        "description": posting.get("descriptionPlain") or posting.get("description"),
                        "source": "lever",
                    },
                ))
            logger.info(f"Discovered {len(selected)} jobs from {handle}")
        return discovered

    async def extract_job(self, discovered: DiscoveredJobUrl) -> dict:
        """Lever discovery API already contains canonical metadata; avoid a second page GET."""
        metadata = discovered.metadata
        return {
            "url": discovered.url,
            "source_url": discovered.url,
            "posting_id": metadata.get("posting_id"),
            "company_handle": metadata.get("company_handle"),
            "title": metadata.get("title", "Lever Job"),
            "location": metadata.get("location"),
            "description": metadata.get("description"),
            "extraction_method": "lever_api_metadata",
            "extraction_confidence": 0.95,
        }

    async def normalize_job(self, extracted: dict) -> NormalizedJobOffer:
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

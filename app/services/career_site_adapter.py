"""Phase 2B: Career site job discovery and extraction adapter."""

import logging
from typing import Optional
from sqlalchemy.orm import Session

from app.models.job_source_adapter import (
    JobSourceAdapter,
    DiscoveredJobUrl,
    NormalizedJobOffer,
)
from app.services.career_page_crawler import CareerPageCrawler, CrawlerConfig
from app.services.job_candidate_detector import JobCandidateDetector
from app.services.job_offer_extractor import JobOfferExtractor
from app.services.url_normalizer import normalize_url
from app.database.models import Company

logger = logging.getLogger(__name__)


class CareerSiteAdapter(JobSourceAdapter):
    """Discover and extract jobs from company career websites.

    Strategy:
    1. Discover career site URL for company
    2. Crawl pages (HTTP + Playwright fallback)
    3. Detect probable job pages (deterministic scoring)
    4. Extract job details (deterministic + fallback)
    5. Normalize to canonical schema
    """

    source_name = "career_site"
    collection_strategy = "crawl"

    def __init__(self, db: Session = None, crawler_config: CrawlerConfig = None):
        """Initialize adapter.

        Args:
            db: Database session (used for company lookup)
            crawler_config: Career page crawler config
        """
        self.db = db
        self.crawler_config = crawler_config or CrawlerConfig()
        self.detector = JobCandidateDetector()
        self.extractor = JobOfferExtractor()

    async def discover_jobs(self, context: dict) -> list[DiscoveredJobUrl]:
        """Discover job URLs from company career site.

        Context args:
            company_id: Company ID to look up
            OR
            career_site_url: Direct career site URL

        Returns:
            List of DiscoveredJobUrl
        """
        # Resolve career site URL
        career_url = context.get("career_site_url")

        if not career_url and "company_id" in context:
            if self.db:
                company = self.db.query(Company).filter(
                    Company.id == context["company_id"]
                ).first()
                if company:
                    career_url = company.career_site_url
                else:
                    raise ValueError(f"Company not found: {context['company_id']}")
            else:
                raise ValueError("DB session required for company lookup")

        if not career_url:
            raise ValueError("No career_site_url provided or found")

        logger.info(f"Discovering jobs from: {career_url}")

        discovered = []
        crawler = CareerPageCrawler(career_url, self.crawler_config)

        try:
            async for page_url, html, title in crawler.crawl():
                # Score as job candidate
                result = self.detector.score(page_url, html, title)

                if result["is_candidate"]:
                    discovered.append(
                        DiscoveredJobUrl(
                            url=page_url,
                            metadata={
                                "title": title,
                                "signals": result["signals"],
                                "score": result["score"],
                            },
                        )
                    )

                logger.debug(
                    f"Score {result['score']}: {page_url[:60]} - "
                    f"{'CANDIDATE' if result['is_candidate'] else 'ignored'}"
                )

        except Exception as e:
            logger.error(f"Crawl error: {e}")
            raise

        logger.info(f"Discovered {len(discovered)} job candidates")
        return discovered

    async def extract_job(self, discovered: DiscoveredJobUrl) -> dict:
        """Extract structured job data from discovered URL.

        Uses deterministic extraction first, falls back to Playwright
        if initial HTML doesn't expose job content.
        """
        url = discovered.url

        # Fetch page (simple HTTP first)
        crawler = CareerPageCrawler(url, self.crawler_config)
        try:
            await crawler.initialize()
            html, title = await crawler.fetch_page(url, use_playwright=False)
        except Exception as e:
            logger.warning(f"HTTP fetch failed, trying Playwright: {e}")
            try:
                html, title = await crawler.fetch_page(url, use_playwright=True)
            except Exception as e2:
                logger.error(f"Both HTTP and Playwright failed: {e2}")
                raise
        finally:
            await crawler.close()

        # Extract using deterministic methods
        extracted = self.extractor.extract(html, url)
        extracted["source_url"] = url

        return extracted

    async def normalize_job(self, extracted: dict) -> NormalizedJobOffer:
        """Normalize extracted data to canonical schema."""
        return NormalizedJobOffer(
            job_title=extracted.get("title") or "Unknown Position",
            company_name=extracted.get("company_name") or "Unknown",
            job_url=extracted.get("source_url") or extracted.get("url"),
            source=self.source_name,
            location=extracted.get("location"),
            contract_type=extracted.get("contract_type"),
            posted_date=extracted.get("posted_date"),
            raw_text=extracted.get("description"),
            external_job_id=extracted.get("external_job_id"),
            required_skills=extracted.get("skills"),
            description=extracted.get("description"),
        )

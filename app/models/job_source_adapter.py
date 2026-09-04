"""Phase 2B: Source-agnostic job ingestion adapters."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class DiscoveredJobUrl:
    """A URL discovered as potential job posting."""
    url: str
    metadata: dict  # Optional context from discovery (title, snippet, etc.)


@dataclass
class NormalizedJobOffer:
    """Canonical job offer format produced by all adapters."""
    job_title: str
    company_name: str
    job_url: str
    source: str  # adapter name: career_site, indeed, apec, etc.
    location: Optional[str] = None
    contract_type: Optional[str] = None
    posted_date: Optional[str] = None
    raw_text: Optional[str] = None
    external_job_id: Optional[str] = None
    required_skills: Optional[list] = None
    description: Optional[str] = None


class JobSourceAdapter(ABC):
    """Base class for all job source adapters.

    Each adapter encapsulates the strategy for discovering, extracting,
    and normalizing job offers from a specific source.
    """

    source_name: str  # e.g., "career_site", "indeed", "apec"
    collection_strategy: str  # e.g., "crawl", "api", "feed", "search"

    @abstractmethod
    async def discover_jobs(self, context: dict) -> list[DiscoveredJobUrl]:
        """Discover job URLs from this source.

        Args:
            context: Adapter-specific discovery context
                     (e.g., company_id, search_terms, etc.)

        Returns:
            List of DiscoveredJobUrl with metadata

        Raises:
            May raise on access control, network, or source-specific errors.
            Errors should be logged; caller handles retry/fallback.
        """
        pass

    @abstractmethod
    async def extract_job(self, discovered: DiscoveredJobUrl) -> dict:
        """Extract structured job data from a discovered URL.

        Args:
            discovered: DiscoveredJobUrl object

        Returns:
            Dict with keys: title, location, description, contract_type,
            external_job_id, skills, posted_date, etc.

        Note:
            Extraction may use deterministic parsing, structured data,
            or ScrapeGraphAI fallback. Implementation decides.
        """
        pass

    @abstractmethod
    async def normalize_job(self, extracted: dict) -> NormalizedJobOffer:
        """Normalize extracted data to canonical JobOffer schema.

        Args:
            extracted: Dict from extract_job()

        Returns:
            NormalizedJobOffer instance
        """
        pass

    async def process_discovered_job(
        self,
        discovered: DiscoveredJobUrl
    ) -> NormalizedJobOffer:
        """Complete pipeline: extract + normalize.

        Convenience method combining extract_job + normalize_job.
        """
        extracted = await self.extract_job(discovered)
        return await self.normalize_job(extracted)

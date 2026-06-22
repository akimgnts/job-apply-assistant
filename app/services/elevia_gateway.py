import logging
from typing import Optional, Dict, Any, List
from app.services.elevia_client import EleviaClient
from app.schemas.elevia_offer import (
    EleviaOfferCatalogEntry,
    EleviaOfferDetail,
    EleviaProfile,
    EleviaMatchContext,
    EleviaIntegrationContext,
)

logger = logging.getLogger(__name__)


class EleviaGateway:
    """Orchestration layer for Elevia API integration."""

    def __init__(self, client: EleviaClient):
        self.client = client

    async def search_offers(
        self,
        query: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 10,
    ) -> List[EleviaOfferCatalogEntry]:
        """Search offers and return normalized entries."""
        try:
            response = await self.client.search_offers(query=query, filters=filters, limit=limit)
            offers = response.get("offers", [])
            return [self._normalize_catalog_entry(offer) for offer in offers]
        except Exception as e:
            logger.error(f"Gateway search offers failed: {e}")
            raise

    async def get_catalog(
        self,
        skip: int = 0,
        limit: int = 50,
    ) -> List[EleviaOfferCatalogEntry]:
        """Get catalog and return normalized entries."""
        try:
            response = await self.client.get_offers_catalog(skip=skip, limit=limit)
            offers = response.get("offers", [])
            return [self._normalize_catalog_entry(offer) for offer in offers]
        except Exception as e:
            logger.error(f"Gateway catalog fetch failed: {e}")
            raise

    async def get_offer_with_context(
        self,
        offer_id: str,
        profile_id: Optional[str] = None,
    ) -> EleviaIntegrationContext:
        """Get complete offer context for application."""
        context = EleviaIntegrationContext(source_offer_id=offer_id)

        try:
            # Fetch offer detail
            offer_data = await self.client.get_offer_detail(offer_id)
            context.offer_detail = self._normalize_offer_detail(offer_data)

            # Optionally fetch profile
            if profile_id:
                try:
                    profile_data = await self.client.get_profile(profile_id)
                    context.profile = self._normalize_profile(profile_data)

                    # Try to get matching context
                    try:
                        match_data = await self.client.match_profile_with_offer(
                            profile_id=profile_id,
                            offer_id=offer_id,
                        )
                        context.matching_context = self._normalize_match_context(match_data)
                    except Exception as e:
                        logger.warning(f"Matching failed (non-critical): {e}")

                except Exception as e:
                    logger.warning(f"Profile fetch failed (non-critical): {e}")

            return context

        except Exception as e:
            logger.error(f"Gateway get offer with context failed: {e}")
            raise

    async def parse_profile_from_file(
        self,
        file_content: bytes,
        filename: str,
    ) -> EleviaProfile:
        """Parse and upload profile file."""
        try:
            response = await self.client.upload_profile(file_content, filename)
            return self._normalize_profile(response)
        except Exception as e:
            logger.error(f"Gateway parse profile failed: {e}")
            raise

    async def get_profile(self, profile_id: str) -> EleviaProfile:
        """Get profile by ID."""
        try:
            response = await self.client.get_profile(profile_id)
            return self._normalize_profile(response)
        except Exception as e:
            logger.error(f"Gateway get profile failed: {e}")
            raise

    @staticmethod
    def _normalize_catalog_entry(data: Dict[str, Any]) -> EleviaOfferCatalogEntry:
        """Normalize raw API offer catalog entry."""
        return EleviaOfferCatalogEntry(
            offer_id=data.get("id", data.get("offer_id", "")),
            title=data.get("title", data.get("job_title", "")),
            company=data.get("company", "")),
            location=data.get("location", data.get("country", "")),
            description=data.get("description", data.get("summary", "")),
            contract_type=data.get("contract_type", data.get("type", None)),
            mission_duration=data.get("mission_duration", data.get("duration", None)),
        )

    @staticmethod
    def _normalize_offer_detail(data: Dict[str, Any]) -> EleviaOfferDetail:
        """Normalize raw API offer detail."""
        return EleviaOfferDetail(
            offer_id=data.get("id", data.get("offer_id", "")),
            title=data.get("title", data.get("job_title", "")),
            company=data.get("company", ""),
            location=data.get("location", data.get("country", "")),
            description=data.get("description", data.get("summary", "")),
            full_text=data.get("full_text", data.get("content", "")),
            contract_type=data.get("contract_type", data.get("type", None)),
            mission_duration=data.get("mission_duration", data.get("duration", None)),
            required_skills=data.get("required_skills", data.get("skills", [])),
            soft_skills=data.get("soft_skills", []),
            salary_range=data.get("salary_range", None),
            ats_keywords=data.get("ats_keywords", []),
            raw_data=data,
        )

    @staticmethod
    def _normalize_profile(data: Dict[str, Any]) -> EleviaProfile:
        """Normalize raw API profile."""
        return EleviaProfile(
            profile_id=data.get("id", data.get("profile_id", "")),
            name=data.get("name", data.get("full_name", None)),
            email=data.get("email", None),
            phone=data.get("phone", None),
            location=data.get("location", data.get("country", None)),
            skills=data.get("skills", []),
            experience=data.get("experience", data.get("experiences", [])),
            education=data.get("education", data.get("educations", [])),
            certifications=data.get("certifications", []),
            raw_data=data,
        )

    @staticmethod
    def _normalize_match_context(data: Dict[str, Any]) -> EleviaMatchContext:
        """Normalize raw API matching response."""
        return EleviaMatchContext(
            match_score=data.get("score", data.get("match_score", None)),
            matching_skills=data.get("matching_skills", []),
            missing_skills=data.get("missing_skills", []),
            strengths=data.get("strengths", []),
            recommendations=data.get("recommendations", []),
            raw_data=data,
        )

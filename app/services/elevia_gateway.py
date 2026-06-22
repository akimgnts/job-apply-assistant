import logging
from typing import Optional, Dict, Any, List
from app.services.elevia_client import EleviaClient

logger = logging.getLogger(__name__)


class EleviaOfferContext:
    """Normalized internal object for Elevia offer context."""

    def __init__(
        self,
        source_offer_id: str,
        source_type: str = "business_france",
        offer_catalog_entry: Optional[Dict[str, Any]] = None,
        offer_detail: Optional[Dict[str, Any]] = None,
        profile: Optional[Dict[str, Any]] = None,
        matching_context: Optional[Dict[str, Any]] = None,
    ):
        self.source = "elevia"
        self.source_offer_id = source_offer_id
        self.source_type = source_type
        self.offer_catalog_entry = offer_catalog_entry or {}
        self.offer_detail = offer_detail or {}
        self.profile = profile or {}
        self.matching_context = matching_context or {}

    def get_job_title(self) -> str:
        """Extract job title from offer."""
        return (
            self.offer_detail.get("title")
            or self.offer_catalog_entry.get("title")
            or "Unknown Position"
        )

    def get_company(self) -> str:
        """Extract company name."""
        return (
            self.offer_detail.get("company")
            or self.offer_catalog_entry.get("company")
            or "Unknown Company"
        )

    def get_location(self) -> str:
        """Extract location."""
        detail_loc = self.offer_detail.get("location")
        if detail_loc:
            return detail_loc

        catalog_city = self.offer_catalog_entry.get("city")
        catalog_country = self.offer_catalog_entry.get("country")
        if catalog_city:
            return f"{catalog_city}, {catalog_country}" if catalog_country else catalog_city
        return "Unknown Location"

    def get_description(self) -> str:
        """Extract full description."""
        return (
            self.offer_detail.get("description")
            or self.offer_detail.get("raw_description")
            or self.offer_catalog_entry.get("description")
            or self.offer_catalog_entry.get("display_description")
            or ""
        )

    def get_required_skills(self) -> List[str]:
        """Extract required skills."""
        return self.offer_detail.get("required_skills", [])

    def get_soft_skills(self) -> List[str]:
        """Extract soft skills."""
        return self.offer_detail.get("soft_skills", [])

    def get_ats_keywords(self) -> List[str]:
        """Extract ATS keywords."""
        return self.offer_detail.get("ats_keywords", [])

    def get_match_score(self) -> Optional[float]:
        """Extract matching score if available."""
        return self.matching_context.get("score")

    def get_matching_explanation(self) -> str:
        """Extract matching explanation."""
        return self.matching_context.get("explanation", "")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for serialization."""
        return {
            "source": self.source,
            "source_offer_id": self.source_offer_id,
            "source_type": self.source_type,
            "offer_catalog_entry": self.offer_catalog_entry,
            "offer_detail": self.offer_detail,
            "profile": self.profile,
            "matching_context": self.matching_context,
        }


class EleviaGateway:
    """Orchestration layer for Elevia integration."""

    def __init__(self, client: Optional[EleviaClient] = None):
        self.client = client or EleviaClient()

    async def health_check(self) -> bool:
        """Check if Elevia is available."""
        return await self.client.health()

    async def search_offers(
        self,
        query: Optional[str] = None,
        limit: int = 50,
        source: str = "all",
    ) -> List[Dict[str, Any]]:
        """Search offers from catalog."""
        logger.info("[ELEVIA_GATEWAY] Searching offers: query=%s, limit=%d", query, limit)

        resp = await self.client.get_catalog(limit=limit, source=source)

        if "error" in resp:
            logger.warning("[ELEVIA_GATEWAY] Catalog error: %s", resp.get("error"))
            return []

        offers = resp.get("offers", [])
        logger.info("[ELEVIA_GATEWAY] Found %d offers", len(offers))
        return offers

    async def get_offer_context(
        self,
        offer_id: str,
        profile_id: Optional[str] = None,
    ) -> Optional[EleviaOfferContext]:
        """Load complete offer context."""
        logger.info("[ELEVIA_GATEWAY] Loading offer: %s, profile_id=%s", offer_id, profile_id)

        # Get offer detail
        detail_resp = await self.client.get_offer_detail(offer_id)
        if "error" in detail_resp:
            logger.error("[ELEVIA_GATEWAY] Failed to load offer detail: %s", detail_resp.get("error"))
            return None

        # Get matching context if profile available
        matching_context = {}
        if profile_id:
            match_resp = await self.client.match(profile_id=profile_id, offer_id=offer_id)
            if "error" not in match_resp:
                matching_context = match_resp

        # Get profile if available
        profile = {}
        if profile_id:
            profile_resp = await self.client.get_profile(profile_id)
            if "error" not in profile_resp:
                profile = profile_resp

        context = EleviaOfferContext(
            source_offer_id=offer_id,
            source_type=detail_resp.get("source", "business_france"),
            offer_detail=detail_resp,
            profile=profile,
            matching_context=matching_context,
        )

        logger.info("[ELEVIA_GATEWAY] Offer context loaded: %s", context.get_job_title())
        return context

    async def get_ranked_offers(
        self,
        profile_id: str,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Get ranked offers for profile from inbox."""
        logger.info("[ELEVIA_GATEWAY] Loading inbox for profile: %s", profile_id)

        resp = await self.client.get_inbox(profile_id=profile_id, limit=limit)

        if "error" in resp:
            logger.warning("[ELEVIA_GATEWAY] Inbox error: %s", resp.get("error"))
            # Fallback to catalog
            logger.info("[ELEVIA_GATEWAY] Falling back to catalog")
            return await self.search_offers(limit=limit)

        offers = resp.get("offers", [])
        logger.info("[ELEVIA_GATEWAY] Loaded %d ranked offers", len(offers))
        return offers

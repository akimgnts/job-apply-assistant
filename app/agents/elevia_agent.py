import logging
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from app.services.elevia_client import EleviaClient
from app.services.elevia_gateway import EleviaGateway
from app.services.elevia_user_service import EleviaUserService
from app.schemas.elevia_offer import (
    EleviaIntegrationContext,
    EleviaOfferCatalogEntry,
)
from app.config import config

logger = logging.getLogger(__name__)


class EleviaAgent:
    """Agent for Elevia offers integration."""

    _client: Optional[EleviaClient] = None
    _gateway: Optional[EleviaGateway] = None

    @classmethod
    def _get_gateway(cls) -> Optional[EleviaGateway]:
        """Lazy-load Elevia gateway."""
        if not config.ELEVIA_ENABLED:
            logger.debug("Elevia is disabled")
            return None

        if cls._gateway is None:
            cls._client = EleviaClient(
                base_url=config.ELEVIA_BASE_URL,
                api_key=config.ELEVIA_API_KEY if config.ELEVIA_API_KEY else None,
            )
            cls._gateway = EleviaGateway(cls._client)

        return cls._gateway

    @classmethod
    async def health_check(cls) -> bool:
        """Check Elevia API health."""
        gateway = cls._get_gateway()
        if not gateway:
            return False
        try:
            return await gateway.client.health_check()
        except Exception as e:
            logger.error(f"Elevia health check error: {e}")
            return False

    @classmethod
    async def search_offers(
        cls,
        query: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 10,
    ) -> Optional[List[EleviaOfferCatalogEntry]]:
        """Search Elevia offers."""
        gateway = cls._get_gateway()
        if not gateway:
            return None
        try:
            return await gateway.search_offers(query=query, filters=filters, limit=limit)
        except Exception as e:
            logger.error(f"Elevia search error: {e}")
            return None

    @classmethod
    async def get_catalog(
        cls,
        skip: int = 0,
        limit: int = 50,
    ) -> Optional[List[EleviaOfferCatalogEntry]]:
        """Get Elevia offers catalog."""
        gateway = cls._get_gateway()
        if not gateway:
            return None
        try:
            return await gateway.get_catalog(skip=skip, limit=limit)
        except Exception as e:
            logger.error(f"Elevia catalog error: {e}")
            return None

    @classmethod
    async def get_offer_with_context(
        cls,
        offer_id: str,
        db: Session,
        telegram_user_id: str,
    ) -> Optional[EleviaIntegrationContext]:
        """Get Elevia offer with full context (including profile if available)."""
        gateway = cls._get_gateway()
        if not gateway:
            return None

        try:
            # Get stored Elevia profile ID
            profile_id = EleviaUserService.get_elevia_profile_id(db, telegram_user_id)

            # Load offer with context
            context = await gateway.get_offer_with_context(
                offer_id=offer_id,
                profile_id=profile_id,
            )

            # Store last accessed offer ID
            EleviaUserService.set_last_elevia_offer_id(db, telegram_user_id, offer_id)

            return context

        except Exception as e:
            logger.error(f"Elevia get offer with context error: {e}")
            return None

    @classmethod
    async def upload_profile_from_file(
        cls,
        file_content: bytes,
        filename: str,
        db: Session,
        telegram_user_id: str,
    ) -> Optional[str]:
        """Upload and store user profile in Elevia."""
        gateway = cls._get_gateway()
        if not gateway:
            return None

        try:
            profile = await gateway.parse_profile_from_file(file_content, filename)
            if profile and profile.profile_id:
                EleviaUserService.set_elevia_profile_id(db, telegram_user_id, profile.profile_id)
                logger.info(f"User {telegram_user_id} profile stored: {profile.profile_id}")
                return profile.profile_id
            return None
        except Exception as e:
            logger.error(f"Elevia profile upload error: {e}")
            return None

    @classmethod
    async def get_user_profile(
        cls,
        db: Session,
        telegram_user_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Get user's stored Elevia profile."""
        gateway = cls._get_gateway()
        if not gateway:
            return None

        try:
            profile_id = EleviaUserService.get_elevia_profile_id(db, telegram_user_id)
            if not profile_id:
                return None

            profile = await gateway.get_profile(profile_id)
            return profile.to_dict() if profile else None

        except Exception as e:
            if "404" in str(e).lower():
                logger.warning(f"Elevia profile {profile_id} not found, clearing local cache")
                EleviaUserService.clear_elevia_profile_id(db, telegram_user_id)
            else:
                logger.error(f"Elevia get profile error: {e}")
            return None

    @classmethod
    def is_enabled(cls) -> bool:
        """Check if Elevia is enabled."""
        return config.ELEVIA_ENABLED

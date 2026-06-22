import logging
import httpx
from typing import Optional, Dict, Any
from app.config import config

logger = logging.getLogger(__name__)


class EleviaClient:
    """HTTP client for Elevia API."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout_ms: int = 20000,
    ):
        self.base_url = base_url or config.ELEVIA_BASE_URL
        self.api_key = api_key or config.ELEVIA_API_KEY
        self.timeout = timeout_ms / 1000.0
        self.enabled = config.ELEVIA_ENABLED

    async def health(self) -> bool:
        """Check if Elevia API is healthy."""
        if not self.enabled:
            logger.warning("[ELEVIA] Integration disabled")
            return False

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(f"{self.base_url}/api/health")
                return resp.status_code == 200
        except Exception as e:
            logger.error("[ELEVIA] Health check failed: %s", str(e))
            return False

    async def get_catalog(
        self,
        limit: int = 50,
        source: str = "all",
    ) -> Dict[str, Any]:
        """Get offer catalog."""
        if not self.enabled:
            return {"error": "ELEVIA_DISABLED", "offers": []}

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(
                    f"{self.base_url}/api/offers/catalog",
                    params={"limit": limit, "source": source},
                )
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPStatusError as e:
            logger.error("[ELEVIA] Catalog error %d: %s", e.response.status_code, e)
            return {"error": f"HTTP_{e.response.status_code}", "offers": []}
        except Exception as e:
            logger.error("[ELEVIA] Catalog request failed: %s", str(e))
            return {"error": str(e), "offers": []}

    async def get_offer_detail(
        self,
        offer_id: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Get detailed offer information."""
        if not self.enabled:
            return {"error": "ELEVIA_DISABLED"}

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(
                    f"{self.base_url}/api/offers/{offer_id}/detail",
                    params=context or {},
                )
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPStatusError as e:
            logger.error(
                "[ELEVIA] Offer detail error %d for %s: %s",
                e.response.status_code,
                offer_id,
                e,
            )
            return {"error": f"HTTP_{e.response.status_code}"}
        except Exception as e:
            logger.error("[ELEVIA] Offer detail request failed: %s", str(e))
            return {"error": str(e)}

    async def get_inbox(
        self,
        profile_id: str,
        limit: int = 20,
    ) -> Dict[str, Any]:
        """Get ranked offers for profile."""
        if not self.enabled:
            return {"error": "ELEVIA_DISABLED", "offers": []}

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    f"{self.base_url}/api/inbox",
                    json={"profile_id": profile_id, "limit": limit},
                )
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPStatusError as e:
            logger.error("[ELEVIA] Inbox error %d: %s", e.response.status_code, e)
            return {"error": f"HTTP_{e.response.status_code}", "offers": []}
        except Exception as e:
            logger.error("[ELEVIA] Inbox request failed: %s", str(e))
            return {"error": str(e), "offers": []}

    async def get_profile(self, profile_id: str) -> Dict[str, Any]:
        """Get persisted profile."""
        if not self.enabled:
            return {"error": "ELEVIA_DISABLED"}

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(f"{self.base_url}/api/profiles/{profile_id}")
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning("[ELEVIA] Profile not found: %s", profile_id)
                return {"error": "PROFILE_NOT_FOUND"}
            logger.error("[ELEVIA] Profile error %d: %s", e.response.status_code, e)
            return {"error": f"HTTP_{e.response.status_code}"}
        except Exception as e:
            logger.error("[ELEVIA] Profile request failed: %s", str(e))
            return {"error": str(e)}

    async def match(
        self,
        profile_id: str,
        offer_id: str,
    ) -> Dict[str, Any]:
        """Get matching score and explanation."""
        if not self.enabled:
            return {"error": "ELEVIA_DISABLED"}

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    f"{self.base_url}/api/v1/match",
                    json={"profile_id": profile_id, "offer_id": offer_id},
                )
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPStatusError as e:
            logger.error("[ELEVIA] Match error %d: %s", e.response.status_code, e)
            return {"error": f"HTTP_{e.response.status_code}"}
        except Exception as e:
            logger.error("[ELEVIA] Match request failed: %s", str(e))
            return {"error": str(e)}

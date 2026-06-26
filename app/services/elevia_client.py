import logging
import asyncio
from typing import Optional, Dict, Any, List
import httpx

logger = logging.getLogger(__name__)


class EleviaClient:
    """HTTP client for Elevia API."""

    def __init__(self, base_url: str, api_key: Optional[str] = None):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.headers = {}
        if api_key:
            self.headers["Authorization"] = f"Bearer {api_key}"
        self.headers["Content-Type"] = "application/json"

    async def health_check(self) -> bool:
        """Check if Elevia API is healthy."""
        try:
            async with httpx.AsyncClient(timeout=5, follow_redirects=True) as client:
                response = await client.get(
                    f"{self.base_url}/api/health",
                    headers=self.headers,
                )
                return response.status_code == 200
        except Exception as e:
            logger.warning(f"Elevia health check failed: {e}")
            return False

    async def get_ingestion_status(self) -> Dict[str, Any]:
        """Get latest ingestion run metadata."""
        try:
            async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
                response = await client.get(
                    f"{self.base_url}/api/ingestion/latest",
                    headers=self.headers,
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Elevia ingestion status failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Elevia ingestion status error: {e}")
            raise

    async def get_offers_catalog(
        self,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """Get recent active offers."""
        try:
            async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
                response = await client.get(
                    f"{self.base_url}/api/offers/recent",
                    params={"limit": limit},
                    headers=self.headers,
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Elevia catalog fetch failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Elevia catalog error: {e}")
            raise

    async def get_offer_detail(self, offer_id: str) -> Dict[str, Any]:
        """Get detailed information about a specific offer."""
        try:
            async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
                response = await client.get(
                    f"{self.base_url}/api/offers/{offer_id}",
                    headers=self.headers,
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"Offer {offer_id} not found")
            else:
                logger.error(f"Elevia get offer detail failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Elevia get offer detail error: {e}")
            raise

    async def upload_profile(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        """Upload and parse a profile file."""
        try:
            async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
                files = {"file": (filename, file_content)}
                response = await client.post(
                    f"{self.base_url}/api/profile/parse-file",
                    files=files,
                    headers={k: v for k, v in self.headers.items() if k != "Content-Type"},
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Elevia profile upload failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Elevia profile upload error: {e}")
            raise

    async def get_profile(self, profile_id: str) -> Dict[str, Any]:
        """Get profile information by ID."""
        try:
            async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
                response = await client.get(
                    f"{self.base_url}/api/profiles/{profile_id}",
                    headers=self.headers,
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"Profile {profile_id} not found")
            else:
                logger.error(f"Elevia get profile failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Elevia get profile error: {e}")
            raise

    async def match_profile_with_offer(
        self,
        profile_id: str,
        offer_id: str,
    ) -> Dict[str, Any]:
        """Match a profile with an offer (optional endpoint)."""
        try:
            payload = {
                "profile_id": profile_id,
                "offer_id": offer_id,
            }
            async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
                response = await client.post(
                    f"{self.base_url}/api/v1/match",
                    json=payload,
                    headers=self.headers,
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Elevia match failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Elevia match error: {e}")
            raise

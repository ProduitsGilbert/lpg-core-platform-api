"""
Pallet route status client for Fastems1 Autopilot.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import logging

import httpx

from app.settings import settings

logger = logging.getLogger(__name__)


class FastemsPalletRouteClient:
    """Wrapper around the dy_pallet_routes endpoint."""

    def __init__(self, base_url: Optional[str] = None, timeout: float = 10.0) -> None:
        self._base_url = (base_url or settings.fastems1_pallet_route_api_base_url or "").rstrip("/")
        self._timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self._base_url or "",
                timeout=self._timeout,
                headers={"Accept": "application/json"},
                verify=False,
            )
        return self._client

    async def aclose(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    async def list_routes(self) -> List[Dict[str, Any]]:
        if not self._base_url:
            logger.warning("Pallet route API base URL is missing")
            return []
        resource = "/dy_pallet_routes"
        try:
            response = await self.client.get(resource)
            response.raise_for_status()
            data = response.json()
            if isinstance(data, list):
                return data
            logger.warning("Unexpected pallet route payload type: %s", type(data))
            return []
        except httpx.HTTPStatusError as exc:
            logger.error(
                "Pallet route API HTTP error",
                extra={"status_code": exc.response.status_code if exc.response else None},
            )
            return []
        except httpx.RequestError as exc:
            logger.error("Pallet route API request failed: %s", exc)
            return []

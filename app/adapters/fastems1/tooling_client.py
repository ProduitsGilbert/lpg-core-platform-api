"""
CNCTooling client for Fastems1 Autopilot.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import logging

import httpx

from app.settings import settings

logger = logging.getLogger(__name__)


class FastemsToolingClient:
    """Simple wrapper around the CNCTooling API."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        requester_id: Optional[str] = None,
        timeout: float = 15.0,
    ) -> None:
        self._base_url = (base_url or settings.fastems1_tooling_api_base_url or "").rstrip("/")
        self._requester_id = requester_id or settings.fastems1_production_requester_id
        self._timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            headers = {"Accept": "application/json"}
            if self._requester_id:
                headers["RequesterUserID"] = self._requester_id
            self._client = httpx.AsyncClient(
                base_url=self._base_url or "",
                timeout=self._timeout,
                headers=headers,
                verify=False,
            )
        return self._client

    async def aclose(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    async def list_machine_tools(self, machine_id: int) -> List[Dict[str, Any]]:
        """
        Return tool inventory for a specific machine (DMC).
        """
        if not self._base_url:
            logger.warning("Fastems tooling API base URL is not configured")
            return []

        resource = f"/CNCTooling/MachineTools?machineId={machine_id}"
        try:
            response = await self.client.get(resource)
            response.raise_for_status()
            data = response.json()
            if isinstance(data, list):
                return data
            logger.warning(
                "Unexpected payload from CNCTooling API",
                extra={"resource": resource, "payload_type": type(data)},
            )
            return []
        except httpx.HTTPStatusError as exc:
            logger.error(
                "CNCTooling API HTTP error",
                extra={"status_code": exc.response.status_code if exc.response else None},
            )
            return []
        except httpx.RequestError as exc:
            logger.error("CNCTooling API request error: %s", exc)
            return []

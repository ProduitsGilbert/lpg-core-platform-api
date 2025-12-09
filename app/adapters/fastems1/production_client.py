"""
HTTP client for Fastems1 production / work-order APIs.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import logging

import httpx

from app.settings import settings

logger = logging.getLogger(__name__)


class FastemsProductionClient:
    """
    Thin wrapper around the Gilbert Tech production API used to retrieve
    unfinished routing lines (work orders + operations).
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        requester_id: Optional[str] = None,
        timeout: float = 30.0,
    ) -> None:
        self._base_url = (base_url or settings.fastems1_production_api_base_url or "").rstrip("/")
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

    async def _get(self, resource: str, timeout: Optional[float] = None) -> List[Dict[str, Any]]:
        if not self._base_url:
            logger.warning("Fastems production API base URL is not configured")
            return []
        try:
            response = await self.client.get(resource, timeout=timeout or self._timeout)
            response.raise_for_status()
            data = response.json()
            if isinstance(data, list):
                return data
            if isinstance(data, dict) and "value" in data:
                value = data.get("value")
                if isinstance(value, list):
                    return value
            logger.warning(
                "Unexpected payload from Fastems production API",
                extra={"resource": resource, "payload_type": type(data)},
            )
            return []
        except httpx.HTTPStatusError as exc:
            logger.error(
                "Fastems production API HTTP error",
                extra={"status_code": exc.response.status_code if exc.response else None},
            )
            return []
        except httpx.RequestError as exc:
            logger.error("Fastems production API request error: %s", exc)
            return []

    async def list_ready_routing_lines(
        self,
        work_center_no: str = "40253",
    ) -> List[Dict[str, Any]]:
        """
        Return routing lines that are scheduled/ready for the provided work center.
        """
        resource = (
            f"/ProductionOrder/"
            f"InScheduleProductionOrderRoutingLine({work_center_no})"
        )
        result = await self._get(resource, timeout=60.0)
        if result:
            return result
        # Fallback to unfinished list if schedule-specific endpoint returns nothing
        return await self.list_unfinished_routing_lines(work_center_no)

    async def list_unfinished_routing_lines(
        self,
        work_center_no: str = "40253",
    ) -> List[Dict[str, Any]]:
        """
        Return unfinished routing lines for the provided work center.
        """
        resource = (
            f"/ProductionOrder/"
            f"AllUnfinishedProductionOrderRoutingLine({work_center_no})"
        )
        return await self._get(resource)

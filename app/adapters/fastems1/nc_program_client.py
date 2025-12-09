"""
NC program metadata client for Fastems1 Autopilot.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import logging

import httpx

from app.settings import settings

logger = logging.getLogger(__name__)


class FastemsNCProgramClient:
    """Retrieves tool requirements per NC program."""

    def __init__(self, base_url: Optional[str] = None, timeout: float = 15.0) -> None:
        self._base_url = (base_url or settings.fastems1_nc_program_tool_base_url or "").rstrip("/")
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

    async def get_program_tools(self, program_name: str) -> List[Dict[str, Any]]:
        if not self._base_url:
            logger.warning("NC program tool API base URL is not configured")
            return []

        resource = f"/nc_program_tools/{program_name}"
        try:
            response = await self.client.get(resource)
            response.raise_for_status()
            data = response.json()
            if isinstance(data, list):
                return data
            logger.warning(
                "Unexpected payload from NC program tool API",
                extra={"resource": resource, "payload_type": type(data)},
            )
            return []
        except httpx.HTTPStatusError as exc:
            logger.error(
                "NC program tool API HTTP error",
                extra={"status_code": exc.response.status_code if exc.response else None},
            )
            return []
        except httpx.RequestError as exc:
            logger.error("NC program tool API request error: %s", exc)
            return []

"""Async ClickUp API client adapter."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import httpx
import logfire

from app.settings import settings
from app.errors import BaseAPIException


class ClickUpError(BaseAPIException):
    """ClickUp API error."""
    pass


class ClickUpUnauthorized(ClickUpError):
    """ClickUp authentication error."""
    pass


class ClickUpNotFound(ClickUpError):
    """ClickUp resource not found."""
    pass


class ClickUpRateLimited(ClickUpError):
    """ClickUp rate limit exceeded."""
    pass


class ClickUpConfigurationError(ClickUpError):
    """ClickUp configuration error."""
    pass


class ClickUpClient:
    """Async client for the ClickUp REST API."""

    def __init__(self) -> None:
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self) -> "ClickUpClient":
        if not settings.clickup_api_key:
            raise ClickUpConfigurationError("ClickUp API key is not configured")

        headers = {
            "Authorization": settings.clickup_api_key,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        timeout = settings.request_timeout if settings.request_timeout else 60
        self._client = httpx.AsyncClient(
            base_url=settings.clickup_api_base_url,
            headers=headers,
            timeout=httpx.Timeout(timeout, connect=10),
            follow_redirects=True,
        )
        return self

    async def __aexit__(self, exc_type, exc, exc_tb) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    @property
    def client(self) -> httpx.AsyncClient:
        if not self._client:
            raise RuntimeError("ClickUpClient used outside of an async context manager")
        return self._client

    async def _request(self, method: str, path: str, **kwargs) -> Dict[str, Any]:
        url = path if path.startswith("http") else f"/{path.lstrip('/')}"
        with logfire.span("clickup.request", method=method, url=url):
            try:
                response = await self.client.request(method, url, **kwargs)
            except httpx.TimeoutException as exc:
                logger = logging.getLogger(__name__)
                logger.error("ClickUp API request timed out", extra={"method": method, "url": url})
                raise ClickUpError("ClickUp API request timed out") from exc
            except httpx.RequestError as exc:
                logger = logging.getLogger(__name__)
                logger.error("ClickUp API request failed", extra={"method": method, "url": url, "error": str(exc)})
                raise ClickUpError("ClickUp API request failed", context={"url": url}) from exc

            if response.status_code == 401:
                raise ClickUpUnauthorized()
            if response.status_code == 404:
                raise ClickUpNotFound("ClickUp resource", url)
            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After")
                retry_seconds = int(retry_after) if retry_after and retry_after.isdigit() else None
                raise ClickUpRateLimited(retry_after=retry_seconds)

            if response.status_code >= 400:
                try:
                    payload = response.json()
                except ValueError:
                    payload = {"body": response.text}
                logger = logging.getLogger(__name__)
                logger.error(
                    "ClickUp API error",
                    extra={
                        "status": response.status_code,
                        "url": url,
                        "method": method,
                        "payload": payload,
                    },
                )
                raise ClickUpError(
                    detail=f"ClickUp API error {response.status_code}",
                    context={"url": url, "method": method, "response": payload},
                )

            if response.status_code == 204:
                return {}

            content_type = response.headers.get("Content-Type", "")
            if "application/json" in content_type:
                return response.json()

            # Fallback: try json, otherwise return metadata
            try:
                return response.json()
            except ValueError:
                return {"content": response.content}

    async def get_lists_in_folder(self, folder_id: str) -> List[Dict[str, Any]]:
        """Get all lists in a specific folder."""
        response = await self._request("GET", f"/folder/{folder_id}/list")
        return response.get("lists", [])

    async def get_tasks_in_list(
        self,
        list_id: str,
        include_closed: bool = False,
        page: Optional[int] = None,
        archived: bool = False
    ) -> Dict[str, Any]:
        """Get tasks from a specific list."""
        params = {
            "include_closed": str(include_closed).lower(),
            "archived": str(archived).lower(),
        }
        if page:
            params["page"] = str(page)

        return await self._request("GET", f"/list/{list_id}/task", params=params)

    async def get_task(self, task_id: str) -> Dict[str, Any]:
        """Get a specific task by ID."""
        return await self._request("GET", f"/task/{task_id}")

    async def get_folder(self, folder_id: str) -> Dict[str, Any]:
        """Get folder information."""
        return await self._request("GET", f"/folder/{folder_id}")

    async def get_list(self, list_id: str) -> Dict[str, Any]:
        """Get list information."""
        return await self._request("GET", f"/list/{list_id}")


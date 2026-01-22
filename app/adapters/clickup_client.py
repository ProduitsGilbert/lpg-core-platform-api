"""Async ClickUp API client adapter."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import httpx
import logfire
from fastapi import status

from app.settings import settings
from app.errors import BaseAPIException


class ClickUpError(BaseAPIException):
    """ClickUp API error."""

    def __init__(self, detail: str, status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR, context: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status_code,
            detail=detail,
            error_code="CLICKUP_ERROR",
            context=context
        )


class ClickUpUnauthorized(ClickUpError):
    """ClickUp authentication error."""

    def __init__(self, detail: str = "ClickUp authentication failed", context: Optional[Dict[str, Any]] = None):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_401_UNAUTHORIZED,
            context=context
        )


class ClickUpNotFound(ClickUpError):
    """ClickUp resource not found."""

    def __init__(self, resource: str, resource_id: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(
            detail=f"ClickUp {resource} '{resource_id}' not found",
            status_code=status.HTTP_404_NOT_FOUND,
            context=context
        )


class ClickUpRateLimited(ClickUpError):
    """ClickUp rate limit exceeded."""

    def __init__(self, retry_after: Optional[int] = None, context: Optional[Dict[str, Any]] = None):
        detail = "ClickUp API rate limit exceeded"
        if retry_after:
            detail += f". Retry after {retry_after} seconds"

        super().__init__(
            detail=detail,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            context=context
        )


class ClickUpConfigurationError(ClickUpError):
    """ClickUp configuration error."""

    def __init__(self, detail: str = "ClickUp is not properly configured", context: Optional[Dict[str, Any]] = None):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            context=context
        )


class ClickUpClient:
    """Async client for the ClickUp REST API."""

    def __init__(self) -> None:
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self) -> "ClickUpClient":
        # Try access token first, then fall back to API key
        token = settings.clickup_access_token or settings.clickup_api_key
        if not token:
            raise ClickUpConfigurationError("ClickUp API key or access token is not configured")

        headers = {
            "Authorization": f"Bearer {token}",
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
        params = {}
        if include_closed:
            params["include_closed"] = str(include_closed).lower()
        if archived:
            params["archived"] = str(archived).lower()
        if page is not None:
            # ClickUp uses 0-based pagination, so convert from 1-based
            clickup_page = max(0, page - 1) if page > 0 else 0
            params["page"] = str(clickup_page)

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

    async def get_folders_in_space(self, space_id: str) -> List[Dict[str, Any]]:
        """Get all folders in a specific space."""
        response = await self._request("GET", f"/space/{space_id}/folder")
        return response.get("folders", [])

    async def get_lists_in_space(self, space_id: str) -> List[Dict[str, Any]]:
        """Get all folderless lists in a specific space."""
        response = await self._request("GET", f"/space/{space_id}/list")
        return response.get("lists", [])



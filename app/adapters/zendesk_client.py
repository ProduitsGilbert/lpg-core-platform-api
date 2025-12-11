"""Async Zendesk API client adapter."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import httpx
import logfire

from app.settings import settings
from app.errors import BaseAPIException


class ZendeskError(BaseAPIException):
    """Zendesk API error."""
    pass


class ZendeskUnauthorized(ZendeskError):
    """Zendesk authentication error."""
    pass


class ZendeskNotFound(ZendeskError):
    """Zendesk resource not found."""
    pass


class ZendeskRateLimited(ZendeskError):
    """Zendesk rate limit exceeded."""
    pass


class ZendeskConfigurationError(ZendeskError):
    """Zendesk configuration error."""
    pass


class ZendeskClient:
    """Async client for the Zendesk REST API."""

    def __init__(self) -> None:
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self) -> "ZendeskClient":
        if not settings.zendesk_api_key or not settings.zendesk_username:
            raise ZendeskConfigurationError("Zendesk API key and username are not configured")

        headers = {
            "Authorization": f"Bearer {settings.zendesk_api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        self._client = httpx.AsyncClient(
            base_url=f"https://{settings.zendesk_subdomain}.zendesk.com/api/v2",
            headers=headers,
            timeout=30.0,
        )

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    def _handle_error(self, response: httpx.Response) -> None:
        """Handle HTTP errors and raise appropriate exceptions."""
        if response.status_code == 401:
            raise ZendeskUnauthorized(f"Authentication failed: {response.text}")
        elif response.status_code == 403:
            raise ZendeskUnauthorized(f"Access forbidden: {response.text}")
        elif response.status_code == 404:
            raise ZendeskNotFound(f"Resource not found: {response.text}")
        elif response.status_code == 429:
            raise ZendeskRateLimited(f"Rate limit exceeded: {response.text}")
        elif response.status_code >= 400:
            raise ZendeskError(f"Zendesk API error ({response.status_code}): {response.text}")

    async def _get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make a GET request to the Zendesk API."""
        if not self._client:
            raise ZendeskError("Client not initialized")

        with logfire.span("zendesk_get", endpoint=endpoint, params=params):
            response = await self._client.get(endpoint, params=params)
            self._handle_error(response)
            return response.json()

    async def search_tickets(
        self,
        query: str,
        page: Optional[int] = None,
        per_page: Optional[int] = None
    ) -> Dict[str, Any]:
        """Search for tickets using Zendesk search API."""
        params = {"query": query}
        if page:
            params["page"] = page
        if per_page:
            params["per_page"] = per_page

        return await self._get("/search.json", params=params)

    async def list_tickets(
        self,
        status: Optional[str] = None,
        page: Optional[int] = None,
        per_page: Optional[int] = None,
        sort_by: Optional[str] = None,
        sort_order: Optional[str] = None
    ) -> Dict[str, Any]:
        """List tickets with optional filtering."""
        params = {}
        if status:
            params["status"] = status
        if page:
            params["page"] = page
        if per_page:
            params["per_page"] = per_page
        if sort_by:
            params["sort_by"] = sort_by
        if sort_order:
            params["sort_order"] = sort_order

        return await self._get("/tickets.json", params=params)

    async def get_ticket(self, ticket_id: int) -> Dict[str, Any]:
        """Get a specific ticket by ID."""
        return await self._get(f"/tickets/{ticket_id}.json")

    async def export_search_results(
        self,
        query: str,
        page_size: Optional[int] = None,
        after_cursor: Optional[str] = None
    ) -> Dict[str, Any]:
        """Export search results using cursor-based pagination."""
        params = {"query": query, "filter[type]": "ticket"}
        if page_size:
            params["page[size]"] = page_size
        if after_cursor:
            params["page[after]"] = after_cursor

        return await self._get("/search/export.json", params=params)


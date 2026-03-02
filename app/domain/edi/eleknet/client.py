"""Async HTTP client for ElekNet requests."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx

from app.settings import settings

from .errors import (
    ElekNetConfigurationError,
    ElekNetGatewayError,
    ElekNetTimeoutError,
    ElekNetUpstreamError,
)


class ElekNetClient:
    """Client responsible for sending XML payloads to ElekNet."""

    def __init__(
        self,
        *,
        base_url: str | None = None,
        xpa_url: str | None = None,
        order_url: str | None = None,
        username: str | None = None,
        password: str | None = None,
        timeout_s: int | None = None,
        verify_tls: bool | None = None,
        max_network_retries: int | None = None,
        async_client: httpx.AsyncClient | None = None,
    ):
        self.base_url = (base_url if base_url is not None else settings.eleknet_base_url) or ""
        self.xpa_url = (xpa_url if xpa_url is not None else settings.eleknet_xpa_url) or ""
        self.order_url = (order_url if order_url is not None else settings.eleknet_order_url) or ""
        self.username = username if username is not None else settings.eleknet_username
        self.password = password if password is not None else settings.eleknet_password
        self.timeout_s = timeout_s if timeout_s is not None else settings.eleknet_timeout_s
        self.verify_tls = verify_tls if verify_tls is not None else settings.eleknet_verify_tls
        self.max_network_retries = (
            max_network_retries
            if max_network_retries is not None
            else settings.eleknet_max_network_retries
        )
        self._async_client = async_client

    async def post_xpa(self, xml_payload: str) -> str:
        """Send xPA XML to ElekNet."""
        return await self._post_form("xPA", xml_payload)

    async def post_order(self, xml_payload: str) -> str:
        """Send order XML to ElekNet."""
        return await self._post_form("xmlOrder", xml_payload)

    def _ensure_configured(self) -> None:
        missing_fields = []
        if not (
            self.base_url.strip()
            or self.xpa_url.strip()
            or self.order_url.strip()
        ):
            missing_fields.append("ELEKNET_BASE_URL")
        if not (self.username or "").strip():
            missing_fields.append("ELEKNET_USERNAME")
        if not (self.password or "").strip():
            missing_fields.append("ELEKNET_PASSWORD")
        if missing_fields:
            raise ElekNetConfigurationError(
                f"Missing ElekNet settings: {', '.join(missing_fields)}"
            )

    async def _post_form(self, field_name: str, xml_payload: str) -> str:
        self._ensure_configured()
        target_url = self._resolve_target_url(field_name)
        if not target_url:
            raise ElekNetConfigurationError(
                "Missing ElekNet endpoint URL for request type "
                f"{field_name}. Configure ELEKNET_BASE_URL or specific endpoint URLs."
            )
        retries = max(0, int(self.max_network_retries))

        for attempt in range(retries + 1):
            try:
                async with self._get_client() as client:
                    response = await client.post(
                        target_url,
                        data={field_name: xml_payload},
                        headers={"Content-Type": "application/x-www-form-urlencoded"},
                    )
            except httpx.TimeoutException as exc:
                if attempt < retries:
                    await asyncio.sleep(0.2)
                    continue
                raise ElekNetTimeoutError("ElekNet request timed out") from exc
            except httpx.RequestError as exc:
                if attempt < retries:
                    await asyncio.sleep(0.2)
                    continue
                raise ElekNetGatewayError(
                    f"Could not connect to ElekNet endpoint {target_url}"
                ) from exc

            if response.status_code >= 400:
                raise ElekNetUpstreamError(
                    f"ElekNet HTTP error {response.status_code}: {response.text[:300]}"
                )

            return response.text

        raise ElekNetGatewayError("Failed to complete ElekNet request")

    def _resolve_target_url(self, field_name: str) -> str:
        if field_name == "xPA":
            return (self.xpa_url.strip() or self.base_url.strip())
        if field_name == "xmlOrder":
            return (self.order_url.strip() or self.base_url.strip())
        return self.base_url.strip()

    @asynccontextmanager
    async def _get_client(self) -> AsyncIterator[httpx.AsyncClient]:
        if self._async_client is not None:
            yield self._async_client
            return

        async with httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout_s),
            verify=self.verify_tls,
        ) as client:
            yield client

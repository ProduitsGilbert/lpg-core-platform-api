"""Async Front API client adapter."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, Optional

import httpx
import logfire

from app.settings import settings
from app.errors import (
    CommunicationsError,
    CommunicationsUnauthorized,
    CommunicationsNotFound,
    CommunicationsRateLimited,
    CommunicationsConfigurationError,
)
from app.ports import FrontClientProtocol

logger = logging.getLogger(__name__)


class FrontClient(FrontClientProtocol):
    """Async client for the Front REST API."""

    def __init__(self) -> None:
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self) -> "FrontClient":
        if not settings.front_api_key:
            raise CommunicationsConfigurationError("Front API key is not configured")

        headers = {
            "Authorization": f"Bearer {settings.front_api_key}",
            "Accept": "application/json",
        }

        timeout = settings.request_timeout if settings.request_timeout else 60
        self._client = httpx.AsyncClient(
            base_url=settings.front_api_base_url,
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
            raise RuntimeError("FrontClient used outside of an async context manager")
        return self._client

    async def _request(self, method: str, path: str, **kwargs) -> Dict[str, Any]:
        url = path if path.startswith("http") else f"/{path.lstrip('/')}"
        with logfire.span("front.request", method=method, url=url):
            try:
                response = await self.client.request(method, url, **kwargs)
            except httpx.TimeoutException as exc:
                logger.error("Front API request timed out", extra={"method": method, "url": url})
                raise CommunicationsError("Front API request timed out") from exc
            except httpx.RequestError as exc:
                logger.error("Front API request failed", extra={"method": method, "url": url, "error": str(exc)})
                raise CommunicationsError("Front API request failed", context={"url": url}) from exc

            if response.status_code == 401:
                raise CommunicationsUnauthorized()
            if response.status_code == 404:
                raise CommunicationsNotFound("Front resource", url)
            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After")
                retry_seconds = int(retry_after) if retry_after and retry_after.isdigit() else None
                raise CommunicationsRateLimited(retry_after=retry_seconds)

            if response.status_code >= 400:
                try:
                    payload = response.json()
                except ValueError:
                    payload = {"body": response.text}
                logger.error(
                    "Front API error",
                    extra={
                        "status": response.status_code,
                        "url": url,
                        "method": method,
                        "payload": payload,
                    },
                )
                raise CommunicationsError(
                    detail=f"Front API error {response.status_code}",
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

    async def get_conversation(self, conversation_id: str) -> Dict[str, Any]:
        return await self._request("GET", f"/conversations/{conversation_id}")

    async def get_conversation_messages(
        self, conversation_id: str, page: Optional[str] = None
    ) -> Dict[str, Any]:
        path = page or f"/conversations/{conversation_id}/messages"
        return await self._request("GET", path)

    async def get_conversation_comments(self, conversation_id: str) -> Dict[str, Any]:
        return await self._request("GET", f"/conversations/{conversation_id}/comments")

    async def create_comment(
        self, conversation_id: str, body: str, author_id: Optional[str] = None
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"body": body}
        if author_id:
            payload["author_id"] = author_id
        return await self._request(
            "POST", f"/conversations/{conversation_id}/comments", json=payload
        )

    async def send_conversation_reply(
        self, conversation_id: str, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        return await self._request(
            "POST", f"/conversations/{conversation_id}/messages", json=payload
        )

    async def archive_conversation(self, conversation_id: str) -> Dict[str, Any]:
        return await self._request("POST", f"/conversations/{conversation_id}/archive")

    async def snooze_conversation(
        self, conversation_id: str, snooze_until: datetime
    ) -> Dict[str, Any]:
        payload = {"snooze_until": int(snooze_until.timestamp())}
        return await self._request(
            "POST", f"/conversations/{conversation_id}/snooze", json=payload
        )

    async def get_message(self, message_id: str) -> Dict[str, Any]:
        return await self._request("GET", f"/messages/{message_id}")

    async def download_attachment(self, attachment_id: str) -> bytes:
        url = f"/download/{attachment_id}"
        with logfire.span("front.download_attachment", attachment_id=attachment_id):
            try:
                response = await self.client.get(url)
            except httpx.TimeoutException as exc:
                raise CommunicationsError("Attachment download timed out") from exc
            except httpx.RequestError as exc:
                raise CommunicationsError("Attachment download failed") from exc

            if response.status_code == 401:
                raise CommunicationsUnauthorized()
            if response.status_code == 404:
                raise CommunicationsNotFound("Attachment", attachment_id)
            if response.status_code >= 400:
                raise CommunicationsError(
                    detail=f"Front download error {response.status_code}",
                    context={"attachment_id": attachment_id},
                )
            return response.content

"""File Share service for document management."""

from __future__ import annotations

import logging
from typing import Dict, Optional

import httpx
import logfire

from app.settings import settings

logger = logging.getLogger(__name__)


class FileShareService:
    """Service for interacting with the Gilbert Tech file share API."""

    def __init__(self) -> None:
        self._base_url = settings.file_share_base_url.rstrip("/")
        self._requester_id = (
            settings.file_share_requester_id
            or settings.bc_api_username
            or "system"
        )

    async def get_item_pdf(self, item_no: str) -> Optional[Dict[str, object]]:
        """Retrieve the PDF documentation for a specific item."""
        url = f"{self._base_url}/FileShare/GetItemPDFFile({item_no})"
        headers = {
            "accept": "*/*",
            "RequesterUserID": self._requester_id,
        }

        with logfire.span("file_share.get_item_pdf", item_no=item_no, url=url):
            try:
                async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
                    response = await client.get(url, headers=headers)

                if response.status_code == 404:
                    logger.info("Item PDF not found", extra={"item_no": item_no})
                    return None

                response.raise_for_status()

                filename = self._extract_filename(response.headers) or f"{item_no}.pdf"
                content_type = response.headers.get("Content-Type", "application/pdf")
                content = response.content

                logfire.info(
                    "Retrieved item PDF from file share",
                    item_no=item_no,
                    filename=filename,
                    size=len(content),
                )

                return {
                    "content": content,
                    "filename": filename,
                    "size": len(content),
                    "content_type": content_type,
                    "metadata": {
                        "item_no": item_no,
                        "source": "file_share_api",
                        "requester": self._requester_id,
                    },
                }

            except httpx.HTTPStatusError as exc:
                status_code = exc.response.status_code if exc.response else None
                logger.error(
                    "File share API returned error",
                    extra={
                        "item_no": item_no,
                        "status_code": status_code,
                        "body": exc.response.text[:500] if exc.response else None,
                    },
                )
                raise
            except Exception as exc:
                logger.error("Error retrieving item PDF", exc_info=exc)
                raise

    @staticmethod
    def _extract_filename(headers: httpx.Headers) -> Optional[str]:
        disposition = headers.get("Content-Disposition")
        if not disposition:
            return None

        parts = [part.strip() for part in disposition.split(";")]
        for part in parts:
            if part.lower().startswith("filename="):
                value = part.split("=", 1)[1]
                return value.strip('"')
        return None

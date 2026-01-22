"""Service for retrieving Business Central OData collections."""

from __future__ import annotations

from contextlib import contextmanager
import base64
import logging
from typing import Any, Dict, List, Optional, Union

import httpx
import logfire

from app.settings import settings

logger = logging.getLogger(__name__)

FilterValue = Union[str, int, float, bool]


@contextmanager
def _maybe_logfire_span(name: str, **kwargs):
    if settings.logfire_api_key:
        with logfire.span(name, **kwargs):
            yield
    else:
        yield


class BusinessCentralODataService:
    """Lightweight wrapper around Business Central OData endpoints."""

    def __init__(self) -> None:
        base_url = (settings.erp_base_url or "").strip()
        if not base_url:
            raise ValueError("ERP_BASE_URL is not configured.")

        if not base_url.endswith("/"):
            base_url = f"{base_url}/"

        self._base_url = base_url
        self._headers = self._build_headers()

    async def fetch_collection(
        self,
        resource: str,
        *,
        filter_field: Optional[str] = None,
        filter_value: Optional[FilterValue] = None,
        top: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve an OData collection from Business Central.

        Args:
            resource: OData collection name (e.g., 'PostedSalesInvoiceHeaders').
            filter_field: Optional field to filter with equality.
            filter_value: Value to compare against using OData eq operator. Supports str, int, float, or bool.
            top: Optional number of records to return (`$top`).

        Returns:
            List of dictionaries representing collection entries.
        """
        params: Dict[str, str] = {}

        if filter_field and filter_value is not None:
            if isinstance(filter_value, str):
                sanitized_value = filter_value.replace("'", "''")
                params["$filter"] = f"{filter_field} eq '{sanitized_value}'"
            elif isinstance(filter_value, bool):
                params["$filter"] = f"{filter_field} eq {'true' if filter_value else 'false'}"
            else:
                params["$filter"] = f"{filter_field} eq {filter_value}"

        if top is not None:
            params["$top"] = str(top)

        url_path = resource.lstrip("/")

        with _maybe_logfire_span(
            "bc_odata.fetch_collection",
            resource=url_path,
            filter_field=filter_field,
            has_filter=bool(filter_value),
            top=top,
        ):
            async with httpx.AsyncClient(
                base_url=self._base_url,
                headers=self._headers,
                timeout=settings.request_timeout,
                verify=False,
            ) as client:
                response = await client.get(url_path, params=params or None)
                response.raise_for_status()
                payload = response.json()

        values = payload.get("value")
        if not isinstance(values, list):
            logger.warning(
                "Unexpected Business Central payload",
                extra={"resource": resource, "payload_type": type(payload)},
            )
            return []

        return values

    async def fetch_collection_paged(
        self,
        resource: str,
        *,
        filter_field: Optional[str] = None,
        filter_value: Optional[FilterValue] = None,
        top: Optional[int] = None,
        max_pages: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve all pages for an OData collection.

        Uses @odata.nextLink when present to continue fetching.
        """
        params: Dict[str, str] = {}

        if filter_field and filter_value is not None:
            if isinstance(filter_value, str):
                sanitized_value = filter_value.replace("'", "''")
                params["$filter"] = f"{filter_field} eq '{sanitized_value}'"
            elif isinstance(filter_value, bool):
                params["$filter"] = f"{filter_field} eq {'true' if filter_value else 'false'}"
            else:
                params["$filter"] = f"{filter_field} eq {filter_value}"

        if top is not None:
            params["$top"] = str(top)

        url_path: Optional[str] = resource.lstrip("/")
        next_params: Optional[Dict[str, str]] = params or None
        results: List[Dict[str, Any]] = []

        with _maybe_logfire_span(
            "bc_odata.fetch_collection_paged",
            resource=url_path,
            filter_field=filter_field,
            has_filter=bool(filter_value),
            top=top,
        ):
            async with httpx.AsyncClient(
                base_url=self._base_url,
                headers=self._headers,
                timeout=settings.request_timeout,
                verify=False,
            ) as client:
                pages = 0
                while url_path and pages < max_pages:
                    response = await client.get(url_path, params=next_params)
                    response.raise_for_status()
                    payload = response.json()
                    values = payload.get("value")
                    if isinstance(values, list):
                        results.extend(values)
                    next_link = payload.get("@odata.nextLink") or payload.get("odata.nextLink")
                    if not next_link:
                        break
                    url_path = next_link
                    next_params = None
                    pages += 1

        return results

    @staticmethod
    def _build_headers() -> Dict[str, str]:
        """Construct authorization headers for Business Central."""
        if not settings.bc_api_username or not settings.bc_api_password:
            raise ValueError("BC_API_USERNAME or BC_API_PASSWORD is not configured.")

        auth = f"{settings.bc_api_username}:{settings.bc_api_password}"
        token = base64.b64encode(auth.encode("utf-8")).decode("utf-8")
        return {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Basic {token}",
        }

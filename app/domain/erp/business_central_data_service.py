"""Service for retrieving Business Central OData collections."""

from __future__ import annotations

import base64
import logging
from typing import Any, Dict, List, Optional

import httpx
import logfire

from app.settings import settings

logger = logging.getLogger(__name__)


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
        filter_value: Optional[str] = None,
        top: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve an OData collection from Business Central.

        Args:
            resource: OData collection name (e.g., 'PostedSalesInvoiceHeaders').
            filter_field: Optional field to filter with equality.
            filter_value: Value to compare against using OData eq operator.
            top: Optional number of records to return (`$top`).

        Returns:
            List of dictionaries representing collection entries.
        """
        params: Dict[str, str] = {}

        if filter_field and filter_value:
            sanitized_value = filter_value.replace("'", "''")
            params["$filter"] = f"{filter_field} eq '{sanitized_value}'"

        if top is not None:
            params["$top"] = str(top)

        url_path = resource.lstrip("/")

        with logfire.span(
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

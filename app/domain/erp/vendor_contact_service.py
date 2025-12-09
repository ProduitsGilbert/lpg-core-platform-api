"""Business Central vendor contact lookup service."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

import httpx
import logfire

from app.domain.erp.business_central_data_service import BusinessCentralODataService
from app.settings import settings

DEFAULT_VENDOR_EMAIL = "achat@gilbert-tech.com"
_WAJAX_VENDOR_CODE = "WAJIN01"
_WAJAX_EMAIL = "qc600ventes@wajax.com"
_WAJAX_NAME = "WAJAX"


@dataclass
class VendorContactInfo:
    """Normalized vendor contact response."""

    vendor_id: str
    email: str
    language: str
    language_code: Optional[str]
    name: str
    communication_language: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert dataclass to dict for API responses."""
        return {
            "vendor_id": self.vendor_id,
            "email": self.email,
            "language": self.language,
            "language_code": self.language_code,
            "name": self.name,
            "communication_language": self.communication_language,
        }


class VendorContactService:
    """Service responsible for retrieving vendor email contact information."""

    def __init__(self, odata_service: BusinessCentralODataService) -> None:
        self._odata_service = odata_service
        explorer_base = (settings.bc_explorer_api_base_url or "").strip()
        if not explorer_base:
            raise ValueError("BC_EXPLORER_API_BASE_URL is not configured.")
        if not explorer_base.endswith("/"):
            explorer_base = f"{explorer_base}/"
        self._explorer_base_url = explorer_base
        self._headers = BusinessCentralODataService._build_headers()
        self._headers.setdefault("company", "Gilbert-tech")

    async def get_vendor_contact(self, vendor_no: str) -> VendorContactInfo:
        """Return vendor email contact info with default fallbacks."""
        normalized_vendor = _normalize_vendor_code(vendor_no)
        if not normalized_vendor:
            raise ValueError("vendor_no must be provided.")

        email = DEFAULT_VENDOR_EMAIL
        language = "French"
        language_code: Optional[str] = None
        name = ""

        with logfire.span("vendor_contact.lookup", vendor=normalized_vendor):
            if normalized_vendor == _WAJAX_VENDOR_CODE:
                email = _WAJAX_EMAIL
                name = _WAJAX_NAME
            else:
                lookup_email = await self._fetch_vendor_email(normalized_vendor)
                if lookup_email:
                    email = lookup_email

            vendor_info = await self._fetch_vendor_metadata(normalized_vendor)
            if vendor_info:
                language, language_code = _normalize_vendor_language(vendor_info.get("Language_Code"))
                name = vendor_info.get("Name") or name

        return VendorContactInfo(
            vendor_id=normalized_vendor,
            email=email,
            language=language,
            language_code=language_code,
            name=name,
            communication_language=language,
        )

    async def _fetch_vendor_email(self, vendor_no: str) -> Optional[str]:
        """Call easyPDFAddress endpoint to retrieve vendor email."""
        filter_expr = (
            "ownerNo eq '{vendor}' and addressType eq 'To' and documentCode eq 'PURCHASE ORDER'"
        ).format(vendor=_escape_odata_literal(vendor_no))

        async with httpx.AsyncClient(
            base_url=self._explorer_base_url,
            headers=self._headers,
            timeout=settings.request_timeout,
            verify=False,
        ) as client:
            response = await client.get("easyPDFAddress", params={"$filter": filter_expr, "$top": "1"})
            response.raise_for_status()
            payload = response.json()

        values = payload.get("value")
        if isinstance(values, list) and values:
            address = values[0].get("address")
            if isinstance(address, str) and address.strip():
                return address.strip()
        return None

    async def _fetch_vendor_metadata(self, vendor_no: str) -> Optional[Dict[str, Any]]:
        """Fetch vendor language and name from Business Central vendor table."""
        records = await self._odata_service.fetch_collection(
            "Vendor",
            filter_field="No",
            filter_value=vendor_no,
            top=1,
        )
        if records:
            return records[0]
        return None


def _normalize_vendor_code(vendor: str) -> str:
    """Trim and uppercase vendor codes."""
    return (vendor or "").strip().upper()


def _escape_odata_literal(value: str) -> str:
    """Escape single quotes for safe OData filters."""
    return value.replace("'", "''")


def _normalize_vendor_language(code: Optional[str]) -> Tuple[str, Optional[str]]:
    """Map BC language codes to friendly names."""
    if not code:
        return "French", None

    normalized = code.strip().upper()
    french_codes = {"FR", "FRA", "FR-CA", "FRCA", "FRANCAIS"}
    if normalized in french_codes:
        return "French", normalized
    return "English", normalized

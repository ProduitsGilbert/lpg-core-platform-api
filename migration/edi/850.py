"""Utilities to generate an EDI 850 document."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Iterable, Mapping, Optional

import logfire

try:  # pragma: no cover - legacy dependency not available in tests
    from data import BC  # type: ignore
except ImportError:  # pragma: no cover - expected in modern deployment
    BC = None

# The legacy script reconfigured logfire on import which interferes with the
# application-wide configuration. We now assume logfire is configured by the app.


def _coerce_decimal(value: object, default: Decimal = Decimal("0")) -> Decimal:
    """Convert raw values from ERP to Decimal with safe fallbacks."""
    if value is None:
        return default
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return default


def _sanitize_text(value: Optional[str]) -> str:
    """Ensure text segments are ASCII-safe and stripped."""
    if not value:
        return ""
    normalized = " ".join(value.strip().split())
    try:
        return normalized.encode("ascii", "ignore").decode("ascii")
    except UnicodeEncodeError:  # pragma: no cover - ignore non-ascii
        return normalized


def _format_date(value: Optional[str]) -> str:
    """Format ERP ISO date values to CCYYMMDD as required by the partner."""
    if not value:
        return ""

    # Dates may come as YYYY-MM-DD or full ISO timestamps. Handle both.
    try:
        if len(value) >= 10:
            parsed = datetime.fromisoformat(value[:19]) if "T" in value else datetime.strptime(value[:10], "%Y-%m-%d")
        else:
            parsed = datetime.strptime(value, "%Y%m%d")
        return parsed.strftime("%Y%m%d")
    except ValueError:
        return value.replace("-", "")


def build_edi_850_document(
    po_number: str,
    po_header: Mapping[str, object],
    po_lines: Iterable[Mapping[str, object]],
    vendor_info: Mapping[str, object],
    *,
    sender_id: str = "GILBERTTECHP",
) -> str:
    """Build an EDI 850 document from ERP purchase order data."""

    if not po_number:
        raise ValueError("A PO number is required to build an EDI 850 document")

    formatted_date = _format_date(str(po_header.get("Document_Date") or po_header.get("orderDate") or ""))
    vendor_code = _sanitize_text(str(po_header.get("Buy_from_Vendor_No") or vendor_info.get("No") or ""))

    if not vendor_code:
        raise ValueError("Vendor code is required to generate an EDI 850 document")

    total_excl_tax = _coerce_decimal(po_header.get("Amount") or po_header.get("Amount_Excl_VAT"))
    total_incl_tax = _coerce_decimal(po_header.get("Amount_Including_VAT"))
    tax_total = (total_incl_tax - total_excl_tax).quantize(Decimal("0.01")) if total_incl_tax else Decimal("0.00")

    identification = f"ID|850|{sender_id}|{vendor_code}|\n"
    header = f"HEAD|||{formatted_date}|{po_number}|00|NE|\n"

    address_ship_to = (
        "ADDR_TYPE|ST|PRODUITS GILBERT INC.|\n"
        "ADDR|1840 Boul Marcotte|\n"
        "LOCATION|Roberval|QC|G8H 2P2|\n"
    )

    address_bill_to = (
        f"ADDR_TYPE|BT|{_sanitize_text(str(vendor_info.get('Name') or ''))}|\n"
        f"ADDR|{_sanitize_text(str(vendor_info.get('Address') or ''))}|\n"
        f"LOCATION|{_sanitize_text(str(vendor_info.get('City') or ''))}|"
        f"{_sanitize_text(str(vendor_info.get('County') or vendor_info.get('State') or ''))}|"
        f"{_sanitize_text(str(vendor_info.get('Post_Code') or vendor_info.get('Zip') or ''))}|\n"
    )

    terms = "TERMS_GEN|RT|\n"
    doc_date = f"DATE|DR|{formatted_date}|\n"
    ship_terms = "FOB|PP|ZZ|SHIPPING POINT|\n"

    details_segments: list[str] = []
    for idx, line in enumerate(po_lines, start=1):
        quantity = _coerce_decimal(line.get("Quantity")).normalize()
        unit_of_measure = _sanitize_text(str(line.get("Unit_of_Measure_Code") or "EA"))
        unit_cost = _coerce_decimal(line.get("Direct_Unit_Cost")).quantize(Decimal("0.0001"))
        vendor_item = _sanitize_text(str(line.get("Vendor_Item_No") or ""))
        buyer_item = _sanitize_text(str(line.get("No") or ""))
        description = _sanitize_text(str(line.get("Description") or ""))

        details_segments.append(
            "|".join(
                [
                    "ITEM",
                    str(idx),
                    f"{quantity}",
                    unit_of_measure,
                    f"{unit_cost}",
                    "VN",
                    vendor_item,
                    "",
                    "",
                    "BP",
                    buyer_item,
                    "",
                ]
            )
            + "\n"
        )
        if description:
            details_segments.append(f"DESC|{description}|\n")

    footer = (
        f"TOTAL|TT|{total_incl_tax.quantize(Decimal('0.01'))}|{total_excl_tax.quantize(Decimal('0.01'))}|\n"
        f"TOTAL_TAX|GST|{tax_total}|\n"
    )

    edi_document = (
        identification
        + header
        + address_ship_to
        + address_bill_to
        + terms
        + doc_date
        + ship_terms
        + "".join(details_segments)
        + footer
    )

    return edi_document


def generate_edi_850(po_number: str, *, sender_id: str = "GILBERTTECHP") -> str:
    """
    Legacy helper that fetches PO data via the legacy data module when available.

    Modern code paths should prefer :func:`build_edi_850_document` with explicit
    data. This function remains for backwards compatibility with existing
    scripts that still rely on the historical interface.
    """

    if BC is None:
        raise RuntimeError("Legacy data module 'data.BC' is not available")

    po_header = BC.get_PO_headers_edi(po_number)
    po_details = BC.get_PO_lines_edi_direct(po_number)

    if not po_header or "value" not in po_header or not po_header["value"]:
        logfire.error(f"PO header not found for {po_number}")
        raise ValueError(f"Purchase Order {po_number} header not found in Business Central")

    if not po_details or "value" not in po_details or not po_details["value"]:
        logfire.error(f"PO lines not found for {po_number}")
        raise ValueError(f"Purchase Order {po_number} lines not found in Business Central")

    vendor_info = BC.get_Vendor_info(po_header["value"][0]["Buy_from_Vendor_No"])
    if not vendor_info or "value" not in vendor_info or not vendor_info["value"]:
        logfire.error(f"Vendor info not found for PO {po_number}")
        raise ValueError(f"Vendor information not found for Purchase Order {po_number}")

    return build_edi_850_document(
        po_number,
        po_header["value"][0],
        po_details["value"],
        vendor_info["value"][0],
        sender_id=sender_id,
    )

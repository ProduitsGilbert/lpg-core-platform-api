"""Utilities to generate the supplier's legacy pipe-delimited EDI 850 document."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Iterable, Mapping, Optional, Sequence

import logfire

try:  # pragma: no cover - legacy dependency not available in tests
    from data import BC  # type: ignore
except ImportError:  # pragma: no cover - expected in modern deployment
    BC = None

DEFAULT_SENDER_ID = "GILBERTTECHP"
DEFAULT_TERMS_CODE = "RT"
DEFAULT_FOB_CODE = "PP"
DEFAULT_FOB_DESCRIPTION = "SHIPPING POINT"
DEFAULT_SHIP_TO = {
    "name": "PRODUITS GILBERT INC.",
    "address_lines": ["1840 Boul Marcotte"],
    "city": "Roberval",
    "state": "QC",
    "postal": "G8H 2P2",
    "country": "CA",
}


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
    """Format ISO-like dates to CCYYMMDD with graceful fallback."""

    if not value:
        return ""

    stripped = value.strip()
    if not stripped:
        return ""

    # Common Business Central formats are "YYYY-MM-DD" or full timestamps.
    if len(stripped) >= 10:
        digits = stripped.replace("-", "").replace(":", "").replace("T", "")
        return digits[:8]

    return stripped.replace("-", "")[:8]


def _format_decimal(value: Decimal, *, precision: str = "0.01") -> str:
    """Render Decimal values with the requested precision."""

    try:
        quantized = value.quantize(Decimal(precision))
    except (InvalidOperation, ValueError):
        return str(value)
    return str(quantized)


def _address_lines_from_vendor(vendor_info: Mapping[str, object]) -> Sequence[str]:
    lines: list[str] = []
    for key in ("Address", "Address_2", "Address2", "Address_3", "Address3"):
        raw = vendor_info.get(key)
        parts = _sanitize_text(str(raw)) if raw else ""
        if parts:
            lines.append(parts)
    return lines or [DEFAULT_SHIP_TO["address_lines"][0]]


def _extract_vendor_location(vendor_info: Mapping[str, object]) -> tuple[str, str, str]:
    city = _sanitize_text(str(vendor_info.get("City") or ""))
    state = _sanitize_text(
        str(
            vendor_info.get("County")
            or vendor_info.get("State")
            or vendor_info.get("State_Code")
            or ""
        )
    )
    postal = _sanitize_text(
        str(
            vendor_info.get("Post_Code")
            or vendor_info.get("Zip")
            or vendor_info.get("ZipCode")
            or ""
        )
    )
    return city, state, postal


def _extract_ship_to_segments(po_header: Mapping[str, object]) -> list[str]:
    """Build the ship-to address block segments."""

    name = _sanitize_text(
        str(
            po_header.get("Ship_to_Name")
            or po_header.get("Ship_to_Name_2")
            or DEFAULT_SHIP_TO["name"]
        )
    )

    address_candidates = [
        _sanitize_text(str(po_header.get("Ship_to_Address") or "")),
        _sanitize_text(str(po_header.get("Ship_to_Address_2") or "")),
        _sanitize_text(str(po_header.get("Ship_to_Address_3") or "")),
    ]
    address_lines = [line for line in address_candidates if line]
    if not address_lines:
        address_lines = list(DEFAULT_SHIP_TO["address_lines"])

    city = _sanitize_text(
        str(
            po_header.get("Ship_to_City")
            or po_header.get("Sell_to_City")
            or DEFAULT_SHIP_TO["city"]
        )
    )
    state = _sanitize_text(
        str(
            po_header.get("Ship_to_County")
            or po_header.get("Ship_to_State")
            or po_header.get("Ship_to_State_Code")
            or po_header.get("Sell_to_State")
            or DEFAULT_SHIP_TO["state"]
        )
    )
    postal = _sanitize_text(
        str(
            po_header.get("Ship_to_Post_Code")
            or po_header.get("Sell_to_Post_Code")
            or DEFAULT_SHIP_TO["postal"]
        )
    )

    segments: list[str] = [f"ADDR_TYPE|ST|{name}|"]
    for line in address_lines:
        segments.append(f"ADDR|{line}|")
    segments.append(f"LOCATION|{city}|{state}|{postal}|")
    return segments


def _extract_bill_to_segments(vendor_info: Mapping[str, object]) -> list[str]:
    """Build the bill-to address block segments using vendor data."""

    name = _sanitize_text(str(vendor_info.get("Name") or vendor_info.get("DisplayName") or ""))
    address_lines = list(_address_lines_from_vendor(vendor_info))
    city, state, postal = _extract_vendor_location(vendor_info)

    segments: list[str] = [f"ADDR_TYPE|BT|{name}|"]
    for line in address_lines:
        segments.append(f"ADDR|{line}|")
    segments.append(f"LOCATION|{city}|{state}|{postal}|")
    return segments


def _extract_tax_totals(po_header: Mapping[str, object], *, total_incl: Decimal, total_excl: Decimal) -> list[tuple[str, Decimal]]:
    """Collect tax totals from the PO header with sensible fallbacks."""

    tax_keys = {
        "GST": ["GST_Amount", "GST", "GSTAmount"],
        "PST": ["PST_Amount", "PST", "PSTAmount"],
        "QST": ["QST_Amount", "QST", "QSTAmount", "TVQ"],
        "HST": ["HST_Amount", "HST", "HSTAmount"],
        "VAT": ["VAT_Amount", "VAT", "VATAmount"],
        "TAX": ["Tax_Amount", "TaxAmount", "Total_Tax", "Total_Tax_Amount"],
    }

    totals: list[tuple[str, Decimal]] = []
    for code, keys in tax_keys.items():
        for key in keys:
            value = po_header.get(key)
            amount = _coerce_decimal(value)
            if amount != Decimal("0"):
                totals.append((code, amount))
                break

    if not totals:
        tax_diff = total_incl - total_excl
        if tax_diff != Decimal("0"):
            totals.append(("TAX", tax_diff))

    return totals


def _build_item_segments(po_lines: Iterable[Mapping[str, object]]) -> tuple[list[str], Decimal, Decimal]:
    """Render ITEM/DESC segments and return totals."""

    segments: list[str] = []
    total_quantity = Decimal("0")
    total_amount = Decimal("0")

    for idx, line in enumerate(po_lines, start=1):
        quantity = _coerce_decimal(line.get("Quantity"))
        unit_cost = _coerce_decimal(line.get("Direct_Unit_Cost") or line.get("Unit_Cost"))
        if quantity != Decimal("0"):
            total_quantity += quantity
        if unit_cost != Decimal("0"):
            total_amount += unit_cost * quantity

        unit_of_measure = _sanitize_text(str(line.get("Unit_of_Measure_Code") or "EA")) or "EA"
        vendor_item = _sanitize_text(str(line.get("Vendor_Item_No") or ""))
        buyer_item = _sanitize_text(str(line.get("No") or line.get("Item_No") or ""))
        description = _sanitize_text(str(line.get("Description") or ""))

        item_segment = "|".join(
            [
                "ITEM",
                str(idx),
                _format_decimal(quantity, precision="0.0001"),
                unit_of_measure,
                _format_decimal(unit_cost, precision="0.0001"),
                "VN",
                vendor_item,
                "",
                "",
                "BP",
                buyer_item,
                "",
            ]
        )
        segments.append(f"{item_segment}|")

        if description:
            segments.append(f"DESC|{description}|")

    return segments, total_quantity, total_amount


def build_edi_850_document(
    po_number: str,
    po_header: Mapping[str, object],
    po_lines: Iterable[Mapping[str, object]],
    vendor_info: Mapping[str, object],
    *,
    sender_id: str = DEFAULT_SENDER_ID,
) -> str:
    """Build the supplier-specific pipe-delimited EDI 850 document."""

    if not po_number:
        raise ValueError("A PO number is required to build an EDI 850 document")

    line_list = list(po_lines)
    if not line_list:
        raise ValueError("At least one purchase order line is required to build an EDI 850 document")

    po_date = _format_date(str(po_header.get("Document_Date") or po_header.get("Order_Date") or ""))
    vendor_no = _sanitize_text(str(vendor_info.get("No") or po_header.get("Buy_from_Vendor_No") or ""))

    if not vendor_no:
        raise ValueError("Vendor code is required to generate an EDI 850 document")

    document_segments: list[str] = []

    document_segments.append(f"ID|850|{sender_id}|{vendor_no}|")
    document_segments.append(f"HEAD|||{po_date}|{po_number}|00|NE|")

    document_segments.extend(_extract_ship_to_segments(po_header))
    document_segments.extend(_extract_bill_to_segments(vendor_info))

    terms_code = _sanitize_text(str(po_header.get("Payment_Terms_Code") or "")) or DEFAULT_TERMS_CODE
    document_segments.append(f"TERMS_GEN|{terms_code}|")

    document_segments.append(f"DATE|DR|{po_date}|")

    fob_description = _sanitize_text(str(po_header.get("FOB") or DEFAULT_FOB_DESCRIPTION)) or DEFAULT_FOB_DESCRIPTION
    document_segments.append(f"FOB|{DEFAULT_FOB_CODE}|ZZ|{fob_description}|")

    item_segments, calculated_quantity, calculated_amount = _build_item_segments(line_list)
    document_segments.extend(item_segments)

    total_excl_tax = _coerce_decimal(po_header.get("Amount"))
    total_incl_tax = _coerce_decimal(po_header.get("Amount_Including_VAT"))

    if total_excl_tax == Decimal("0") and calculated_amount != Decimal("0"):
        total_excl_tax = calculated_amount
    if total_incl_tax == Decimal("0") and total_excl_tax != Decimal("0"):
        total_incl_tax = total_excl_tax

    document_segments.append(
        f"TOTAL|TT|{_format_decimal(total_incl_tax, precision='0.01')}|{_format_decimal(total_excl_tax, precision='0.01')}|"
    )

    for code, amount in _extract_tax_totals(po_header, total_incl=total_incl_tax, total_excl=total_excl_tax):
        document_segments.append(f"TOTAL_TAX|{code}|{_format_decimal(amount, precision='0.01')}|")

    # Keep track of totals in logs for quick debugging if supplier reports issues.
    line_count = sum(1 for segment in item_segments if segment.startswith("ITEM|"))

    logfire.info(
        "Generated EDI 850 payload",
        po_number=po_number,
        line_count=line_count,
        total_quantity=str(calculated_quantity),
        total_excl=str(total_excl_tax),
        total_incl=str(total_incl_tax),
    )

    return "\n".join(document_segments) + "\n"


def generate_edi_850(po_number: str, *, sender_id: str = DEFAULT_SENDER_ID) -> str:
    """
    Legacy helper that fetches PO data via the legacy data module when available.

    Modern code paths should prefer :func:`build_edi_850_document` with explicit
    data. This function remains for backwards compatibility with existing
    scripts that still rely on the historical interface.
    """

    if BC is None:
        raise RuntimeError("Legacy data module 'data.BC' is not available")

    po_header = BC.get_PO_headers_edi(po_number)
    po_details = BC.get_PO_lines_edi(po_number)

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

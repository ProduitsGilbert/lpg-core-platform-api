"""Domain service for EDI document generation and transmission."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Optional, Tuple

import logfire

from app.adapters.erp_client import ERPClient
from app.errors import InvalidPurchaseOrderError, PurchaseOrderNotFoundError
from migration.edi import build_edi_850_document, get_edi_paths, send_file


@dataclass
class EDITransmissionResult:
    """Structured result for an EDI transmission attempt."""

    po_number: str
    file_name: str
    file_path: str
    sent: bool
    generated_at: datetime
    remote_path: Optional[str] = None
    message: Optional[str] = None


class EDIService:
    """Coordinate generation and transmission of EDI documents."""

    def __init__(self, erp_client: Optional[ERPClient] = None, *, sender_id: str = "GILBERTTECHP"):
        self.erp_client = erp_client or ERPClient()
        self.sender_id = sender_id

    def _fetch_po_data(self, po_number: str):
        po_header = self.erp_client.get_purchase_order(po_number)
        if not po_header:
            raise PurchaseOrderNotFoundError(po_number)

        lines = self.erp_client.get_purchase_order_lines(po_number)
        if not lines:
            raise InvalidPurchaseOrderError(
                "Purchase order has no lines to include in the EDI document",
                context={"po_number": po_number},
            )

        vendor_code = po_header.get("Buy_from_Vendor_No")
        if not vendor_code:
            raise InvalidPurchaseOrderError(
                "Purchase order is missing vendor information",
                context={"po_number": po_number},
            )

        vendor_info = self.erp_client.get_vendor(vendor_code)
        if not vendor_info:
            raise InvalidPurchaseOrderError(
                "Unable to retrieve vendor details for EDI document",
                context={"po_number": po_number, "vendor": vendor_code},
            )

        return po_header, lines, vendor_info

    def generate_purchase_order_850(self, po_number: str) -> Tuple[str, str]:
        po_header, lines, vendor_info = self._fetch_po_data(po_number)
        document = build_edi_850_document(
            po_number,
            po_header,
            lines,
            vendor_info,
            sender_id=self.sender_id,
        )

        timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        file_name = f"PO_{po_number}_{timestamp}.edi"
        return document, file_name

    def send_purchase_order_850(self, po_number: str) -> EDITransmissionResult:
        document, file_name = self.generate_purchase_order_850(po_number)

        send_dir, _ = get_edi_paths()
        os.makedirs(send_dir, exist_ok=True)
        file_path = os.path.join(send_dir, file_name)

        with open(file_path, "w", encoding="ascii", newline="") as edi_file:
            edi_file.write(document)

        logfire.info(
            "Generated EDI 850 document",
            po_number=po_number,
            file=file_path,
            sender_id=self.sender_id,
        )

        send_result = send_file(file_path, remove_local_on_success=False)

        logfire.info(
            "EDI 850 transmission attempted",
            po_number=po_number,
            success=send_result.success,
            remote_path=send_result.remote_path,
            message=send_result.message,
        )

        return EDITransmissionResult(
            po_number=po_number,
            file_name=file_name,
            file_path=file_path,
            sent=send_result.success,
            generated_at=datetime.now(UTC),
            remote_path=send_result.remote_path,
            message=send_result.message,
        )

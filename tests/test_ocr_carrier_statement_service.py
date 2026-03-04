import io
import threading
import time
from datetime import date
from decimal import Decimal

from pypdf import PdfWriter

from app.domain.ocr.models import (
    CarrierAccountStatementExtraction,
    CarrierStatementShipment,
)
from app.domain.ocr.ocr_service import OCRService


def _make_pdf_bytes(page_count: int) -> bytes:
    writer = PdfWriter()
    for _ in range(page_count):
        writer.add_blank_page(width=612, height=792)
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


class _FakeOCRClient:
    def __init__(self) -> None:
        self.enabled = True
        self._lock = threading.Lock()
        self._active_calls = 0
        self.max_active_calls = 0

    def extract_generic_document(
        self,
        file_content: bytes,
        filename: str,
        document_type: str,
        output_model,
        additional_instructions=None,
        prefer_vision: bool = False,
    ) -> CarrierAccountStatementExtraction:
        with self._lock:
            self._active_calls += 1
            self.max_active_calls = max(self.max_active_calls, self._active_calls)

        time.sleep(0.1)

        tracking_number = filename.rsplit("-", 1)[-1].replace(".pdf", "")
        shipment = CarrierStatementShipment(
            shipment_date=date(2025, 7, 14),
            tracking_number=tracking_number,
            shipped_from_address="LES PRODUITS GILBERT\n1840 MARCOTTE BOUL\nROBERVAL QC G8H 2P2",
            shipped_to_address="CLIENT DESTINATION\nJOLIETTE QC J6E 8T6",
            charges=[],
            total_charges=Decimal("10.00"),
        )
        result = CarrierAccountStatementExtraction(
            carrier="purolator",
            account_number="515176910",
            invoice_number="TEST-001",
            currency="CAD",
            processed_pages=1,
            shipments=[shipment],
        )

        with self._lock:
            self._active_calls -= 1
        return result

    def extract_generic_text(self, *args, **kwargs):
        raise AssertionError("extract_generic_text should not be called in this test")


def test_carrier_statement_extraction_processes_pdf_pages_in_parallel():
    client = _FakeOCRClient()
    service = OCRService(client)

    response = service.extract_carrier_account_statement(
        file_content=_make_pdf_bytes(page_count=4),
        filename="parallel-test.pdf",
        carrier="purolator",
    )

    assert response.success is True
    assert response.extracted_data["processed_pages"] == 4
    assert len(response.extracted_data["shipments"]) == 4
    assert client.max_active_calls > 1

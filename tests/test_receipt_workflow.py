import datetime
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from app.domain.dtos import CreateReceiptCommand, ReceiptLineInput
from app.domain.purchasing_service import PurchasingService
from app.errors import ValidationException


class StubERPClient:
    def __init__(self):
        self.poline_calls = []
        self.create_receipt_calls = []

    def get_poline(self, po_id: str, line_no: int):
        self.poline_calls.append((po_id, line_no))
        return {
            "po_id": po_id,
            "line_no": line_no,
            "item_no": "ITEM-001",
            "description": "Sample",
            "quantity": 5,
            "unit_of_measure": "EA",
            "unit_price": 10,
            "line_amount": 50,
            "promise_date": datetime.date.today().isoformat(),
            "status": "open",
            "quantity_received": 0,
        }

    def create_receipt(self, po_id, lines, receipt_date, vendor_shipment_no, job_delay, notes):
        self.create_receipt_calls.append(
            {
                "po_id": po_id,
                "lines": lines,
                "receipt_date": receipt_date,
                "vendor_shipment_no": vendor_shipment_no,
                "job_delay": job_delay,
                "notes": notes,
            }
        )
        return {
            "receipt_id": "RCPT-123",
            "po_id": po_id,
            "vendor_id": "VEND-001",
            "vendor_name": "Vendor Inc",
            "receipt_date": receipt_date.isoformat(),
            "posting_date": receipt_date.isoformat(),
            "status": "posted",
            "notes": notes,
            "created_by": "tester",
            "created_at": datetime.datetime.now(datetime.UTC).isoformat(),
        }


@pytest.fixture(autouse=True)
def stub_audit(monkeypatch):
    monkeypatch.setattr("app.audit.write_audit_log", lambda *args, **kwargs: None)


def make_command(**overrides):
    base = {
        "po_id": "PO123",
        "lines": [
            ReceiptLineInput(line_no=10000, quantity=Decimal("2"), location_code=None)
        ],
        "receipt_date": datetime.date(2024, 5, 1),
        "notes": "Test receipt",
        "vendor_shipment_no": overrides.get("vendor_shipment_no"),
        "job_check_delay_seconds": overrides.get("job_check_delay_seconds", 0),
        "actor": "tester",
        "trace_id": "trace-123",
    }
    base.update(overrides)
    return CreateReceiptCommand(**base)


def test_create_receipt_requires_shipment_number(monkeypatch):
    service = PurchasingService(erp_client=StubERPClient())
    db_session = MagicMock()

    command = make_command(vendor_shipment_no=None)

    with pytest.raises(ValidationException):
        service.create_receipt(command, db_session)


def test_create_receipt_success(monkeypatch):
    erp = StubERPClient()
    service = PurchasingService(erp_client=erp)
    db_session = MagicMock()

    command = make_command(vendor_shipment_no="SHIP-001")

    result = service.create_receipt(command, db_session)

    assert result.receipt_id == "RCPT-123"
    assert erp.create_receipt_calls[0]["vendor_shipment_no"] == "SHIP-001"
    assert erp.create_receipt_calls[0]["job_delay"] == 0

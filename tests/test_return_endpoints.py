import datetime
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.settings import settings
from app.domain.purchasing_service import PurchasingService
from app.domain.documents.file_share_service import FileShareService
from app.api.v1.erp import purchase_orders as v1_purchase_orders
from app.routers import purchasing as legacy_purchasing
from app.api.v1.documents import file_share as file_share_router
from app.deps import get_db


class StubERPClient:
    """In-memory ERP client simulation for testing."""

    def __init__(self) -> None:
        self.return_headers = {
            "RF01242": {
                "No": "RF01242",
                "Buy_from_Vendor_No": "WAJIN01",
                "Buy_from_Vendor_Name": "Wajin Supplier",
                "Posting_Date": "2024-04-20",
                "Vendor_Order_No": "PO072204",
                "External_Document_No": "PR072204",
                "Status": "Released",
                "Assigned_User_ID": "GIRDA01",
                "Last_Modified_DateTime": "2024-04-20T12:00:00Z",
            }
        }
        self.return_lines = {
            "RF01242": [
                {
                    "Document_No": "RF01242",
                    "Line_No": 10000,
                    "Receipt_Line_No": 10000,
                    "No": "NO PEINTURE",
                    "Description": "No Peinture",
                    "Quantity": 1,
                    "Unit_of_Measure_Code": "PCS",
                }
            ]
        }
        self.posted_receipt_headers = {
            "PR072204": {
                "No": "PR072204",
                "Buy_from_Vendor_No": "WAJIN01",
                "Buy_from_Vendor_Name": "Wajin Supplier",
                "Location_Code": "MAIN",
                "Purch_Order_No": "PO072204",
            }
        }
        self.posted_receipt_lines = {
            "PR072204": [
                {
                    "Document_No": "PR072204",
                    "Line_No": 10000,
                    "Item_No": "NO PEINTURE",
                    "Description": "No Peinture",
                    "Quantity": 1,
                    "Unit_of_Measure_Code": "PCS",
                    "Location_Code": "MAIN",
                }
            ]
        }
        self.created_returns = []

    # -- Helpers used by PurchasingService --
    def get_purchase_return_order(self, return_no: str):
        return self.return_headers.get(return_no)

    def get_purchase_return_order_lines(self, return_no: str):
        return self.return_lines.get(return_no, [])

    def get_posted_purchase_receipt_lines(self, receipt_id: str):
        return self.posted_receipt_lines.get(receipt_id, [])

    def create_return(self, receipt_id: str, lines, return_date: datetime.date, reason: str) -> str:
        header = self.posted_receipt_headers.get(receipt_id)
        if not header:
            raise ValueError(f"Unknown receipt {receipt_id}")

        return_no = "RF09999"
        new_header = {
            "No": return_no,
            "Buy_from_Vendor_No": header["Buy_from_Vendor_No"],
            "Buy_from_Vendor_Name": header.get("Buy_from_Vendor_Name"),
            "Posting_Date": return_date.isoformat(),
            "Vendor_Order_No": header.get("Purch_Order_No"),
            "External_Document_No": receipt_id,
            "Status": "Open",
            "Assigned_User_ID": settings.bc_api_username or "tester",
            "Last_Modified_DateTime": f"{return_date.isoformat()}T08:00:00Z",
            "Comments": reason,
        }

        mapped_lines = [
            {
                "Document_No": return_no,
                "Line_No": payload.get("line_no", 10000),
                "Receipt_Line_No": payload.get("line_no", 10000),
                "No": payload.get("item_no"),
                "Description": payload.get("description"),
                "Quantity": payload.get("quantity", 0),
                "Unit_of_Measure_Code": payload.get("unit_of_measure"),
            }
            for payload in lines
        ]

        self.return_headers[return_no] = new_header
        self.return_lines[return_no] = mapped_lines
        self.created_returns.append((return_no, receipt_id, lines, reason))

        return return_no


class DummyResponse:
    def __init__(self, status_code: int, content: bytes, headers: dict[str, str]):
        self.status_code = status_code
        self.content = content
        self.headers = headers
        self.text = content.decode("utf-8", errors="ignore")

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class DummyAsyncClient:
    def __init__(self, *args, response: DummyResponse, **kwargs):
        self._response = response
        self.requested_url = None
        self.requested_headers = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, url: str, headers=None):
        self.requested_url = url
        self.requested_headers = headers or {}
        return self._response


@pytest.fixture
def erp_stub(monkeypatch) -> StubERPClient:
    settings.erp_base_url = "https://bc.example.com/ODataV4/"
    settings.bc_api_username = "GIRDA01"
    settings.bc_api_password = "password"
    settings.file_share_requester_id = "GIRDA01"
    settings.logfire_api_key = None

    async def _verify_database_connection():
        return True

    monkeypatch.setattr("app.main.verify_database_connection", _verify_database_connection)
    monkeypatch.setattr("app.main.dispose_engine", lambda: None)

    stub = StubERPClient()
    service = PurchasingService(erp_client=stub, ai_client=MagicMock())
    monkeypatch.setattr(v1_purchase_orders, "purchasing_service", service)
    monkeypatch.setattr(legacy_purchasing, "purchasing_service", service)

    file_service = FileShareService()
    monkeypatch.setattr(file_share_router, "file_share_service", file_service)

    return stub


@pytest.fixture
def client(erp_stub):
    app = create_app()
    app.dependency_overrides[get_db] = lambda: MagicMock()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_get_purchase_return_order(client):
    paths = {route.path for route in client.app.routes}
    assert '/api/v1/erp/po/returns/{return_id}' in paths

    response = client.get("/api/v1/erp/po/returns/RF01242")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["return_id"] == "RF01242"
    assert payload["po_id"] == "PO072204"
    assert payload["vendor_id"] == "WAJIN01"
    assert payload["lines"][0]["item_no"] == "NO PEINTURE"
    assert float(payload["lines"][0]["quantity_returned"]) == 1.0


def test_create_purchase_return_order(client, erp_stub: StubERPClient):
    body = {
        "receipt_id": "PR072204",
        "lines": [
            {
                "line_no": 10000,
                "quantity": "1"
            }
        ],
        "reason": "Damaged on arrival",
        "return_date": "2024-05-01",
    }

    response = client.post("/api/v1/erp/po/PO072204/returns", json=body)

    assert response.status_code == 201
    payload = response.json()
    assert payload["return_id"] == "RF09999"
    assert payload["po_id"] == "PO072204"
    assert payload["vendor_id"] == "WAJIN01"
    assert float(payload["lines"][0]["quantity_returned"]) == 1.0
    assert ("RF09999", "PR072204") in [
        (entry[0], entry[1]) for entry in erp_stub.created_returns
    ]


def test_get_item_pdf_file(client, monkeypatch):
    pdf_bytes = b"%PDF-1.4\nPDF content for 1510136\n%%EOF"
    response = DummyResponse(
        status_code=200,
        content=pdf_bytes,
        headers={
            "Content-Type": "application/pdf",
            "Content-Disposition": 'attachment; filename="1510136_datasheet.pdf"',
        },
    )

    dummy_client = DummyAsyncClient(response=response)
    monkeypatch.setattr(
        "app.domain.documents.file_share_service.httpx.AsyncClient",
        lambda *args, **kwargs: dummy_client,
    )

    api_response = client.get("/api/v1/documents/file-share/items/1510136/pdf")

    assert api_response.status_code == 200
    assert api_response.headers["Content-Type"] == "application/pdf"
    assert b"1510136" in api_response.content
    assert dummy_client.requested_url.endswith("FileShare/GetItemPDFFile(1510136)")
    assert dummy_client.requested_headers["RequesterUserID"] == "GIRDA01"

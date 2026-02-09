from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient

from app.api.v1.kpi.router import get_payables_invoice_stats_service
from app.main import app


def _client() -> TestClient:
    return TestClient(app)


def test_get_payables_invoice_stats() -> None:
    client = _client()
    stub = MagicMock()
    stub.get_stats = AsyncMock(
        return_value={
            "continia": {"invoice_count": 3, "total_amount": 200.5},
            "purchase_invoice": {"invoice_count": 2, "total_amount": 110.5},
            "posted_purchase_order": {"invoice_count": 4, "total_amount": 420.0},
            "continia_statuses": [
                {"status": "Mismatch", "invoice_count": 2, "total_amount": 150.5},
                {"status": "Awaiting Approval", "invoice_count": 1, "total_amount": 50.0},
            ],
        }
    )

    app.dependency_overrides[get_payables_invoice_stats_service] = lambda: stub
    try:
        response = client.get("/api/v1/kpi/payables/invoices/stats")
    finally:
        app.dependency_overrides.pop(get_payables_invoice_stats_service, None)

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["continia"]["invoice_count"] == 3
    assert payload["purchase_invoice"]["total_amount"] == 110.5
    assert payload["posted_purchase_order"]["invoice_count"] == 4
    assert payload["continia_statuses"][0]["status"] == "Mismatch"
    stub.get_stats.assert_awaited_once_with(refresh=False)


def test_get_payables_invoice_stats_with_refresh() -> None:
    client = _client()
    stub = MagicMock()
    stub.get_stats = AsyncMock(
        return_value={
            "continia": {"invoice_count": 1, "total_amount": 10.0},
            "purchase_invoice": {"invoice_count": 2, "total_amount": 20.0},
            "posted_purchase_order": {"invoice_count": 3, "total_amount": 30.0},
            "continia_statuses": [],
        }
    )

    app.dependency_overrides[get_payables_invoice_stats_service] = lambda: stub
    try:
        response = client.get("/api/v1/kpi/payables/invoices/stats?refresh=true")
    finally:
        app.dependency_overrides.pop(get_payables_invoice_stats_service, None)

    assert response.status_code == 200, response.text
    stub.get_stats.assert_awaited_once_with(refresh=True)

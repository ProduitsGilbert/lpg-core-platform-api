"""Tests for the purchase order reopen endpoint."""

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import app
from app.domain.erp.models import PurchaseOrderReopenResponse
from app.errors import ERPError
import app.api.v1.erp.purchase_orders as po_module


client = TestClient(app)


def test_reopen_purchase_order_success():
    mock_response = PurchaseOrderReopenResponse(
        id="PO034369",
        status="Open",
        details={"message": "Reopened"},
    )

    async_mock = AsyncMock(return_value=mock_response)

    with patch.object(po_module.po_service, "reopen_purchase_order", async_mock):
        response = client.post(
            "/api/v1/erp/po/reopen",
            json={"headerNo": "PO034369"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["id"] == "PO034369"
    assert payload["data"]["status"].lower() == "open"
    async_mock.assert_awaited_once_with("PO034369")


def test_reopen_purchase_order_service_error():
    error = ERPError("Business Central unavailable", context={"po_id": "PO034369"})
    async_mock = AsyncMock(side_effect=error)

    with patch.object(po_module.po_service, "reopen_purchase_order", async_mock):
        response = client.post(
            "/api/v1/erp/po/reopen",
            json={"headerNo": "PO034369"},
        )

    assert response.status_code == 503
    payload = response.json()
    assert payload["error"] == "ERP_ERROR"
    assert payload["detail"] == "Business Central unavailable"


def test_reopen_purchase_order_validation_error():
    response = client.post(
        "/api/v1/erp/po/reopen",
        json={},
    )

    assert response.status_code == 422
    payload = response.json()
    assert payload["error"] == "VALIDATION_ERROR"

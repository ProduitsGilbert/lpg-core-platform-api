import os
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

os.environ.setdefault("ERP_BASE_URL", "http://test.example.com")
os.environ.setdefault(
    "DB_DSN",
    "mssql+pyodbc://test:test@localhost:1433/test?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes",
)

from app.domain.edi.eleknet.errors import ElekNetUnauthorizedError
from app.domain.edi.eleknet.schemas import ElekNetOrderResponse, ElekNetPriceAvailabilityResponse
from app.main import app


def test_price_availability_endpoint_returns_normalized_response(monkeypatch):
    from app.api.v1.edi import eleknet as eleknet_router

    fake_service = AsyncMock()
    fake_service.fetch_price_availability.return_value = ElekNetPriceAvailabilityResponse(
        returnCode="S",
        items=[],
    )
    monkeypatch.setattr(eleknet_router, "eleknet_service", fake_service)

    client = TestClient(app)
    response = client.post(
        "/api/v1/edi/eleknet/price-availability",
        json={"items": [{"productCode": "ABC-001", "qty": 1}], "productInfo": True},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["returnCode"] == "S"
    assert payload["data"]["items"] == []


def test_price_availability_endpoint_validates_item_limit():
    client = TestClient(app)
    too_many_items = [{"productCode": f"P-{i}", "qty": 1} for i in range(201)]

    response = client.post(
        "/api/v1/edi/eleknet/price-availability",
        json={"items": too_many_items},
    )

    assert response.status_code == 422


def test_order_endpoint_returns_401_on_access_denied(monkeypatch):
    from app.api.v1.edi import eleknet as eleknet_router

    fake_service = AsyncMock()
    fake_service.create_order.side_effect = ElekNetUnauthorizedError("Access denied")
    monkeypatch.setattr(eleknet_router, "eleknet_service", fake_service)

    client = TestClient(app)
    response = client.post(
        "/api/v1/edi/eleknet/order",
        json={
            "orderHeader": {
                "partner": "Lumen",
                "type": "Order",
                "custno": "CUST-01",
                "shipTo": "SHIP-01",
                "whse": "WH-1",
                "po": "PO-100",
                "delivery": "Y",
                "shipComplete": "N",
            },
            "orderLines": [{"productCode": "ABC-001", "qty": 3}],
        },
    )

    assert response.status_code == 401
    payload = response.json()
    assert payload["error"] == "ELEKNET_UNAUTHORIZED"


def test_order_endpoint_returns_success(monkeypatch):
    from app.api.v1.edi import eleknet as eleknet_router

    fake_service = AsyncMock()
    fake_service.create_order.return_value = ElekNetOrderResponse(
        returnCode="S",
        po="PO-100",
        orderNumber="12345",
    )
    monkeypatch.setattr(eleknet_router, "eleknet_service", fake_service)

    client = TestClient(app)
    response = client.post(
        "/api/v1/edi/eleknet/order",
        json={
            "orderHeader": {
                "partner": "Lumen",
                "type": "Order",
                "custno": "CUST-01",
                "shipTo": "SHIP-01",
                "whse": "WH-1",
                "po": "PO-100",
                "delivery": "Y",
                "shipComplete": "N",
            },
            "orderLines": [{"productCode": "ABC-001", "qty": 3}],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["returnCode"] == "S"
    assert payload["data"]["po"] == "PO-100"
    assert payload["data"]["orderNumber"] == "12345"

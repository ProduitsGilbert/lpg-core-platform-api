from datetime import date
from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient

from app.api.v1.crm.router import get_crm_service
from app.main import app


def _client() -> TestClient:
    return TestClient(app)


def test_get_crm_accounts_endpoint() -> None:
    client = _client()
    stub = MagicMock()
    stub.get_accounts = AsyncMock(
        return_value={
            "items": [
                {
                    "account_id": "acc-1",
                    "name": "Acme",
                    "email": "sales@acme.com",
                }
            ],
            "count": 1,
        }
    )

    app.dependency_overrides[get_crm_service] = lambda: stub
    try:
        response = client.get("/api/v1/crm/accounts?top=25&search=ac")
    finally:
        app.dependency_overrides.pop(get_crm_service, None)

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["count"] == 1
    assert payload["items"][0]["name"] == "Acme"
    stub.get_accounts.assert_awaited_once_with(top=25, search="ac")


def test_get_crm_sales_stats_endpoint() -> None:
    client = _client()
    stub = MagicMock()
    stub.get_sales_stats = AsyncMock(
        return_value={
            "as_of": date(2026, 2, 9),
            "open_opportunities_count": 10,
            "open_pipeline_amount": 100000.0,
            "weighted_pipeline_amount": 72000.0,
            "won_this_month_count": 4,
            "won_this_month_amount": 28000.0,
            "lost_this_month_count": 2,
        }
    )

    app.dependency_overrides[get_crm_service] = lambda: stub
    try:
        response = client.get("/api/v1/crm/sales/stats")
    finally:
        app.dependency_overrides.pop(get_crm_service, None)

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["open_pipeline_amount"] == 100000.0
    assert payload["won_this_month_count"] == 4
    stub.get_sales_stats.assert_awaited_once()


def test_get_crm_sales_forecast_validates_months() -> None:
    client = _client()
    stub = MagicMock()
    app.dependency_overrides[get_crm_service] = lambda: stub
    try:
        response = client.get("/api/v1/crm/sales/forecast?months=13")
    finally:
        app.dependency_overrides.pop(get_crm_service, None)
    assert response.status_code == 422, response.text

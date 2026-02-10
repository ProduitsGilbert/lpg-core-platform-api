import datetime as dt
from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient

from app.api.v1.kpi.router import get_sales_stats_service
from app.main import app


def _client() -> TestClient:
    return TestClient(app)


def test_get_sales_stats_snapshot_uses_latest_cache_when_no_date() -> None:
    client = _client()
    stub = MagicMock()
    stub.get_latest_snapshot = AsyncMock(
        return_value={
            "snapshot_date": "2026-02-09",
            "new_orders_count": 4,
            "last_week_orders_amount": 12345.67,
            "new_quotes_count": 2,
            "last_week_quotes_amount": 345.67,
            "total_quotes_count": 9,
            "total_quotes_amount": 987.65,
            "pending_quotes_amount": 456.78,
            "biggest_customer_last_month": {
                "customer_no": "C-100",
                "customer_name": "ACME",
                "order_amount": 9999.99,
            },
        }
    )

    app.dependency_overrides[get_sales_stats_service] = lambda: stub
    try:
        response = client.get("/api/v1/kpi/sales/stats")
    finally:
        app.dependency_overrides.pop(get_sales_stats_service, None)

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["snapshot_date"] == "2026-02-09"
    assert payload["new_orders_count"] == 4
    assert payload["new_quotes_count"] == 2
    stub.get_latest_snapshot.assert_awaited_once()


def test_get_sales_stats_snapshot_with_date() -> None:
    client = _client()
    stub = MagicMock()
    stub.get_snapshot = AsyncMock(
        return_value={
            "snapshot_date": "2026-02-08",
            "new_orders_count": 1,
            "last_week_orders_amount": 300.0,
            "new_quotes_count": 1,
            "last_week_quotes_amount": 120.0,
            "total_quotes_count": 5,
            "total_quotes_amount": 420.0,
            "pending_quotes_amount": 120.0,
            "biggest_customer_last_month": None,
        }
    )

    app.dependency_overrides[get_sales_stats_service] = lambda: stub
    try:
        response = client.get("/api/v1/kpi/sales/stats?date=2026-02-08&refresh=true")
    finally:
        app.dependency_overrides.pop(get_sales_stats_service, None)

    assert response.status_code == 200, response.text
    stub.get_snapshot.assert_awaited_once_with(snapshot_date=dt.date(2026, 2, 8), refresh=True)


def test_get_sales_stats_snapshot_invalid_date() -> None:
    client = _client()
    stub = MagicMock()
    app.dependency_overrides[get_sales_stats_service] = lambda: stub
    try:
        response = client.get("/api/v1/kpi/sales/stats?date=09-02-2026")
    finally:
        app.dependency_overrides.pop(get_sales_stats_service, None)

    assert response.status_code == 422, response.text
    payload = response.json()
    assert payload["error"] == "VALIDATION_ERROR"


def test_get_sales_stats_history() -> None:
    client = _client()
    stub = MagicMock()
    stub.get_history = AsyncMock(
        return_value={
            "start_date": "2026-01-11",
            "end_date": "2026-02-09",
            "days": 30,
            "points": [
                {
                    "snapshot_date": "2026-02-09",
                    "new_orders_count": 2,
                    "last_week_orders_amount": 500.0,
                    "new_quotes_count": 2,
                    "last_week_quotes_amount": 200.0,
                    "total_quotes_count": 7,
                    "total_quotes_amount": 700.0,
                    "pending_quotes_amount": 100.0,
                    "biggest_customer_last_month": None,
                }
            ],
        }
    )

    app.dependency_overrides[get_sales_stats_service] = lambda: stub
    try:
        response = client.get("/api/v1/kpi/sales/stats/history?end_date=2026-02-09&days=30")
    finally:
        app.dependency_overrides.pop(get_sales_stats_service, None)

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["end_date"] == "2026-02-09"
    assert payload["days"] == 30
    assert payload["points"][0]["snapshot_date"] == "2026-02-09"
    stub.get_history.assert_awaited_once_with(
        end_date=dt.date(2026, 2, 9),
        days=30,
        ensure_end_snapshot=True,
    )


def test_get_sales_stats_history_invalid_end_date() -> None:
    client = _client()
    stub = MagicMock()
    app.dependency_overrides[get_sales_stats_service] = lambda: stub
    try:
        response = client.get("/api/v1/kpi/sales/stats/history?end_date=02-09-2026")
    finally:
        app.dependency_overrides.pop(get_sales_stats_service, None)

    assert response.status_code == 422, response.text
    payload = response.json()
    assert payload["error"] == "VALIDATION_ERROR"

import datetime as dt
from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient

from app.api.v1.kpi.router import get_purchasing_stats_service
from app.main import app


def _client() -> TestClient:
    return TestClient(app)


def test_get_purchasing_stats() -> None:
    client = _client()
    stub = MagicMock()
    stub.get_stats = AsyncMock(
        return_value={
            "start_date": "2026-01-13",
            "end_date": "2026-02-10",
            "days": 29,
            "period": "week",
            "total_pos": 5,
            "total_amount": 1250.5,
            "po_timeline": [
                {
                    "period_start": "2026-02-09",
                    "period_end": "2026-02-10",
                    "po_count": 2,
                    "total_amount": 700.0,
                }
            ],
            "action_categories": [
                {"action_category": "PRICE_CHANGE", "updates_count": 3},
                {"action_category": "DATE_CHANGE", "updates_count": 2},
            ],
            "total_action_updates": 5,
        }
    )

    app.dependency_overrides[get_purchasing_stats_service] = lambda: stub
    try:
        response = client.get("/api/v1/kpi/purchasing/stats?end_date=2026-02-10&days=29&period=week")
    finally:
        app.dependency_overrides.pop(get_purchasing_stats_service, None)

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["total_pos"] == 5
    assert payload["po_timeline"][0]["period_start"] == "2026-02-09"
    assert payload["action_categories"][0]["action_category"] == "PRICE_CHANGE"
    stub.get_stats.assert_awaited_once_with(
        end_date=dt.date(2026, 2, 10),
        days=29,
        period="week",
    )


def test_get_purchasing_stats_invalid_date() -> None:
    client = _client()
    stub = MagicMock()
    app.dependency_overrides[get_purchasing_stats_service] = lambda: stub
    try:
        response = client.get("/api/v1/kpi/purchasing/stats?end_date=10-02-2026")
    finally:
        app.dependency_overrides.pop(get_purchasing_stats_service, None)

    assert response.status_code == 422, response.text
    payload = response.json()
    assert payload["error"] == "VALIDATION_ERROR"

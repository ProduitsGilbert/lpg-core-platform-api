from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient

from app.api.v1.kpi.router import get_tool_prediction_kpi_service
from app.main import app


def _client() -> TestClient:
    return TestClient(app)


def _sample_response() -> dict:
    return {
        "snapshot_date": "2026-03-04",
        "machine_center": "DMC100",
        "total_tools": 1,
        "predictions": [
            {
                "snapshot_date": "2026-03-04",
                "generated_at": "2026-03-04T10:00:00+00:00",
                "work_center_no": "40253",
                "machine_center": "DMC100",
                "tool_id": "1035",
                "total_required_use_time_seconds": 3600,
                "rows_count": 4,
                "program_count": 2,
                "total_remaining_life": 140.0,
                "inventory_instances": 3,
                "available_instances": 2,
                "sister_count_total": 2,
                "sister_count_available": 1,
                "sister_count_machine": 1,
                "time_since_last_use_hours": 3.0,
                "uses_last_24h": 5,
                "uses_last_7d": 18,
                "wear_rate_24h": 7.2,
                "wear_rate_7d": 4.5,
                "tool_usage_minutes_90d": 920.0,
                "future_usage_minutes_24h": 10.0,
                "future_usage_minutes_48h": 20.0,
                "future_usage_minutes_7d": 70.0,
                "shortage_probability": 0.74,
                "shortage_label": "HIGH",
                "updated_at": "2026-03-04T10:00:01+00:00",
            }
        ],
    }


def test_get_tool_shortage_predictions_latest_snapshot() -> None:
    client = _client()
    stub = MagicMock()
    stub.get_latest_snapshot = AsyncMock(return_value=_sample_response())

    app.dependency_overrides[get_tool_prediction_kpi_service] = lambda: stub
    try:
        response = client.get("/api/v1/kpi/tooling/shortage-predictions?machine_center=dmc100&limit=50")
    finally:
        app.dependency_overrides.pop(get_tool_prediction_kpi_service, None)

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["snapshot_date"] == "2026-03-04"
    assert payload["total_tools"] == 1
    assert payload["predictions"][0]["tool_id"] == "1035"
    stub.get_latest_snapshot.assert_awaited_once_with(machine_center="dmc100", limit=50)


def test_get_tool_shortage_predictions_with_refresh() -> None:
    client = _client()
    stub = MagicMock()
    stub.refresh_snapshot = AsyncMock(return_value=10)
    stub.get_snapshot = AsyncMock(return_value=_sample_response())

    app.dependency_overrides[get_tool_prediction_kpi_service] = lambda: stub
    try:
        response = client.get(
            "/api/v1/kpi/tooling/shortage-predictions?date=2026-03-03&refresh=true&machine_center=DMC100"
        )
    finally:
        app.dependency_overrides.pop(get_tool_prediction_kpi_service, None)

    assert response.status_code == 200, response.text
    stub.refresh_snapshot.assert_awaited_once()
    stub.get_snapshot.assert_awaited_once()


def test_get_tool_shortage_predictions_invalid_date() -> None:
    client = _client()
    stub = MagicMock()
    stub.get_latest_snapshot = AsyncMock(return_value=_sample_response())

    app.dependency_overrides[get_tool_prediction_kpi_service] = lambda: stub
    try:
        response = client.get("/api/v1/kpi/tooling/shortage-predictions?date=03-04-2026")
    finally:
        app.dependency_overrides.pop(get_tool_prediction_kpi_service, None)

    assert response.status_code == 422

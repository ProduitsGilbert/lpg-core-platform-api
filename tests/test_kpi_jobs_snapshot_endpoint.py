import datetime as dt
from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient

from app.api.v1.kpi.router import get_jobs_snapshot_service
from app.main import app


def _client() -> TestClient:
    return TestClient(app)


def test_get_jobs_snapshot_uses_latest_cache_when_no_date() -> None:
    client = _client()
    stub = MagicMock()
    stub.get_latest_snapshot = AsyncMock(
        return_value={
            "snapshot_date": "2026-02-09",
            "total_jobs": 1,
            "jobs": [
                {
                    "job_no": "GIM1136",
                    "job_name": "Factory Upgrade",
                    "job_status": "Open",
                    "avancement_bom_percent": 65.5,
                    "division": "CONST",
                    "region": "CAN-QC",
                }
            ],
        }
    )

    app.dependency_overrides[get_jobs_snapshot_service] = lambda: stub
    try:
        response = client.get("/api/v1/kpi/jobs/snapshots?division=CONST")
    finally:
        app.dependency_overrides.pop(get_jobs_snapshot_service, None)

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["snapshot_date"] == "2026-02-09"
    assert payload["jobs"][0]["job_no"] == "GIM1136"
    stub.get_latest_snapshot.assert_awaited_once_with(
        division="CONST",
        region=None,
        job_no=None,
        job_status="Open",
    )


def test_get_jobs_snapshot_with_date_refresh() -> None:
    client = _client()
    stub = MagicMock()
    stub.get_snapshot = AsyncMock(
        return_value={
            "snapshot_date": "2026-02-08",
            "total_jobs": 0,
            "jobs": [],
        }
    )

    app.dependency_overrides[get_jobs_snapshot_service] = lambda: stub
    try:
        response = client.get("/api/v1/kpi/jobs/snapshots?date=2026-02-08&refresh=true&region=CAN-QC")
    finally:
        app.dependency_overrides.pop(get_jobs_snapshot_service, None)

    assert response.status_code == 200, response.text
    stub.get_snapshot.assert_awaited_once_with(
        snapshot_date=dt.date(2026, 2, 8),
        refresh=True,
        division=None,
        region="CAN-QC",
        job_no=None,
        job_status="Open",
    )


def test_get_jobs_snapshot_invalid_date() -> None:
    client = _client()
    stub = MagicMock()
    app.dependency_overrides[get_jobs_snapshot_service] = lambda: stub
    try:
        response = client.get("/api/v1/kpi/jobs/snapshots?date=09-02-2026")
    finally:
        app.dependency_overrides.pop(get_jobs_snapshot_service, None)

    assert response.status_code == 422, response.text
    payload = response.json()
    assert payload["error"] == "VALIDATION_ERROR"


def test_get_jobs_snapshot_history() -> None:
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
                    "job_no": "GIM1136",
                    "job_name": "Factory Upgrade",
                    "job_status": "Open",
                    "avancement_bom_percent": 72.0,
                    "division": "CONST",
                    "region": "CAN-QC",
                }
            ],
        }
    )

    app.dependency_overrides[get_jobs_snapshot_service] = lambda: stub
    try:
        response = client.get(
            "/api/v1/kpi/jobs/snapshots/history?end_date=2026-02-09&days=30&job_no=GIM1136"
        )
    finally:
        app.dependency_overrides.pop(get_jobs_snapshot_service, None)

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["end_date"] == "2026-02-09"
    assert payload["points"][0]["job_no"] == "GIM1136"
    stub.get_history.assert_awaited_once_with(
        end_date=dt.date(2026, 2, 9),
        days=30,
        ensure_end_snapshot=True,
        division=None,
        region=None,
        job_no="GIM1136",
        job_status="Open",
    )


def test_get_specific_job_progress_history() -> None:
    client = _client()
    stub = MagicMock()
    stub.get_job_progress_history = AsyncMock(
        return_value={
            "job_no": "GIM1136",
            "job_name": "Factory Upgrade",
            "job_status": "Open",
            "division": "CONST",
            "region": "CAN-QC",
            "start_date": "2026-02-01",
            "end_date": "2026-02-09",
            "days": 9,
            "points": [
                {"snapshot_date": "2026-02-08", "avancement_bom_percent": 64.0},
                {"snapshot_date": "2026-02-09", "avancement_bom_percent": 66.5},
            ],
        }
    )
    app.dependency_overrides[get_jobs_snapshot_service] = lambda: stub
    try:
        response = client.get("/api/v1/kpi/jobs/GIM1136/snapshots/history?days=9")
    finally:
        app.dependency_overrides.pop(get_jobs_snapshot_service, None)

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["job_no"] == "GIM1136"
    assert len(payload["points"]) == 2
    stub.get_job_progress_history.assert_awaited_once_with(
        job_no="GIM1136",
        end_date=dt.date.today(),
        days=9,
        ensure_end_snapshot=True,
        division=None,
        region=None,
        job_status="Open",
    )


def test_warmup_jobs_snapshot_cache_endpoint() -> None:
    client = _client()
    stub = MagicMock()
    stub.warmup_snapshot = AsyncMock(
        return_value={
            "snapshot_date": "2026-02-09",
            "refreshed": True,
            "total_jobs": 120,
            "duration_seconds": 6.2,
        }
    )
    app.dependency_overrides[get_jobs_snapshot_service] = lambda: stub
    try:
        response = client.post("/api/v1/kpi/jobs/snapshots/warmup?date=2026-02-09")
    finally:
        app.dependency_overrides.pop(get_jobs_snapshot_service, None)

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["refreshed"] is True
    assert payload["total_jobs"] == 120
    stub.warmup_snapshot.assert_awaited_once_with(
        snapshot_date=dt.date(2026, 2, 9),
        job_status="Open",
    )

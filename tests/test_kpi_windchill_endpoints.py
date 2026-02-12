from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from app.api.v1.kpi.router import get_windchill_kpi_service
from app.main import app


def _client() -> TestClient:
    return TestClient(app)


def test_list_windchill_created_drawings_per_user() -> None:
    client = _client()
    stub = MagicMock()
    stub.list_created_drawings_per_user.return_value = [
        {"count": 2, "creation_date": "2026-02-05", "created_by": "User A"}
    ]

    app.dependency_overrides[get_windchill_kpi_service] = lambda: stub
    try:
        response = client.get("/api/v1/kpi/windchill/created-drawings-per-user")
    finally:
        app.dependency_overrides.pop(get_windchill_kpi_service, None)

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["data"][0]["count"] == 2
    assert payload["data"][0]["creation_date"] == "2026-02-05"
    assert payload["data"][0]["created_by"] == "User A"
    stub.list_created_drawings_per_user.assert_called_once()


def test_list_windchill_modified_drawings_per_user() -> None:
    client = _client()
    stub = MagicMock()
    stub.list_modified_drawings_per_user.return_value = [
        {"count": 3, "last_modified": "2026-02-05", "modified_by": "User B"}
    ]

    app.dependency_overrides[get_windchill_kpi_service] = lambda: stub
    try:
        response = client.get("/api/v1/kpi/windchill/modified-drawings-per-user")
    finally:
        app.dependency_overrides.pop(get_windchill_kpi_service, None)

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["data"][0]["count"] == 3
    assert payload["data"][0]["last_modified"] == "2026-02-05"
    assert payload["data"][0]["modified_by"] == "User B"
    stub.list_modified_drawings_per_user.assert_called_once()

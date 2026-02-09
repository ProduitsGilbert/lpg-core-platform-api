import os

import pytest


def _kpi_url(base_url: str, path: str) -> str:
    return f"{base_url}/api/v1/kpi{path}"


def _getenv_any(*names: str) -> str | None:
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    return None


def _require_windchill_env() -> None:
    if _getenv_any("WINDCHILL_DB_DSN", "windchill_DB_DSN"):
        return
    required = (
        ("WINDCHILL_SQL_SERVER", "windchill_SQL_SERVER"),
        ("WINDCHILL_SQL_DATABASE", "windchill_SQL_DATABASE"),
        ("WINDCHILL_SQL_USERNAME", "windchill_SQL_USERNAME"),
        ("WINDCHILL_SQL_PASSWORD", "windchill_SQL_PASSWORD"),
    )
    missing = [pair[0] for pair in required if not _getenv_any(*pair)]
    if missing:
        pytest.skip(f"Missing Windchill configuration environment variables: {', '.join(missing)}")


def test_windchill_created_drawings_per_user(http_session, base_url, default_timeout) -> None:
    _require_windchill_env()

    response = http_session.get(
        _kpi_url(base_url, "/windchill/created-drawings-per-user"),
        timeout=default_timeout,
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert "data" in payload
    assert isinstance(payload["data"], list)


def test_windchill_modified_drawings_per_user(http_session, base_url, default_timeout) -> None:
    _require_windchill_env()

    response = http_session.get(
        _kpi_url(base_url, "/windchill/modified-drawings-per-user"),
        timeout=default_timeout,
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert "data" in payload
    assert isinstance(payload["data"], list)

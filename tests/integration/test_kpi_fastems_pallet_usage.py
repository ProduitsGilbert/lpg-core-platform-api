import os

import pytest


def _kpi_url(base_url: str, path: str) -> str:
    return f"{base_url}/api/v1/kpi{path}"


def _require_cedule_env() -> None:
    if os.getenv("CEDULE_DB_DSN"):
        return
    required = (
        "CEDULE_SQL_SERVER",
        "CEDULE_SQL_DATABASE",
        "CEDULE_SQL_USERNAME",
        "CEDULE_SQL_PASSWORD",
    )
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        pytest.skip(f"Missing Cedule configuration environment variables: {', '.join(missing)}")


def test_fastems1_pallet_usage(http_session, base_url, default_timeout) -> None:
    _require_cedule_env()

    response = http_session.get(
        _kpi_url(base_url, "/fastems1/pallet-usage"),
        timeout=default_timeout,
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert "data" in payload
    assert isinstance(payload["data"], list)


def test_fastems2_pallet_usage(http_session, base_url, default_timeout) -> None:
    _require_cedule_env()

    response = http_session.get(
        _kpi_url(base_url, "/fastems2/pallet-usage"),
        timeout=default_timeout,
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert "data" in payload
    assert isinstance(payload["data"], list)

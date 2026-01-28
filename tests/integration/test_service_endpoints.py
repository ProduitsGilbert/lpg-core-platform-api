import os

import pytest


CUSTOMER_IDS = [
    value.strip()
    for value in os.environ.get("TEST_SERVICE_CUSTOMER_IDS", "ALEEQ01,DYNTO01,GERCO01").split(",")
    if value.strip()
]


def _service_url(base_url: str, path: str) -> str:
    return f"{base_url}/api/v1/service{path}"


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


def test_list_service_divisions(http_session, base_url, default_timeout) -> None:
    _require_cedule_env()

    response = http_session.get(_service_url(base_url, "/divisions"), timeout=default_timeout)
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["data"], "Expected at least one service division"


@pytest.mark.parametrize("customer_id", CUSTOMER_IDS)
def test_list_customer_service_assets(http_session, base_url, default_timeout, customer_id: str) -> None:
    _require_cedule_env()

    response = http_session.get(
        _service_url(base_url, f"/customers/{customer_id}/assets"),
        timeout=default_timeout,
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["data"], f"Expected service assets for customer {customer_id}"
    for item in payload["data"]:
        assert item["customer_id"].strip().upper() == customer_id.upper()



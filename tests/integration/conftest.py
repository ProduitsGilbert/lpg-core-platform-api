import os

import pytest
import requests

BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:3003").rstrip("/")
DEFAULT_TIMEOUT = int(os.environ.get("TEST_HTTP_TIMEOUT", "120"))


@pytest.fixture(scope="session")
def base_url() -> str:
    return BASE_URL


@pytest.fixture(scope="session")
def default_timeout() -> int:
    return DEFAULT_TIMEOUT


@pytest.fixture(scope="session")
def http_session() -> requests.Session:
    session = requests.Session()
    yield session
    session.close()


@pytest.fixture(scope="session", autouse=True)
def ensure_api_is_reachable(http_session: requests.Session, base_url: str, default_timeout: int) -> None:
    try:
        response = http_session.get(f"{base_url}/healthz", timeout=default_timeout)
        response.raise_for_status()
    except Exception as exc:  # pragma: no cover - skip when API unavailable
        pytest.skip(f"API health check failed ({exc}); ensure the service is running before tests.")

from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.api.v1.erp.business_central import get_vendor_contact_service
from app.domain.erp.vendor_contact_service import VendorContactInfo


@pytest.fixture(autouse=True)
def clear_dependency_overrides():
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _mock_vendor_contact_service():
    service = SimpleNamespace(get_vendor_contact=AsyncMock())
    app.dependency_overrides[get_vendor_contact_service] = lambda: service
    return service


def test_vendor_email_contact_success(client):
    contact = VendorContactInfo(
        vendor_id="TEST01",
        email="test@example.com",
        language="English",
        language_code="ENU",
        name="Test Vendor",
        communication_language="English",
    )
    service = _mock_vendor_contact_service()
    service.get_vendor_contact.return_value = contact

    response = client.get("/api/v1/erp/bc/vendor-email-contact", params={"vendor_no": "TEST01"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["vendor_id"] == "TEST01"
    assert payload["email"] == "test@example.com"
    assert payload["language"] == "English"
    service.get_vendor_contact.assert_awaited_once_with("TEST01")


def test_vendor_email_contact_invalid_vendor(client):
    service = _mock_vendor_contact_service()
    service.get_vendor_contact.side_effect = ValueError("vendor_no must be provided.")

    response = client.get("/api/v1/erp/bc/vendor-email-contact", params={"vendor_no": "BAD"})

    assert response.status_code == 400
    detail = response.json()["detail"]["error"]
    assert detail["code"] == "INVALID_VENDOR"
    assert "must be provided" in detail["message"]
    service.get_vendor_contact.assert_awaited_once()


def test_vendor_email_contact_http_error(client):
    service = _mock_vendor_contact_service()
    request = httpx.Request("GET", "https://example.com")
    response = httpx.Response(status_code=500, request=request)
    service.get_vendor_contact.side_effect = httpx.HTTPStatusError(
        "Upstream failure", request=request, response=response
    )

    response_obj = client.get("/api/v1/erp/bc/vendor-email-contact", params={"vendor_no": "FAIL"})

    assert response_obj.status_code == 502
    detail = response_obj.json()["detail"]["error"]
    assert detail["code"] == "BC_VENDOR_CONTACT_ERROR"
    service.get_vendor_contact.assert_awaited_once_with("FAIL")

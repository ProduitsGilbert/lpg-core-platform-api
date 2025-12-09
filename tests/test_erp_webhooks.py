from fastapi.testclient import TestClient
import pytest

from app.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_items_webhook_validation_returns_token(client: TestClient) -> None:
    response = client.get(
        "/api/v1/erp/webhooks/items",
        params={"validationtoken": "validation-token"},
    )

    assert response.status_code == 200
    assert response.text == "validation-token"
    assert response.headers.get("content-type", "").startswith("text/plain")


def test_items_webhook_validation_without_token(client: TestClient) -> None:
    response = client.get("/api/v1/erp/webhooks/items")

    assert response.status_code == 200
    assert response.text == ""


def test_items_webhook_notifications_acknowledged(client: TestClient) -> None:
    payload = [
        {
            "subscriptionId": "sub-123",
            "changeType": "Updated",
            "resource": "/items(ITEM-001)",
        }
    ]

    response = client.post("/api/v1/erp/webhooks/items", json=payload)

    assert response.status_code == 202
    assert response.text == ""

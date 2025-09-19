from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.domain.erp.models import ItemResponse
from app.errors import ERPConflict


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _setup_item_service(monkeypatch, **overrides):
    service = SimpleNamespace(
        update_item=AsyncMock(),
        create_purchased_item=AsyncMock(),
        create_manufactured_item=AsyncMock(),
    )
    for name, value in overrides.items():
        setattr(service, name, value)
    monkeypatch.setattr("app.api.v1.erp.items.ItemService", lambda: service)
    monkeypatch.setattr("app.api.v1.erp.items.get_item_service", lambda: service)
    return service


def test_update_item_fields_success(client, monkeypatch):
    item_response = ItemResponse(
        id="ITEM-100",
        description="Updated item",
        unit_of_measure="EA"
    )
    service = _setup_item_service(monkeypatch)
    service.update_item.return_value = item_response

    payload = {
        "updates": [
            {"field": "Description", "new_value": "Updated item"}
        ]
    }
    response = client.post("/api/v1/erp/items/ITEM-100/update", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["description"] == "Updated item"

    args, kwargs = service.update_item.await_args
    assert args[0] == "ITEM-100"
    assert len(args[1]) == 1
    assert args[1][0].field == "Description"
    assert args[1][0].new_value == "Updated item"


def test_create_purchased_item_success(client, monkeypatch):
    item_response = ItemResponse(
        id="ITEM-200",
        description="Template copy",
        unit_of_measure="EA"
    )
    service = _setup_item_service(monkeypatch)
    service.create_purchased_item.return_value = item_response

    response = client.post("/api/v1/erp/items/purchased", json={"item_no": "ITEM-200"})

    assert response.status_code == 201
    body = response.json()
    assert body["data"]["id"] == "ITEM-200"
    service.create_purchased_item.assert_awaited_once_with("ITEM-200")


def test_create_manufactured_item_conflict(client, monkeypatch):
    service = _setup_item_service(monkeypatch)
    service.create_manufactured_item.side_effect = ERPConflict("Item exists")

    response = client.post("/api/v1/erp/items/manufactured", json={"item_no": "ITEM-123"})

    assert response.status_code == 409
    body = response.json()
    error = body["detail"]["error"]
    assert error["code"] == "ERP_CONFLICT"
    assert "Item exists" in error["message"]
    service.create_manufactured_item.assert_awaited_once_with("ITEM-123")

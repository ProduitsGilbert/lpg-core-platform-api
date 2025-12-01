from types import SimpleNamespace
from unittest.mock import AsyncMock
from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.domain.erp.models import (
    ItemResponse,
    TariffCalculationResponse,
    TariffMaterialResponse,
    TariffSummaryResponse,
    ItemAvailabilityResponse,
    ItemAvailabilityTimelineEntry,
    ItemAttributesResponse,
    ItemAttributeValueEntry,
)
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


def _setup_item_attribute_service(monkeypatch, response: ItemAttributesResponse):
    service = SimpleNamespace(
        get_item_attributes=AsyncMock(return_value=response),
    )
    monkeypatch.setattr("app.api.v1.erp.items.ItemAttributeService", lambda: service)
    monkeypatch.setattr("app.api.v1.erp.items.get_item_attribute_service", lambda: service)
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


def test_get_item_attributes_success(client, monkeypatch):
    response_model = ItemAttributesResponse(
        item_id="0410604",
        attributes=[
            ItemAttributeValueEntry(
                attribute_id=2,
                attribute_name="Matériel",
                attribute_type="Option",
                value_id=372,
                value="HARDOX-450",
            ),
            ItemAttributeValueEntry(
                attribute_id=5,
                attribute_name="Epaisseur",
                attribute_type="Decimal",
                value_id=90,
                value="0.375",
            ),
        ],
    )
    service = _setup_item_attribute_service(monkeypatch, response_model)

    response = client.get("/api/v1/erp/items/0410604/attributes")

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["item_id"] == "0410604"
    assert payload["attributes"][0]["value"] == "HARDOX-450"
    service.get_item_attributes.assert_awaited_once_with("0410604")


def _setup_tariff_service(monkeypatch, response: TariffCalculationResponse):
    service = SimpleNamespace(calculate=AsyncMock(return_value=response))
    monkeypatch.setattr("app.api.v1.erp.items.TariffCalculationService", lambda: service)
    monkeypatch.setattr("app.api.v1.erp.items.get_tariff_service", lambda: service)
    return service


def _setup_availability_service(monkeypatch, response: ItemAvailabilityResponse):
    service = SimpleNamespace(get_availability=AsyncMock(return_value=response))
    monkeypatch.setattr("app.api.v1.erp.items.ItemAvailabilityService", lambda: service)
    monkeypatch.setattr("app.api.v1.erp.items.get_availability_service", lambda: service)
    return service


def _sample_tariff_response() -> TariffCalculationResponse:
    summary = TariffSummaryResponse(
        total_materials=1,
        calculated_materials=1,
        total_weight_kg=10.0,
        total_weight_with_scrap_kg=11.0,
        total_cost_cad=100.0,
        total_cost_usd=74.0,
        exchange_rate=0.74,
    )
    material = TariffMaterialResponse(
        item_no="MAT-1",
        description="Steel Plate",
        material_type="plate",
        quantity=1.0,
        scrap_percent=5.0,
        dimensions={"thickness": 1.0},
        weight_per_piece_lbs=20.0,
        weight_per_piece_kg=9.07184,
        total_weight_lbs=20.0,
        total_weight_kg=9.07184,
        total_with_scrap_lbs=21.0,
        total_with_scrap_kg=9.525432,
        standard_cost_cad=50.0,
        total_cost_cad=50.0,
        total_cost_usd=37.0,
        vendor_no="VENDOR-1",
        vendor_item_no="V1",
    )
    return TariffCalculationResponse(
        item_id="PARENT",
        production_bom_no="BOM-1",
        summary=summary,
        materials=[material],
        parent_country_of_melt_and_pour="USA",
        parent_country_of_manufacture="USA",
        report="Full report text",
    )


def _sample_availability_response(include_timeline: bool) -> ItemAvailabilityResponse:
    timeline = None
    if include_timeline:
        timeline = [
            ItemAvailabilityTimelineEntry(
                period_start=date(2024, 11, 1),
                incoming_qty=Decimal("5"),
                outgoing_qty=Decimal("2"),
                projected_available=Decimal("13"),
                incoming_jobs=["JOB-IN-1"],
                outgoing_jobs=["JOB-OUT-1"],
            )
        ]
    return ItemAvailabilityResponse(
        item_id="1510136",
        as_of_date=date(2024, 11, 12),
        current_inventory=Decimal("10"),
        total_incoming=Decimal("5"),
        total_outgoing=Decimal("2"),
        projected_available=Decimal("13"),
        details_included=include_timeline,
        timeline=timeline,
    )


def test_get_item_tariff_summary_only(client, monkeypatch):
    response_model = _sample_tariff_response()
    service = _setup_tariff_service(monkeypatch, response_model)

    response = client.get("/api/v1/erp/items/PARENT/tariff")
    assert response.status_code == 200
    body = response.json()["data"]
    assert body["summary"]["total_weight_kg"] == 10.0
    assert body.get("materials") is None
    assert body.get("report") is None
    service.calculate.assert_awaited_once_with("PARENT")


def test_get_item_tariff_with_details(client, monkeypatch):
    response_model = _sample_tariff_response()
    service = _setup_tariff_service(monkeypatch, response_model)

    response = client.get("/api/v1/erp/items/PARENT/tariff?include_details=true")
    assert response.status_code == 200
    body = response.json()["data"]
    assert body["materials"][0]["item_no"] == "MAT-1"
    assert body["report"] == "Full report text"
    service.calculate.assert_awaited_once_with("PARENT")


def test_get_item_availability_summary_only(client, monkeypatch):
    response_model = _sample_availability_response(include_timeline=False)
    service = _setup_availability_service(monkeypatch, response_model)

    response = client.get("/api/v1/erp/items/1510136/availability")
    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["projected_available"] == 13
    assert payload["timeline"] is None
    service.get_availability.assert_awaited_once_with(
        item_id="1510136", include_details=False, exclude_minimum_stock=False
    )


def test_get_item_availability_with_details(client, monkeypatch):
    response_model = _sample_availability_response(include_timeline=True)
    service = _setup_availability_service(monkeypatch, response_model)

    response = client.get("/api/v1/erp/items/1510136/availability?details=true")
    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["details_included"] is True
    assert payload["timeline"][0]["incoming_qty"] == 5
    assert payload["timeline"][0]["incoming_jobs"][0] == "JOB-IN-1"
    assert payload["timeline"][0]["outgoing_jobs"][0] == "JOB-OUT-1"
    service.get_availability.assert_awaited_once_with(
        item_id="1510136", include_details=True, exclude_minimum_stock=False
    )


def test_get_item_availability_excluding_minimum_stock(client, monkeypatch):
    response_model = _sample_availability_response(include_timeline=False)
    service = _setup_availability_service(monkeypatch, response_model)

    response = client.get("/api/v1/erp/items/1510136/availability?exclude_minimum_stock=true")
    assert response.status_code == 200
    service.get_availability.assert_awaited_once_with(
        item_id="1510136", include_details=False, exclude_minimum_stock=True
    )

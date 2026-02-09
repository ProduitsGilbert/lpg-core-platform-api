from types import SimpleNamespace
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.domain.erp.models import (
    ProductionItemInfo,
    ProductionBomCostShareResponse,
    ProductionRoutingCostResponse,
    ProductionRoutingLineCost,
)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _setup_service(monkeypatch, **overrides):
    service = SimpleNamespace(**overrides)
    monkeypatch.setattr("app.api.v1.erp.production.ProductionService", lambda: service)
    monkeypatch.setattr("app.api.v1.erp.production.get_production_service", lambda: service)
    return service


def test_get_production_item(client, monkeypatch):
    expected = ProductionItemInfo(
        item_no="7305101",
        description="Test Item",
        routing_no="ROUT-01",
        production_bom_no="BOM-01",
        base_unit_of_measure="EA",
        unit_cost=Decimal("10"),
        unit_price=Decimal("25"),
    )
    _setup_service(monkeypatch, get_item_info=AsyncMock(return_value=expected))

    resp = client.get("/api/v1/erp/production/items/7305101")
    assert resp.status_code == 200
    body = resp.json()["data"]
    assert body["item_no"] == "7305101"
    assert body["routing_no"] == "ROUT-01"


def test_get_bom_cost_share(client, monkeypatch):
    response = ProductionBomCostShareResponse(
        item_no="7305101",
        routing_no="ROUT-01",
        production_bom_no="BOM-01",
        lines=[],
    )
    _setup_service(monkeypatch, get_bom_cost_shares=AsyncMock(return_value=response))

    resp = client.get("/api/v1/erp/production/items/7305101/bom-cost-share")
    assert resp.status_code == 200
    body = resp.json()["data"]
    assert body["item_no"] == "7305101"
    assert body["lines"] == []


def test_get_routing_costs(client, monkeypatch):
    line = ProductionRoutingLineCost(
        routing_no="ROUT-01",
        operation_no="10",
        sequence_no=10,
        type="Work Center",
        work_center_no="40210",
        description="Saw",
        quantity_per=Decimal("1"),
        unit_of_measure_code="MIN",
        setup_time_minutes=Decimal("5"),
        run_time_minutes=Decimal("10"),
        cost_per_minute=Decimal("0.5"),
        setup_cost=Decimal("2.5"),
        run_cost=Decimal("5.0"),
        total_cost=Decimal("7.5"),
    )
    response = ProductionRoutingCostResponse(
        item_no="7305101",
        routing_no="ROUT-01",
        production_bom_no="BOM-01",
        lines=[line],
        total_setup_cost=Decimal("2.5"),
        total_run_cost=Decimal("5.0"),
        total_cost=Decimal("7.5"),
    )
    _setup_service(monkeypatch, get_routing_costs=AsyncMock(return_value=response))

    resp = client.get("/api/v1/erp/production/items/7305101/routing-costs")
    assert resp.status_code == 200
    body = resp.json()["data"]
    assert body["routing_no"] == "ROUT-01"
    assert len(body["lines"]) == 1

from types import SimpleNamespace
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.domain.erp.models import (
    ProductionItemInfo,
    ProductionBomCostShareResponse,
    ProductionCostingGroupedItemResponse,
    ProductionCostingScanResponse,
    ProductionCostingSourceSnapshot,
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


def _setup_costing_service(monkeypatch, **overrides):
    service = SimpleNamespace(**overrides)
    monkeypatch.setattr("app.api.v1.erp.production.ProductionCostingSnapshotService", lambda: service)
    monkeypatch.setattr(
        "app.api.v1.erp.production.get_production_costing_snapshot_service",
        lambda: service,
    )
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


def test_run_costing_scan(client, monkeypatch):
    result = ProductionCostingScanResponse(
        scan_id="8d71cd5f-53c6-460c-9eb0-ab7a8dcf8d40",
        scan_mode="delta",
        trigger_source="manual",
        status="success",
        routing_headers_count=2,
        bom_headers_count=1,
        routing_lines_count=45,
        bom_lines_count=31,
        total_lines_count=76,
    )
    mock_run_scan = AsyncMock(return_value=result)
    _setup_costing_service(monkeypatch, run_scan=mock_run_scan)

    resp = client.post("/api/v1/erp/production/costing/scans", json={"full_refresh": False})
    assert resp.status_code == 200
    body = resp.json()["data"]
    assert body["scan_id"] == result.scan_id
    assert body["total_lines_count"] == 76
    mock_run_scan.assert_awaited_once_with(full_refresh=False, trigger_source="manual")


def test_get_grouped_costing_snapshot(client, monkeypatch):
    routing_snapshot = ProductionCostingSourceSnapshot(
        source_type="routing",
        source_no="0115105-05",
        base_item_no="0115105",
        revision="05",
        scan_id="10000000-0000-0000-0000-000000000000",
        line_count=2,
        lines=[{"Operation_No": "10"}, {"Operation_No": "20"}],
    )
    bom_snapshot = ProductionCostingSourceSnapshot(
        source_type="bom",
        source_no="0115105-05",
        base_item_no="0115105",
        revision="05",
        scan_id="10000000-0000-0000-0000-000000000000",
        line_count=3,
        lines=[{"Line_No": "10000"}],
    )
    grouped = ProductionCostingGroupedItemResponse(
        item_no="0115105",
        latest_only=True,
        include_lines=True,
        total_versions=2,
        routing_versions=[routing_snapshot],
        bom_versions=[bom_snapshot],
    )
    mock_get_grouped = AsyncMock(return_value=grouped)
    _setup_costing_service(monkeypatch, get_grouped_item_snapshot=mock_get_grouped)

    resp = client.get("/api/v1/erp/production/costing/items/0115105")
    assert resp.status_code == 200
    body = resp.json()["data"]
    assert body["item_no"] == "0115105"
    assert body["total_versions"] == 2
    assert len(body["routing_versions"]) == 1
    mock_get_grouped.assert_awaited_once_with(
        item_no="0115105",
        latest_only=True,
        include_lines=True,
    )

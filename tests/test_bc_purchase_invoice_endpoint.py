from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

import app.api.v1.erp.business_central as bc_module
from app.api.v1.erp.business_central import get_odata_service
from app.main import app


def _client() -> TestClient:
    return TestClient(app)


def _override_odata_service(service: SimpleNamespace) -> None:
    app.dependency_overrides[get_odata_service] = lambda: service


@contextmanager
def _noop_span(*_args, **_kwargs):
    yield


@pytest.fixture(autouse=True)
def _disable_logfire():
    app.dependency_overrides.clear()
    original_span = bc_module.logfire.span
    bc_module.logfire.span = _noop_span
    try:
        yield
    finally:
        bc_module.logfire.span = original_span
        app.dependency_overrides.clear()


def test_list_purchase_invoices_with_filters() -> None:
    client = _client()
    service = SimpleNamespace(fetch_collection=AsyncMock(return_value=[{"No": "PI-0001"}]))
    _override_odata_service(service)

    try:
        response = client.get(
            "/api/v1/erp/bc/purchase-invoices",
            params={"no": "PI-0001", "vendor_no": "V-100", "top": 5},
        )
    finally:
        app.dependency_overrides.pop(get_odata_service, None)

    assert response.status_code == 200, response.text
    assert response.json() == [{"No": "PI-0001"}]
    service.fetch_collection.assert_awaited_once_with(
        "PurchaseInvoices?$filter=No eq 'PI-0001' and Buy_from_Vendor_No eq 'V-100'&$top=5",
        filter_field=None,
        filter_value=None,
        top=None,
    )


def test_list_purchase_invoice_lines() -> None:
    client = _client()
    service = SimpleNamespace(fetch_collection=AsyncMock(return_value=[{"Document_No": "PI-0001"}]))
    _override_odata_service(service)

    try:
        response = client.get("/api/v1/erp/bc/purchase-invoices/PI-0001/lines", params={"top": 2})
    finally:
        app.dependency_overrides.pop(get_odata_service, None)

    assert response.status_code == 200, response.text
    assert response.json() == [{"Document_No": "PI-0001"}]
    service.fetch_collection.assert_awaited_once_with(
        "PurchaseInvoiceLines?$filter=Document_No eq 'PI-0001'&$top=2",
        filter_field=None,
        filter_value=None,
        top=None,
    )


def test_create_purchase_invoice_success() -> None:
    client = _client()
    service = SimpleNamespace(
        create_record=AsyncMock(
            side_effect=[
                {"SystemId": "guid-1", "@odata.etag": 'W/"1"', "No": "PI-0001"},
                {"SystemId": "line-1", "Document_No": "PI-0001", "Line_No": 10000},
                {"SystemId": "line-2", "Document_No": "PI-0001", "Line_No": 20000},
            ]
        ),
        update_record=AsyncMock(return_value={"SystemId": "guid-1", "No": "PI-0001"}),
    )
    _override_odata_service(service)

    try:
        response = client.post(
            "/api/v1/erp/bc/purchase-invoices",
            json={
                "vendor_no": "V-100",
                "vendor_invoice_no": "SUP-INV-55",
                "posting_date": "2026-03-04",
                "due_date": "2026-03-15",
                "lines": [
                    {
                        "line_type": "Item",
                        "no": "ITEM-100",
                        "quantity": 3,
                        "direct_unit_cost_excl_tax": 12.5,
                    },
                    {
                        "line_type": "G/L Account",
                        "no": "6000",
                        "quantity": 1,
                        "direct_unit_cost_excl_tax": 99.99,
                    },
                ],
            },
        )
    finally:
        app.dependency_overrides.pop(get_odata_service, None)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["invoice_no"] == "PI-0001"
    assert len(body["lines"]) == 2

    assert service.create_record.await_count == 3
    first_call = service.create_record.await_args_list[0]
    assert first_call.args == ("PurchaseInvoices", {})

    service.update_record.assert_awaited_once_with(
        "PurchaseInvoices",
        "guid-1",
        {
            "Buy_from_Vendor_No": "V-100",
            "Vendor_Invoice_No": "SUP-INV-55",
            "Posting_Date": "2026-03-04",
            "Due_Date": "2026-03-15",
        },
        etag='W/"1"',
    )

    second_call = service.create_record.await_args_list[1]
    assert second_call.args == (
        "PurchaseInvoiceLines",
        {
            "Document_No": "PI-0001",
            "Type": "Item",
            "No": "ITEM-100",
            "Quantity": 3.0,
            "Direct_Unit_Cost_Excl_Tax": 12.5,
        },
    )

    third_call = service.create_record.await_args_list[2]
    assert third_call.args == (
        "PurchaseInvoiceLines",
        {
            "Document_No": "PI-0001",
            "Type": "G/L Account",
            "No": "6000",
            "Quantity": 1.0,
            "Direct_Unit_Cost_Excl_Tax": 99.99,
        },
    )


def test_create_purchase_invoice_missing_system_id_returns_502() -> None:
    client = _client()
    service = SimpleNamespace(
        create_record=AsyncMock(return_value={"No": "PI-0001"}),
        update_record=AsyncMock(),
    )
    _override_odata_service(service)

    try:
        response = client.post(
            "/api/v1/erp/bc/purchase-invoices",
            json={
                "vendor_no": "V-100",
                "vendor_invoice_no": "SUP-INV-55",
                "posting_date": "2026-03-04",
                "due_date": "2026-03-15",
                "lines": [
                    {
                        "line_type": "Item",
                        "no": "ITEM-100",
                        "quantity": 1,
                        "direct_unit_cost_excl_tax": 2,
                    }
                ],
            },
        )
    finally:
        app.dependency_overrides.pop(get_odata_service, None)

    assert response.status_code == 502, response.text
    assert response.json()["detail"]["error"]["code"] == "BC_INVALID_RESPONSE"
    service.update_record.assert_not_awaited()

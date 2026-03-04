from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi.testclient import TestClient

from app.api.v1.erp.business_central import get_odata_service
from app.main import app


@pytest.fixture(autouse=True)
def clear_dependency_overrides():
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_get_posted_sales_invoice_by_tracking_success(client: TestClient):
    service = SimpleNamespace(fetch_collection=AsyncMock())

    async def _fetch_collection(resource, *, filter_field=None, filter_value=None, top=None):
        _ = top
        if (
            resource == "PostedSalesInvoices"
            and filter_field == "Package_Tracking_No"
            and filter_value == "335568694913"
        ):
            return [
                {
                    "No": "INV036928",
                    "Package_Tracking_No": "335568694913",
                    "Amount_Excl_Tax": 1000.0,
                    "Amount_Including_VAT": 1149.0,
                    "Currency_Code": "CAD",
                }
            ]
        if (
            resource == "PostedSalesInvoiceLines"
            and filter_field == "Document_No"
            and filter_value == "INV036928"
        ):
            return [
                {
                    "Document_No": "INV036928",
                    "No": "41800",
                    "Type": "G/L Account",
                    "Description": "Transport",
                    "Line_Amount_Excl_Tax": 85.5,
                },
                {
                    "Document_No": "INV036928",
                    "No": "10010",
                    "Type": "Item",
                    "Line_Amount_Excl_Tax": 914.5,
                },
            ]
        return []

    service.fetch_collection.side_effect = _fetch_collection
    app.dependency_overrides[get_odata_service] = lambda: service

    response = client.get(
        "/api/v1/erp/bc/posted-sales-invoices/by-tracking",
        params={"tracking_number": ":335568694913"},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["tracking_number"] == "335568694913"
    assert payload["matches_count"] == 1
    match = payload["matches"][0]
    assert match["invoice_no"] == "INV036928"
    assert match["sales_order_totals"]["amount_excl_tax"] == 1000.0
    assert match["transport_charge"]["amount_excl_tax"] == 85.5
    assert match["transport_charge"]["line"]["No"] == "41800"
    assert len(match["lines"]) == 2


def test_get_posted_sales_invoice_by_tracking_not_found(client: TestClient):
    service = SimpleNamespace(fetch_collection=AsyncMock(return_value=[]))
    app.dependency_overrides[get_odata_service] = lambda: service

    response = client.get(
        "/api/v1/erp/bc/posted-sales-invoices/by-tracking",
        params={"tracking_number": "000000000000"},
    )

    assert response.status_code == 404, response.text
    payload = response.json()
    assert payload["detail"]["error"]["code"] == "BC_POSTED_SALES_INVOICE_NOT_FOUND"
    assert payload["detail"]["error"]["tracking_number"] == "000000000000"


def test_get_posted_sales_invoice_by_tracking_falls_back_to_headers_resource(client: TestClient):
    service = SimpleNamespace(fetch_collection=AsyncMock())

    async def _fetch_collection(resource, *, filter_field=None, filter_value=None, top=None):
        _ = top
        if resource == "PostedSalesInvoices":
            request = httpx.Request("GET", "https://example.local/PostedSalesInvoices")
            response = httpx.Response(404, request=request)
            raise httpx.HTTPStatusError("Not found", request=request, response=response)

        if (
            resource == "PostedSalesInvoiceHeaders"
            and filter_field == "Package_Tracking_No"
            and filter_value == "335568694913"
        ):
            return [{"No": "INV036928", "Package_Tracking_No": "335568694913"}]

        if (
            resource == "PostedSalesInvoiceLines"
            and filter_field == "Document_No"
            and filter_value == "INV036928"
        ):
            return [{"No": "41800", "Line_Amount_Excl_Tax": 42.0}]

        return []

    service.fetch_collection.side_effect = _fetch_collection
    app.dependency_overrides[get_odata_service] = lambda: service

    response = client.get(
        "/api/v1/erp/bc/posted-sales-invoices/by-tracking",
        params={"tracking_number": "335568694913"},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["matches_count"] == 1
    assert payload["matches"][0]["invoice_no"] == "INV036928"
    assert payload["matches"][0]["transport_charge"]["amount_excl_tax"] == 42.0

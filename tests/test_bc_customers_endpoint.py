from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.api.v1.erp import business_central as bc_api
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


def _mock_odata_service(*, customers, default_dimensions):
    service = SimpleNamespace(fetch_collection=AsyncMock(), fetch_collection_paged=AsyncMock())

    async def _fetch_collection(resource, *, filter_field=None, filter_value=None, top=None):
        _ = top
        if resource == "Customers":
            if filter_field == "No" and filter_value is not None:
                return [row for row in customers if str(row.get("No")) == str(filter_value)]
            return customers
        if resource in {"ShipToAddress", "ShipToAddresses", "Ship_to_Address", "Ship_to_Addresses"}:
            return []
        return []

    async def _fetch_collection_paged(resource, **kwargs):
        _ = kwargs
        if resource.startswith("DefaultDimensions?%24filter="):
            return default_dimensions
        return []

    service.fetch_collection.side_effect = _fetch_collection
    service.fetch_collection_paged.side_effect = _fetch_collection_paged
    app.dependency_overrides[get_odata_service] = lambda: service
    return service


def test_list_customers_includes_division(client):
    _mock_odata_service(
        customers=[{"No": "CUST01", "Name": "Customer 01"}],
        default_dimensions=[
            {
                "No": "CUST01",
                "Table_ID": 18,
                "Dimension_Code": "DIVISION",
                "Dimension_Value_Code": "CONST",
            }
        ],
    )

    response = client.get("/api/v1/erp/bc/customers", params={"no": "CUST01"})

    assert response.status_code == 200, response.text
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["customer_no"] == "CUST01"
    assert payload[0]["division"] == "CONST"


def test_list_customers_sets_division_to_null_when_missing(client):
    _mock_odata_service(
        customers=[{"No": "CUST01", "Name": "Customer 01"}],
        default_dimensions=[
            {
                "No": "CUST01",
                "Table_ID": 18,
                "Dimension_Code": "REGION",
                "Dimension_Value_Code": "CAN-QC",
            }
        ],
    )

    response = client.get("/api/v1/erp/bc/customers", params={"no": "CUST01"})

    assert response.status_code == 200, response.text
    payload = response.json()
    assert len(payload) == 1
    assert "division" in payload[0]
    assert payload[0]["division"] is None


def test_list_customers_regenerate_cache_seeds_without_geocoding(client, monkeypatch):
    _mock_odata_service(
        customers=[
            {
                "No": "CUST01",
                "Name": "Customer 01",
                "Address": "123 Main St",
                "City": "Montreal",
                "Post_Code": "H1H1H1",
                "Country_Region_Code": "CA",
            }
        ],
        default_dimensions=[],
    )
    mark_cached_without_geocode = AsyncMock()
    schedule_refresh = AsyncMock()
    monkeypatch.setattr(
        bc_api.customer_geocode_cache,
        "mark_cached_without_geocode",
        mark_cached_without_geocode,
    )
    monkeypatch.setattr(
        bc_api.customer_geocode_cache,
        "schedule_refresh",
        schedule_refresh,
    )

    response = client.get(
        "/api/v1/erp/bc/customers",
        params={"no": "CUST01", "regenerate_cache": "true"},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert len(payload) == 1
    mark_cached_without_geocode.assert_awaited()
    schedule_refresh.assert_not_awaited()

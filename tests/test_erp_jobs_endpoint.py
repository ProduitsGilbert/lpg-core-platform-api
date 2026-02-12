from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from app.api.v1.erp.jobs import get_odata_service
from app.main import app


def _client() -> TestClient:
    return TestClient(app)


def test_list_job_default_dimensions_by_job_no() -> None:
    client = _client()
    stub_service = type("StubODataService", (), {})()
    stub_service.fetch_collection = AsyncMock(
        return_value=[
            {
                "Table_ID": 167,
                "No": "GIM1136",
                "Dimension_Code": "REGION",
                "Dimension_Value_Code": "CAN-QC",
            },
            {
                "Table_ID": 167,
                "No": "GIM1136",
                "Dimension_Code": "DIVISION",
                "Dimension_Value_Code": "CONST",
            },
        ]
    )

    app.dependency_overrides[get_odata_service] = lambda: stub_service
    try:
        response = client.get("/api/v1/erp/jobs/default-dimensions?job_no=GIM1136")
    finally:
        app.dependency_overrides.pop(get_odata_service, None)

    assert response.status_code == 200, response.text
    payload = response.json()
    assert len(payload) == 2
    assert payload[0]["No"] == "GIM1136"
    stub_service.fetch_collection.assert_awaited_once_with("DefaultDimensions?$filter=No eq 'GIM1136'")


def test_list_job_default_dimensions_with_dimension_filter() -> None:
    client = _client()
    stub_service = type("StubODataService", (), {})()
    stub_service.fetch_collection = AsyncMock(
        return_value=[
            {
                "Table_ID": 167,
                "No": "GIM1136",
                "Dimension_Code": "DIVISION",
                "Dimension_Value_Code": "CONST",
            }
        ]
    )

    app.dependency_overrides[get_odata_service] = lambda: stub_service
    try:
        response = client.get(
            "/api/v1/erp/jobs/default-dimensions?job_no=GIM1136&dimension_code=DIVISION&top=10"
        )
    finally:
        app.dependency_overrides.pop(get_odata_service, None)

    assert response.status_code == 200, response.text
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["Dimension_Code"] == "DIVISION"
    stub_service.fetch_collection.assert_awaited_once_with(
        "DefaultDimensions?$filter=No eq 'GIM1136' and Dimension_Code eq 'DIVISION'&$top=10"
    )

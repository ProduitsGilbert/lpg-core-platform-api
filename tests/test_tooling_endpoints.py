from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient

from app.api.v1.tooling.router import (
    get_future_tooling_need_service,
    get_tooling_usage_history_service,
)
from app.main import app


def _client() -> TestClient:
    return TestClient(app)


def test_get_future_tooling_needs_endpoint() -> None:
    client = _client()
    stub = MagicMock()
    stub.get_future_needs = AsyncMock(
        return_value={
            "work_center_no": "40253",
            "snapshot_date": "2026-03-04",
            "generated_at": "2026-03-04T06:00:00",
            "from_cache": False,
            "source_order_count": 1,
            "unique_program_count": 1,
            "rows_count": 1,
            "tools_summary": [
                {
                    "tool_id": "1035",
                    "total_required_use_time_seconds": 203,
                    "rows_count": 1,
                    "program_count": 1,
                }
            ],
            "rows": [
                {
                    "no_prod_order": "M181334",
                    "prod_order_no": "M181334-1",
                    "line_no": 10000,
                    "status": "Released",
                    "due_date": "2026-02-09",
                    "routing_no": "8423166-01",
                    "routing_item_no": "8423166",
                    "op_code": "000500-2OP",
                    "operation_suffix": "2OP",
                    "nc_program": "8423166-2OP",
                    "part_no": "8423166",
                    "description": "Part A",
                    "input_quantity": 1,
                    "completed_quantity": 0,
                    "remaining_quantity": 1,
                    "tool_id": "1035",
                    "tool_use_time_seconds": 203,
                    "tool_description": "TOOL A",
                    "total_required_use_time_seconds": 203,
                }
            ],
        }
    )

    app.dependency_overrides[get_future_tooling_need_service] = lambda: stub
    try:
        response = client.get("/api/v1/tooling/future-needs?work_center_no=40253")
    finally:
        app.dependency_overrides.pop(get_future_tooling_need_service, None)

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["work_center_no"] == "40253"
    assert payload["rows_count"] == 1
    assert payload["tools_summary"][0]["tool_id"] == "1035"
    stub.get_future_needs.assert_awaited_once_with(work_center_no="40253", refresh=False)


def test_get_future_tooling_needs_endpoint_with_refresh() -> None:
    client = _client()
    stub = MagicMock()
    stub.get_future_needs = AsyncMock(
        return_value={
            "work_center_no": "40253",
            "snapshot_date": "2026-03-04",
            "generated_at": "2026-03-04T06:00:00",
            "from_cache": False,
            "source_order_count": 0,
            "unique_program_count": 0,
            "rows_count": 0,
            "tools_summary": [],
            "rows": [],
        }
    )

    app.dependency_overrides[get_future_tooling_need_service] = lambda: stub
    try:
        response = client.get("/api/v1/tooling/future-needs?work_center_no=40253&refresh=true")
    finally:
        app.dependency_overrides.pop(get_future_tooling_need_service, None)

    assert response.status_code == 200, response.text
    stub.get_future_needs.assert_awaited_once_with(work_center_no="40253", refresh=True)


def test_get_tooling_usage_history_endpoint() -> None:
    client = _client()
    stub = MagicMock()
    stub.get_usage_history = AsyncMock(
        return_value={
            "work_center_no": "40253",
            "machine_center": "DMC100",
            "start_date": "2025-03-05",
            "end_date": "2026-03-04",
            "generated_at": "2026-03-04T05:00:00+00:00",
            "from_cache": False,
            "source_entry_count": 1,
            "unique_program_count": 1,
            "rows_count": 1,
            "tools_summary": [
                {
                    "tool_id": "1035",
                    "total_estimated_use_time_seconds": 203,
                    "rows_count": 1,
                    "unique_program_count": 1,
                    "months_active": 1,
                }
            ],
            "monthly_summary": [
                {
                    "month": "2026-02",
                    "source_entries_count": 1,
                    "rows_count": 1,
                    "quantity_total": 1.0,
                    "estimated_use_time_seconds_total": 203,
                }
            ],
            "rows": [
                {
                    "posting_date": "2026-02-10",
                    "work_center_no": "40253",
                    "machine_center": "DMC100",
                    "order_no": "M181334-1",
                    "item_no": "8423166",
                    "operation_no": "000500-2OP",
                    "operation_suffix": "2OP",
                    "nc_program": "8423166-2OP",
                    "quantity": 1.0,
                    "tool_id": "1035",
                    "tool_use_time_seconds": 203,
                    "tool_description": "TOOL A",
                    "estimated_total_use_time_seconds": 203,
                }
            ],
        }
    )

    app.dependency_overrides[get_tooling_usage_history_service] = lambda: stub
    try:
        response = client.get(
            "/api/v1/tooling/history-usage?work_center_no=40253&machine_center=DMC100&months=12"
        )
    finally:
        app.dependency_overrides.pop(get_tooling_usage_history_service, None)

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["work_center_no"] == "40253"
    assert payload["machine_center"] == "DMC100"
    assert payload["rows_count"] == 1
    stub.get_usage_history.assert_awaited_once_with(
        work_center_no="40253",
        machine_center="DMC100",
        months=12,
        refresh=False,
    )


def test_get_fastems2_future_tooling_needs_endpoint() -> None:
    client = _client()
    stub = MagicMock()
    stub.get_future_needs = AsyncMock(
        return_value={
            "work_center_no": "40279",
            "snapshot_date": "2026-03-04",
            "generated_at": "2026-03-04T06:00:00",
            "from_cache": False,
            "source_order_count": 1,
            "unique_program_count": 1,
            "rows_count": 1,
            "tools_summary": [
                {
                    "tool_id": "5502",
                    "total_required_use_time_seconds": 13,
                    "rows_count": 1,
                    "program_count": 1,
                }
            ],
            "rows": [
                {
                    "no_prod_order": "M100001",
                    "prod_order_no": "M100001-1",
                    "line_no": 10000,
                    "status": "Released",
                    "due_date": "2026-03-10",
                    "routing_no": "8317032-01",
                    "routing_item_no": "8317032",
                    "op_code": "000500-1OP",
                    "operation_suffix": "1OP",
                    "nc_program": "8317032-1OP",
                    "part_no": "8317032",
                    "description": "Part B",
                    "input_quantity": 1,
                    "completed_quantity": 0,
                    "remaining_quantity": 1,
                    "tool_id": "5502",
                    "tool_use_time_seconds": 13,
                    "tool_description": "TOOL B",
                    "total_required_use_time_seconds": 13,
                }
            ],
        }
    )

    app.dependency_overrides[get_future_tooling_need_service] = lambda: stub
    try:
        response = client.get("/api/v1/tooling/fastems2/future-needs")
    finally:
        app.dependency_overrides.pop(get_future_tooling_need_service, None)

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["work_center_no"] == "40279"
    stub.get_future_needs.assert_awaited_once_with(
        work_center_no="40279",
        refresh=False,
        tool_source="fastems2",
    )


def test_get_fastems2_tooling_usage_history_endpoint() -> None:
    client = _client()
    stub = MagicMock()
    stub.get_usage_history = AsyncMock(
        return_value={
            "work_center_no": "40279",
            "machine_center": "FASTEMS2",
            "start_date": "2025-03-05",
            "end_date": "2026-03-04",
            "generated_at": "2026-03-04T05:00:00+00:00",
            "from_cache": False,
            "source_entry_count": 1,
            "unique_program_count": 1,
            "rows_count": 1,
            "tools_summary": [
                {
                    "tool_id": "5502",
                    "total_estimated_use_time_seconds": 26,
                    "rows_count": 1,
                    "unique_program_count": 1,
                    "months_active": 1,
                }
            ],
            "monthly_summary": [
                {
                    "month": "2026-02",
                    "source_entries_count": 1,
                    "rows_count": 1,
                    "quantity_total": 2.0,
                    "estimated_use_time_seconds_total": 26,
                }
            ],
            "rows": [
                {
                    "posting_date": "2026-02-10",
                    "work_center_no": "40279",
                    "machine_center": "FASTEMS2",
                    "order_no": "M100001-1",
                    "item_no": "8317032",
                    "operation_no": "000500-1OP",
                    "operation_suffix": "1OP",
                    "nc_program": "8317032-1OP",
                    "quantity": 2.0,
                    "tool_id": "5502",
                    "tool_use_time_seconds": 13,
                    "tool_description": "TOOL B",
                    "estimated_total_use_time_seconds": 26,
                }
            ],
        }
    )

    app.dependency_overrides[get_tooling_usage_history_service] = lambda: stub
    try:
        response = client.get("/api/v1/tooling/fastems2/history-usage")
    finally:
        app.dependency_overrides.pop(get_tooling_usage_history_service, None)

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["work_center_no"] == "40279"
    stub.get_usage_history.assert_awaited_once_with(
        work_center_no="40279",
        machine_center="FASTEMS2",
        months=12,
        refresh=False,
        tool_source="fastems2",
    )

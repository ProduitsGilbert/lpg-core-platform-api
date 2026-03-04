import datetime as dt

import pytest

from app.domain.tooling.usage_history_service import ToolingUsageHistoryService


class _StubERPClient:
    def __init__(self, rows):
        self.rows = rows
        self.calls = []

    async def _fetch_with_candidate_resources(self, *, resource_candidates, filter_clauses=None):
        self.calls.append((tuple(resource_candidates), tuple(filter_clauses or [])))
        return self.rows


class _StubNCProgramClient:
    def __init__(self, payload_by_program):
        self.payload_by_program = payload_by_program
        self.calls = []

    async def get_program_tools(self, program_name: str):
        self.calls.append(program_name)
        return self.payload_by_program.get(program_name, [])


class _NoCache:
    is_configured = False

    def register_pair(self, work_center_no: str, machine_center: str) -> None:
        _ = (work_center_no, machine_center)

    def get_snapshot(self, cache_key: str):
        _ = cache_key
        return None

    def upsert_snapshot(self, **kwargs):
        _ = kwargs
        return dt.datetime.now(dt.UTC)

    def prune_before(self, updated_before_iso: str) -> None:
        _ = updated_before_iso


class _CacheHit:
    is_configured = True

    def __init__(self, payload):
        self.payload = payload
        self.registered = []

    def register_pair(self, work_center_no: str, machine_center: str) -> None:
        self.registered.append((work_center_no, machine_center))

    def get_snapshot(self, cache_key: str):
        _ = cache_key
        return self.payload

    def upsert_snapshot(self, **kwargs):
        _ = kwargs
        raise AssertionError("upsert_snapshot should not be called on cache hit")

    def prune_before(self, updated_before_iso: str) -> None:
        _ = updated_before_iso


@pytest.mark.asyncio
async def test_tooling_usage_history_builds_tool_usage(monkeypatch) -> None:
    monkeypatch.setattr("app.domain.tooling.usage_history_service.tooling_usage_history_cache", _NoCache())
    erp_rows = [
        {
            "Posting_Date": "2026-02-10",
            "Work_Center_No": "40253",
            "Order_No": "M181334-1",
            "Order_Type": "Production",
            "Type": "Work Center",
            "Item_No": "8423166",
            "Operation_No": "000500-2OP",
            "Quantity": 2,
        },
        {
            "Posting_Date": "2026-02-12",
            "Work_Center_No": "40253",
            "Order_No": "M181335-1",
            "Order_Type": "Production",
            "Type": "Work Center",
            "Item_No": "8423166",
            "Operation_No": "000500-2OP",
            "Quantity": 1,
        },
    ]
    nc_payload = {
        "8423166-2OP": [
            {"TOOL_ID": "1035", "USE_TIME": 203, "DESCRIPTION": "TOOL A"},
            {"TOOL_ID": "1037", "USE_TIME": 227, "DESCRIPTION": "TOOL B"},
        ]
    }
    service = ToolingUsageHistoryService(
        erp_client=_StubERPClient(erp_rows),
        nc_program_client=_StubNCProgramClient(nc_payload),
    )

    result = await service.get_usage_history(
        work_center_no="40253",
        machine_center="DMC100",
        months=12,
        refresh=True,
    )

    assert result.work_center_no == "40253"
    assert result.machine_center == "DMC100"
    assert result.source_entry_count == 2
    assert result.unique_program_count == 1
    assert result.rows_count == 4

    tool_row = next(row for row in result.rows if row.order_no == "M181334-1" and row.tool_id == "1035")
    assert tool_row.nc_program == "8423166-2OP"
    assert tool_row.operation_suffix == "2OP"
    assert tool_row.estimated_total_use_time_seconds == 406

    summary_1035 = next(item for item in result.tools_summary if item.tool_id == "1035")
    assert summary_1035.total_estimated_use_time_seconds == 609
    assert summary_1035.rows_count == 2
    assert summary_1035.unique_program_count == 1

    month = next(item for item in result.monthly_summary if item.month == "2026-02")
    assert month.source_entries_count == 2
    assert month.rows_count == 4


@pytest.mark.asyncio
async def test_tooling_usage_history_uses_cache(monkeypatch) -> None:
    cached_payload = {
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
    cache = _CacheHit(cached_payload)
    monkeypatch.setattr("app.domain.tooling.usage_history_service.tooling_usage_history_cache", cache)
    service = ToolingUsageHistoryService(
        erp_client=_StubERPClient([]),
        nc_program_client=_StubNCProgramClient({}),
    )

    result = await service.get_usage_history(
        work_center_no="40253",
        machine_center="DMC100",
        months=12,
        refresh=False,
    )

    assert cache.registered == [("40253", "DMC100")]
    assert result.from_cache is True
    assert result.rows_count == 1


@pytest.mark.asyncio
async def test_tooling_usage_history_parses_fastems2_tool_payload(monkeypatch) -> None:
    monkeypatch.setattr("app.domain.tooling.usage_history_service.tooling_usage_history_cache", _NoCache())
    erp_rows = [
        {
            "Posting_Date": "2026-02-10",
            "Work_Center_No": "40279",
            "Order_No": "M200001-1",
            "Order_Type": "Production",
            "Type": "Work Center",
            "Item_No": "8317032",
            "Operation_No": "000500-1OP",
            "Quantity": 2,
        }
    ]
    nc_payload = {
        "8317032-1OP": [
            {"ToolCode": "5502", "Usage": 13, "Description": "FORET"},
        ]
    }
    service = ToolingUsageHistoryService(
        erp_client=_StubERPClient(erp_rows),
        nc_program_client=_StubNCProgramClient(nc_payload),
    )

    result = await service.get_usage_history(
        work_center_no="40279",
        machine_center="FASTEMS2",
        months=12,
        refresh=True,
        tool_source="fastems2",
    )

    row = next(item for item in result.rows if item.tool_id == "5502")
    assert row.tool_use_time_seconds == 13
    assert row.estimated_total_use_time_seconds == 26
    assert row.tool_description == "FORET"

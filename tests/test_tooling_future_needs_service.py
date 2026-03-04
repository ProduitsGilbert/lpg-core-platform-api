import datetime as dt

import pytest

from app.domain.tooling.future_needs_service import FutureToolingNeedService


class _StubProductionClient:
    def __init__(self, rows):
        self.rows = rows
        self.calls = []

    async def list_unfinished_routing_lines(self, work_center_no: str = "40253"):
        self.calls.append(work_center_no)
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

    def register_work_center(self, work_center_no: str) -> None:
        _ = work_center_no

    def get_snapshot(self, work_center_no: str, snapshot_date: str):
        _ = (work_center_no, snapshot_date)
        return None

    def upsert_snapshot(self, work_center_no: str, snapshot_date: str, payload):
        _ = (work_center_no, snapshot_date, payload)
        return dt.datetime.utcnow()

    def prune_before(self, snapshot_date_iso: str) -> None:
        _ = snapshot_date_iso


class _CacheHit:
    is_configured = True

    def __init__(self, payload):
        self.payload = payload
        self.requested = []

    def register_work_center(self, work_center_no: str) -> None:
        self.requested.append(work_center_no)

    def get_snapshot(self, work_center_no: str, snapshot_date: str):
        _ = (work_center_no, snapshot_date)
        return self.payload

    def upsert_snapshot(self, work_center_no: str, snapshot_date: str, payload):
        _ = (work_center_no, snapshot_date, payload)
        raise AssertionError("upsert_snapshot should not be called on cache hit")

    def prune_before(self, snapshot_date_iso: str) -> None:
        _ = snapshot_date_iso


@pytest.mark.asyncio
async def test_future_tooling_needs_builds_program_and_tool_usage(monkeypatch) -> None:
    monkeypatch.setattr("app.domain.tooling.future_needs_service.tooling_future_needs_cache", _NoCache())
    production_rows = [
        {
            "noProdOrder": "M181334",
            "prodOrderNo": "M181334-1",
            "lineNo": 10000,
            "status": "Released",
            "routingNo": "8423166-01",
            "itemNo": "8423166",
            "description": "Part A",
            "opCode": "000500-2OP",
            "inputQuantity": 3,
            "qtyfait": 1,
            "dueDate": "2026-02-09",
        },
        {
            "noProdOrder": "M181335",
            "prodOrderNo": "M181335-1",
            "lineNo": 10000,
            "status": "Released",
            "routingNo": "8423166-01",
            "itemNo": "8423166",
            "description": "Part A",
            "opCode": "000500-2OP",
            "inputQuantity": 2,
            "qtyfait": 0,
            "dueDate": "2026-02-10",
        },
    ]
    nc_payload = {
        "8423166-2OP": [
            {"TOOL_ID": "1035", "USE_TIME": 203, "DESCRIPTION": "TOOL A"},
            {"TOOL_ID": "1037", "USE_TIME": 227, "DESCRIPTION": "TOOL B"},
        ]
    }
    production_client = _StubProductionClient(production_rows)
    nc_client = _StubNCProgramClient(nc_payload)
    service = FutureToolingNeedService(
        production_client=production_client,
        nc_program_client=nc_client,
    )

    result = await service.get_future_needs(work_center_no="40253", refresh=True)

    assert production_client.calls == ["40253"]
    assert nc_client.calls == ["8423166-2OP"]
    assert result.work_center_no == "40253"
    assert result.unique_program_count == 1
    assert result.source_order_count == 2
    assert result.rows_count == 4

    tool_row = next(row for row in result.rows if row.no_prod_order == "M181334" and row.tool_id == "1035")
    assert tool_row.routing_item_no == "8423166"
    assert tool_row.operation_suffix == "2OP"
    assert tool_row.nc_program == "8423166-2OP"
    assert tool_row.remaining_quantity == 2
    assert tool_row.tool_use_time_seconds == 203
    assert tool_row.total_required_use_time_seconds == 406

    summary_1035 = next(item for item in result.tools_summary if item.tool_id == "1035")
    assert summary_1035.total_required_use_time_seconds == 812
    assert summary_1035.rows_count == 2
    assert summary_1035.program_count == 1


@pytest.mark.asyncio
async def test_future_tooling_needs_uses_daily_cache_when_available(monkeypatch) -> None:
    cached_payload = {
        "work_center_no": "40253",
        "snapshot_date": dt.date.today().isoformat(),
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
    cache = _CacheHit(cached_payload)
    monkeypatch.setattr("app.domain.tooling.future_needs_service.tooling_future_needs_cache", cache)

    production_client = _StubProductionClient([])
    nc_client = _StubNCProgramClient({})
    service = FutureToolingNeedService(
        production_client=production_client,
        nc_program_client=nc_client,
    )

    result = await service.get_future_needs(work_center_no="40253", refresh=False)

    assert cache.requested == ["40253"]
    assert production_client.calls == []
    assert nc_client.calls == []
    assert result.from_cache is True
    assert result.rows_count == 1


@pytest.mark.asyncio
async def test_future_tooling_needs_parses_fastems2_tool_payload(monkeypatch) -> None:
    monkeypatch.setattr("app.domain.tooling.future_needs_service.tooling_future_needs_cache", _NoCache())
    production_rows = [
        {
            "noProdOrder": "M200001",
            "prodOrderNo": "M200001-1",
            "lineNo": 10000,
            "status": "Released",
            "routingNo": "8317032-01",
            "itemNo": "8317032",
            "description": "Part Fastems2",
            "opCode": "000500-1OP",
            "inputQuantity": 2,
            "qtyfait": 0,
            "dueDate": "2026-03-12",
        }
    ]
    nc_payload = {
        "8317032-1OP": [
            {"ToolCode": "5502", "Usage": 13, "Description": "FORET"},
        ]
    }
    service = FutureToolingNeedService(
        production_client=_StubProductionClient(production_rows),
        nc_program_client=_StubNCProgramClient(nc_payload),
    )

    result = await service.get_future_needs(work_center_no="40279", refresh=True, tool_source="fastems2")

    tool_row = next(row for row in result.rows if row.tool_id == "5502")
    assert tool_row.tool_use_time_seconds == 13
    assert tool_row.total_required_use_time_seconds == 26
    assert tool_row.tool_description == "FORET"

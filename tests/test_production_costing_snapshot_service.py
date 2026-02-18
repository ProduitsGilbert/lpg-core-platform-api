import datetime as dt
from uuid import UUID

import pytest

from app.domain.erp.production_costing_snapshot_service import ProductionCostingSnapshotService


class _StubERPClient:
    def __init__(self) -> None:
        self.routing_lines_calls: list[str | None] = []
        self.bom_lines_calls: list[str | None] = []
        self.routing_headers_filters: list[dt.datetime | None] = []
        self.bom_headers_filters: list[dt.datetime | None] = []

    async def get_routing_headers(self, *, last_modified_after=None):
        self.routing_headers_filters.append(last_modified_after)
        return [{"No": "7403032-12", "Last_Date_Modified": "2026-02-17"}]

    async def get_production_bom_headers(self, *, last_modified_after=None):
        self.bom_headers_filters.append(last_modified_after)
        return [{"No": "7403032-12", "Last_Date_Modified": "2026-02-17"}]

    async def get_routing_lines(self, routing_no=None):
        self.routing_lines_calls.append(routing_no)
        return [{"Routing_No": routing_no or "7403032-12", "Operation_No": "10"}]

    async def get_production_bom_lines(self, production_bom_no=None):
        self.bom_lines_calls.append(production_bom_no)
        return [{"Production_BOM_No": production_bom_no or "7403032-12", "Line_No": "10000"}]


class _StubRepository:
    is_configured = True

    def __init__(self, *, routing_since: dt.datetime | None, bom_since: dt.datetime | None) -> None:
        self._routing_since = routing_since
        self._bom_since = bom_since
        self._scan_id = UUID("10000000-0000-0000-0000-000000000001")
        self._row: dict | None = None
        self.inserted = 0
        self.created_mode: str | None = None
        self.create_scan_calls = 0
        self.upsert_calls: list[tuple[str, dt.datetime | None]] = []

    def ensure_schema(self) -> None:
        return None

    def get_source_last_modified(self, source_type: str):
        if source_type == "routing":
            return self._routing_since
        return self._bom_since

    def create_scan(self, *, scan_mode: str, trigger_source: str, since_modified_at):
        self.create_scan_calls += 1
        self.created_mode = scan_mode
        self._row = {
            "scan_id": str(self._scan_id),
            "scan_started_at": dt.datetime(2026, 2, 18, 12, 0, 0),
            "scan_finished_at": None,
            "scan_mode": scan_mode,
            "trigger_source": trigger_source,
            "status": "running",
            "since_modified_at": since_modified_at,
            "until_modified_at": None,
            "routing_headers_count": 0,
            "bom_headers_count": 0,
            "routing_lines_count": 0,
            "bom_lines_count": 0,
            "error_message": None,
        }
        return self._scan_id

    def insert_line_snapshots(self, rows):
        self.inserted += len(rows)
        return len(rows)

    def upsert_source_state(self, *, source_type: str, last_successful_modified_at, last_scan_id):
        _ = last_scan_id
        self.upsert_calls.append((source_type, last_successful_modified_at))

    def complete_scan(
        self,
        *,
        scan_id,
        status,
        until_modified_at,
        routing_headers_count,
        bom_headers_count,
        routing_lines_count,
        bom_lines_count,
        error_message=None,
    ):
        assert self._row is not None
        assert str(scan_id) == str(self._scan_id)
        self._row.update(
            {
                "scan_finished_at": dt.datetime(2026, 2, 18, 12, 1, 0),
                "status": status,
                "until_modified_at": until_modified_at,
                "routing_headers_count": routing_headers_count,
                "bom_headers_count": bom_headers_count,
                "routing_lines_count": routing_lines_count,
                "bom_lines_count": bom_lines_count,
                "error_message": error_message,
            }
        )

    def get_scan(self, scan_id):
        assert str(scan_id) == str(self._scan_id)
        return self._row


@pytest.mark.asyncio
async def test_delta_scan_bootstraps_full_tables_when_no_watermark():
    client = _StubERPClient()
    repo = _StubRepository(routing_since=None, bom_since=None)
    service = ProductionCostingSnapshotService(erp_client=client, repository=repo)

    result = await service.run_scan(full_refresh=False, trigger_source="scheduler")

    assert result.scan_mode == "delta"
    assert result.snapshot_created is True
    assert client.routing_headers_filters == [None]
    assert client.bom_headers_filters == [None]
    assert client.routing_lines_calls == [None]
    assert client.bom_lines_calls == [None]
    assert result.routing_lines_count == 1
    assert result.bom_lines_count == 1
    assert repo.inserted == 2
    assert repo.create_scan_calls == 1
    assert sorted(source for source, _ in repo.upsert_calls) == ["bom", "routing"]
    assert all(value is not None for _, value in repo.upsert_calls)


@pytest.mark.asyncio
async def test_delta_scan_can_mix_routing_delta_with_bom_bootstrap():
    routing_since = dt.datetime(2026, 2, 16, 0, 0, 0)
    client = _StubERPClient()
    repo = _StubRepository(routing_since=routing_since, bom_since=None)
    service = ProductionCostingSnapshotService(erp_client=client, repository=repo)

    await service.run_scan(full_refresh=False, trigger_source="scheduler")

    assert client.routing_headers_filters == [routing_since]
    assert client.bom_headers_filters == [None]
    assert client.routing_lines_calls == ["7403032-12"]
    assert client.bom_lines_calls == [None]
    assert repo.create_scan_calls == 1


@pytest.mark.asyncio
async def test_scan_uses_fallback_watermark_when_headers_have_no_modified_date():
    class _NoModifiedERP(_StubERPClient):
        async def get_routing_headers(self, *, last_modified_after=None):
            self.routing_headers_filters.append(last_modified_after)
            return [{"No": "7403032-12"}]

        async def get_production_bom_headers(self, *, last_modified_after=None):
            self.bom_headers_filters.append(last_modified_after)
            return [{"No": "7403032-12"}]

    client = _NoModifiedERP()
    repo = _StubRepository(routing_since=None, bom_since=None)
    service = ProductionCostingSnapshotService(erp_client=client, repository=repo)

    await service.run_scan(full_refresh=False, trigger_source="scheduler")

    assert sorted(source for source, _ in repo.upsert_calls) == ["bom", "routing"]
    assert all(value is not None for _, value in repo.upsert_calls)


@pytest.mark.asyncio
async def test_delta_scan_skips_snapshot_when_no_headers_changed():
    class _NoChangeERP(_StubERPClient):
        async def get_routing_headers(self, *, last_modified_after=None):
            self.routing_headers_filters.append(last_modified_after)
            return []

        async def get_production_bom_headers(self, *, last_modified_after=None):
            self.bom_headers_filters.append(last_modified_after)
            return []

    since = dt.datetime(2026, 2, 17, 0, 0, 0)
    client = _NoChangeERP()
    repo = _StubRepository(routing_since=since, bom_since=since)
    service = ProductionCostingSnapshotService(erp_client=client, repository=repo)

    result = await service.run_scan(full_refresh=False, trigger_source="scheduler")

    assert result.status == "skipped_no_changes"
    assert result.snapshot_created is False
    assert result.total_lines_count == 0
    assert repo.create_scan_calls == 0
    assert repo.inserted == 0
    assert repo.upsert_calls == []


@pytest.mark.asyncio
async def test_delta_scan_skips_when_header_date_equals_watermark():
    class _EqualDateERP(_StubERPClient):
        async def get_routing_headers(self, *, last_modified_after=None):
            self.routing_headers_filters.append(last_modified_after)
            return [{"No": "7403032-12", "Last_Date_Modified": "2026-02-18"}]

        async def get_production_bom_headers(self, *, last_modified_after=None):
            self.bom_headers_filters.append(last_modified_after)
            return [{"No": "7403032-12", "Last_Date_Modified": "2026-02-18"}]

    since = dt.datetime(2026, 2, 18, 0, 0, 0)
    client = _EqualDateERP()
    repo = _StubRepository(routing_since=since, bom_since=since)
    service = ProductionCostingSnapshotService(erp_client=client, repository=repo)

    result = await service.run_scan(full_refresh=False, trigger_source="scheduler")

    assert result.status == "skipped_no_changes"
    assert result.snapshot_created is False
    assert repo.create_scan_calls == 0

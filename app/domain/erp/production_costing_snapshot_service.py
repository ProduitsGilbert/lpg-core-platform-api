"""Service for snapshotting ERP Routing/BOM lines for costing analysis."""

from __future__ import annotations

import asyncio
import datetime as dt
import json
import logging
from typing import Any, Dict, Iterable, Optional
from uuid import UUID

from app.adapters.erp_client import ERPClient
from app.domain.erp.models import (
    ProductionCostingGroupedItemResponse,
    ProductionCostingScanResponse,
    ProductionCostingSourceSnapshot,
)
from app.errors import DatabaseError
from app.integrations.cedule_production_costing_repository import CeduleProductionCostingRepository
from app.settings import settings

logger = logging.getLogger(__name__)


class ProductionCostingSnapshotService:
    """Synchronize and query production costing snapshots in Cedule."""

    def __init__(
        self,
        *,
        erp_client: Optional[ERPClient] = None,
        repository: Optional[CeduleProductionCostingRepository] = None,
    ) -> None:
        self._client = erp_client or ERPClient()
        self._repository = repository or CeduleProductionCostingRepository()
        self._insert_batch_size = max(50, int(getattr(settings, "production_costing_insert_batch_size", 500)))
        self._max_concurrency = max(1, int(getattr(settings, "production_costing_sync_max_concurrency", 6)))

    @property
    def is_configured(self) -> bool:
        return self._repository.is_configured

    async def run_scan(
        self,
        *,
        full_refresh: bool,
        trigger_source: str,
    ) -> ProductionCostingScanResponse:
        if not self._repository.is_configured:
            raise DatabaseError("Cedule database not configured")

        await asyncio.to_thread(self._repository.ensure_schema)

        scan_mode = "full" if full_refresh else "delta"
        since_routing: Optional[dt.datetime] = None
        since_bom: Optional[dt.datetime] = None
        routing_bootstrap = full_refresh
        bom_bootstrap = full_refresh

        if not full_refresh:
            since_routing = await asyncio.to_thread(self._repository.get_source_last_modified, "routing")
            since_bom = await asyncio.to_thread(self._repository.get_source_last_modified, "bom")
            routing_bootstrap = since_routing is None
            bom_bootstrap = since_bom is None

        since_modified_at = _min_datetime([since_routing, since_bom])

        routing_headers = await self._client.get_routing_headers(
            last_modified_after=None if routing_bootstrap else since_routing
        )
        bom_headers = await self._client.get_production_bom_headers(
            last_modified_after=None if bom_bootstrap else since_bom
        )

        routing_modified_by_no = self._map_header_modified_by_no(routing_headers, source_type="routing")
        bom_modified_by_no = self._map_header_modified_by_no(bom_headers, source_type="bom")

        if not routing_bootstrap and since_routing is not None:
            routing_modified_by_no = _filter_modified_after(routing_modified_by_no, since_routing)
        if not bom_bootstrap and since_bom is not None:
            bom_modified_by_no = _filter_modified_after(bom_modified_by_no, since_bom)

        routing_headers_count = len(routing_modified_by_no)
        bom_headers_count = len(bom_modified_by_no)

        latest_routing_modified = _max_datetime(routing_modified_by_no.values())
        latest_bom_modified = _max_datetime(bom_modified_by_no.values())
        watermark_fallback = dt.datetime.now(dt.UTC).replace(tzinfo=None, microsecond=0)
        if latest_routing_modified is None and routing_headers_count > 0:
            latest_routing_modified = watermark_fallback
        if latest_bom_modified is None and bom_headers_count > 0:
            latest_bom_modified = watermark_fallback

        has_routing_changes = routing_bootstrap or routing_headers_count > 0
        has_bom_changes = bom_bootstrap or bom_headers_count > 0

        if not full_refresh and not has_routing_changes and not has_bom_changes:
            return _build_skipped_scan_response(
                scan_mode=scan_mode,
                trigger_source=trigger_source,
                since_modified_at=since_modified_at,
                until_modified_at=_max_datetime([since_routing, since_bom]),
            )

        scan_id = await asyncio.to_thread(
            self._repository.create_scan,
            scan_mode=scan_mode,
            trigger_source=trigger_source,
            since_modified_at=since_modified_at,
        )

        routing_lines_count = 0
        bom_lines_count = 0
        until_modified_at: Optional[dt.datetime] = None

        try:
            if routing_bootstrap:
                routing_lines = await self._client.get_routing_lines()
                routing_lines_count = await self._persist_lines(
                    scan_id=scan_id,
                    source_type="routing",
                    lines=routing_lines,
                    header_modified_by_no=routing_modified_by_no,
                )
            else:
                routing_lines_count = await self._persist_delta_lines(
                    scan_id=scan_id,
                    source_type="routing",
                    header_modified_by_no=routing_modified_by_no,
                )

            if bom_bootstrap:
                bom_lines = await self._client.get_production_bom_lines()
                bom_lines_count = await self._persist_lines(
                    scan_id=scan_id,
                    source_type="bom",
                    lines=bom_lines,
                    header_modified_by_no=bom_modified_by_no,
                )
            else:
                bom_lines_count = await self._persist_delta_lines(
                    scan_id=scan_id,
                    source_type="bom",
                    header_modified_by_no=bom_modified_by_no,
                )

            if latest_routing_modified:
                await asyncio.to_thread(
                    self._repository.upsert_source_state,
                    source_type="routing",
                    last_successful_modified_at=latest_routing_modified,
                    last_scan_id=scan_id,
                )
            if latest_bom_modified:
                await asyncio.to_thread(
                    self._repository.upsert_source_state,
                    source_type="bom",
                    last_successful_modified_at=latest_bom_modified,
                    last_scan_id=scan_id,
                )

            until_modified_at = _max_datetime([latest_routing_modified, latest_bom_modified])

            await asyncio.to_thread(
                self._repository.complete_scan,
                scan_id=scan_id,
                status="success",
                until_modified_at=until_modified_at,
                routing_headers_count=routing_headers_count,
                bom_headers_count=bom_headers_count,
                routing_lines_count=routing_lines_count,
                bom_lines_count=bom_lines_count,
                error_message=None,
            )
        except Exception as exc:
            await asyncio.to_thread(
                self._repository.complete_scan,
                scan_id=scan_id,
                status="failed",
                until_modified_at=until_modified_at,
                routing_headers_count=routing_headers_count,
                bom_headers_count=bom_headers_count,
                routing_lines_count=routing_lines_count,
                bom_lines_count=bom_lines_count,
                error_message=str(exc)[:2000],
            )
            raise

        row = await asyncio.to_thread(self._repository.get_scan, scan_id)
        if not row:
            raise DatabaseError("Costing scan completed but result could not be loaded")
        return _scan_row_to_response(row)

    async def get_grouped_item_snapshot(
        self,
        *,
        item_no: str,
        latest_only: bool,
        include_lines: bool,
    ) -> ProductionCostingGroupedItemResponse:
        if not self._repository.is_configured:
            raise DatabaseError("Cedule database not configured")

        await asyncio.to_thread(self._repository.ensure_schema)

        base_item_no = _base_item_no(item_no)
        rows = await asyncio.to_thread(
            self._repository.list_item_snapshot_rows,
            base_item_no=base_item_no,
            latest_only=latest_only,
            include_lines=include_lines,
        )

        grouped: dict[tuple[str, str, str], dict[str, Any]] = {}

        for row in rows:
            source_type = str(row.get("source_type") or "").strip().lower()
            source_no = str(row.get("source_no") or "").strip()
            scan_id = str(row.get("scan_id") or "").strip()
            if not source_type or not source_no or not scan_id:
                continue

            key = (source_type, source_no, scan_id)
            entry = grouped.get(key)
            if entry is None:
                entry = {
                    "source_type": source_type,
                    "source_no": source_no,
                    "base_item_no": _base_item_no(source_no),
                    "revision": _extract_revision(source_no),
                    "scan_id": scan_id,
                    "scan_started_at": _to_utc_naive(row.get("scan_started_at")),
                    "scan_finished_at": _to_utc_naive(row.get("scan_finished_at")),
                    "header_last_modified_at": _to_utc_naive(row.get("header_last_modified_at")),
                    "line_count": 0,
                    "lines": [],
                }
                grouped[key] = entry

            entry["line_count"] += 1
            if include_lines:
                payload = _safe_load_json(row.get("row_json"))
                if payload is not None:
                    entry["lines"].append(payload)

        snapshots = [ProductionCostingSourceSnapshot.model_validate(value) for value in grouped.values()]
        snapshots.sort(key=lambda s: (s.source_type, s.source_no, s.scan_started_at or dt.datetime.min))

        routing_versions = [snapshot for snapshot in snapshots if snapshot.source_type == "routing"]
        bom_versions = [snapshot for snapshot in snapshots if snapshot.source_type == "bom"]

        last_scan_at = _max_datetime(snapshot.scan_started_at for snapshot in snapshots)

        return ProductionCostingGroupedItemResponse(
            item_no=base_item_no,
            latest_only=latest_only,
            include_lines=include_lines,
            total_versions=len(snapshots),
            last_scan_at=last_scan_at,
            routing_versions=routing_versions,
            bom_versions=bom_versions,
        )

    def _map_header_modified_by_no(
        self,
        rows: Iterable[Dict[str, Any]],
        *,
        source_type: str,
    ) -> dict[str, Optional[dt.datetime]]:
        out: dict[str, Optional[dt.datetime]] = {}
        for row in rows:
            source_no = self._extract_source_no(row, source_type=source_type, from_header=True)
            if not source_no:
                continue
            out[source_no] = _extract_last_modified(row)
        return out

    async def _persist_delta_lines(
        self,
        *,
        scan_id: UUID,
        source_type: str,
        header_modified_by_no: dict[str, Optional[dt.datetime]],
    ) -> int:
        if not header_modified_by_no:
            return 0

        semaphore = asyncio.Semaphore(self._max_concurrency)
        tasks = [
            asyncio.create_task(self._fetch_lines_for_source(source_type, source_no, modified_at, semaphore))
            for source_no, modified_at in header_modified_by_no.items()
        ]

        persisted = 0
        for task in asyncio.as_completed(tasks):
            source_no, header_last_modified_at, lines = await task
            persisted += await self._persist_source_lines(
                scan_id=scan_id,
                source_type=source_type,
                source_no=source_no,
                header_last_modified_at=header_last_modified_at,
                lines=lines,
            )
        return persisted

    async def _fetch_lines_for_source(
        self,
        source_type: str,
        source_no: str,
        header_last_modified_at: Optional[dt.datetime],
        semaphore: asyncio.Semaphore,
    ) -> tuple[str, Optional[dt.datetime], list[dict[str, Any]]]:
        async with semaphore:
            if source_type == "routing":
                lines = await self._client.get_routing_lines(source_no)
            else:
                lines = await self._client.get_production_bom_lines(source_no)
        return source_no, header_last_modified_at, lines

    async def _persist_lines(
        self,
        *,
        scan_id: UUID,
        source_type: str,
        lines: list[dict[str, Any]],
        header_modified_by_no: dict[str, Optional[dt.datetime]],
    ) -> int:
        persisted = 0
        batch: list[dict[str, Any]] = []

        for line in lines:
            source_no = self._extract_source_no(line, source_type=source_type, from_header=False)
            if not source_no:
                continue

            row = {
                "scan_id": str(scan_id),
                "source_type": source_type,
                "source_no": source_no,
                "source_base_item_no": _base_item_no(source_no),
                "header_last_modified_at": header_modified_by_no.get(source_no) or _extract_last_modified(line),
                "line_key": _line_key(line, source_type=source_type),
                "row_json": json.dumps(line, ensure_ascii=True, default=str, separators=(",", ":")),
            }
            batch.append(row)

            if len(batch) >= self._insert_batch_size:
                persisted += await asyncio.to_thread(self._repository.insert_line_snapshots, batch)
                batch = []

        if batch:
            persisted += await asyncio.to_thread(self._repository.insert_line_snapshots, batch)

        return persisted

    async def _persist_source_lines(
        self,
        *,
        scan_id: UUID,
        source_type: str,
        source_no: str,
        header_last_modified_at: Optional[dt.datetime],
        lines: list[dict[str, Any]],
    ) -> int:
        if not lines:
            return 0

        batch = [
            {
                "scan_id": str(scan_id),
                "source_type": source_type,
                "source_no": source_no,
                "source_base_item_no": _base_item_no(source_no),
                "header_last_modified_at": header_last_modified_at or _extract_last_modified(line),
                "line_key": _line_key(line, source_type=source_type),
                "row_json": json.dumps(line, ensure_ascii=True, default=str, separators=(",", ":")),
            }
            for line in lines
        ]
        return await asyncio.to_thread(self._repository.insert_line_snapshots, batch)

    @staticmethod
    def _extract_source_no(row: Dict[str, Any], *, source_type: str, from_header: bool) -> str:
        if source_type == "routing":
            fields = ("No", "Routing_No", "RoutingNo") if from_header else ("Routing_No", "RoutingNo", "No")
        else:
            fields = (
                ("No", "Production_BOM_No", "ProductionBOMNo")
                if from_header
                else ("Production_BOM_No", "ProductionBOMNo", "No")
            )

        for field in fields:
            value = row.get(field)
            if value in (None, ""):
                continue
            normalized = str(value).strip()
            if normalized:
                return normalized
        return ""


def _scan_row_to_response(row: Dict[str, Any]) -> ProductionCostingScanResponse:
    routing_lines = int(row.get("routing_lines_count") or 0)
    bom_lines = int(row.get("bom_lines_count") or 0)
    return ProductionCostingScanResponse(
        scan_id=str(row.get("scan_id")),
        scan_mode=str(row.get("scan_mode") or ""),
        trigger_source=str(row.get("trigger_source") or ""),
        status=str(row.get("status") or ""),
        scan_started_at=_to_utc_naive(row.get("scan_started_at")),
        scan_finished_at=_to_utc_naive(row.get("scan_finished_at")),
        since_modified_at=_to_utc_naive(row.get("since_modified_at")),
        until_modified_at=_to_utc_naive(row.get("until_modified_at")),
        routing_headers_count=int(row.get("routing_headers_count") or 0),
        bom_headers_count=int(row.get("bom_headers_count") or 0),
        routing_lines_count=routing_lines,
        bom_lines_count=bom_lines,
        total_lines_count=routing_lines + bom_lines,
        snapshot_created=True,
        error_message=(str(row.get("error_message")) if row.get("error_message") else None),
    )


def _build_skipped_scan_response(
    *,
    scan_mode: str,
    trigger_source: str,
    since_modified_at: Optional[dt.datetime],
    until_modified_at: Optional[dt.datetime],
) -> ProductionCostingScanResponse:
    now = dt.datetime.now(dt.UTC).replace(tzinfo=None, microsecond=0)
    return ProductionCostingScanResponse(
        scan_id="",
        scan_mode=scan_mode,
        trigger_source=trigger_source,
        status="skipped_no_changes",
        scan_started_at=now,
        scan_finished_at=now,
        since_modified_at=since_modified_at,
        until_modified_at=until_modified_at,
        routing_headers_count=0,
        bom_headers_count=0,
        routing_lines_count=0,
        bom_lines_count=0,
        total_lines_count=0,
        snapshot_created=False,
        error_message=None,
    )


def _safe_load_json(value: Any) -> Optional[dict[str, Any]]:
    if value in (None, ""):
        return None
    if isinstance(value, dict):
        return value
    try:
        loaded = json.loads(str(value))
    except (TypeError, ValueError):
        return None
    if isinstance(loaded, dict):
        return loaded
    return {"value": loaded}


def _line_key(row: Dict[str, Any], *, source_type: str) -> Optional[str]:
    if source_type == "routing":
        fields = ("Operation_No", "OperationNo", "Sequence", "Type", "No")
    else:
        fields = ("Line_No", "LineNo", "Position", "Type", "No")

    values = [str(row.get(field)).strip() for field in fields if row.get(field) not in (None, "")]
    if not values:
        return None
    return "|".join(values)[:200]


def _extract_revision(source_no: str) -> Optional[str]:
    normalized = (source_no or "").strip()
    if "-" not in normalized:
        return None
    revision = normalized.split("-", 1)[1].strip()
    return revision or None


def _base_item_no(value: str) -> str:
    normalized = (value or "").strip()
    if "-" in normalized:
        return normalized.split("-", 1)[0].strip()
    return normalized


def _extract_last_modified(row: Dict[str, Any]) -> Optional[dt.datetime]:
    candidates = (
        "Last_Modified_Date",
        "Last_Date_Modified",
        "LastModifiedDate",
        "Last_Modified_Date_Time",
        "Last Modified Date",
        "SystemModifiedAt",
        "Modified_At",
    )
    for field in candidates:
        value = row.get(field)
        parsed = _to_utc_naive(value)
        if parsed is not None:
            return parsed
    return None


def _to_utc_naive(value: Any) -> Optional[dt.datetime]:
    if value is None:
        return None
    parsed: Optional[dt.datetime] = None

    if isinstance(value, dt.datetime):
        parsed = value
    elif isinstance(value, dt.date):
        parsed = dt.datetime.combine(value, dt.time.min)
    elif isinstance(value, str):
        cleaned = value.strip()
        if not cleaned:
            return None
        normalized = cleaned.replace("Z", "+00:00")
        try:
            parsed = dt.datetime.fromisoformat(normalized)
        except ValueError:
            parsed = None

    if parsed is None:
        return None

    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(dt.UTC).replace(tzinfo=None)
    return parsed


def _max_datetime(values: Iterable[Optional[dt.datetime]]) -> Optional[dt.datetime]:
    normalized = [value for value in values if value is not None]
    if not normalized:
        return None
    return max(normalized)


def _min_datetime(values: Iterable[Optional[dt.datetime]]) -> Optional[dt.datetime]:
    normalized = [value for value in values if value is not None]
    if not normalized:
        return None
    return min(normalized)


def _filter_modified_after(
    values: dict[str, Optional[dt.datetime]],
    cutoff: dt.datetime,
) -> dict[str, Optional[dt.datetime]]:
    filtered: dict[str, Optional[dt.datetime]] = {}
    for source_no, modified_at in values.items():
        if modified_at is None:
            continue
        if modified_at > cutoff:
            filtered[source_no] = modified_at
    return filtered

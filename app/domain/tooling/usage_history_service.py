from __future__ import annotations

import asyncio
import calendar
import datetime as dt
from collections import defaultdict
from typing import Any

from app.adapters.erp_client import ERPClient
from app.adapters.fastems1.nc_program_client import FastemsNCProgramClient
from app.domain.tooling.models import (
    ToolingUsageHistoryMonthSummary,
    ToolingUsageHistoryResponse,
    ToolingUsageHistoryRow,
    ToolingUsageHistoryToolSummary,
)
from app.domain.tooling.nc_program_source import (
    get_tool_description,
    get_tool_id,
    get_tool_use_time_value,
    nc_program_base_url_for_source,
    resolve_tool_source,
)
from app.domain.tooling.usage_history_cache import tooling_usage_history_cache
from app.errors import ValidationException
from app.settings import settings


def _safe_float(value: Any) -> float:
    try:
        if value is None:
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _iso_date(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if "T" in text:
        text = text.split("T", 1)[0]
    return text


def _month_start(day: dt.date) -> dt.date:
    return day.replace(day=1)


def _next_month(day: dt.date) -> dt.date:
    if day.month == 12:
        return dt.date(day.year + 1, 1, 1)
    return dt.date(day.year, day.month + 1, 1)


def _month_windows(start_date: dt.date, end_date: dt.date) -> list[tuple[dt.date, dt.date]]:
    windows: list[tuple[dt.date, dt.date]] = []
    cursor = _month_start(start_date)
    while cursor <= end_date:
        month_end = _next_month(cursor) - dt.timedelta(days=1)
        window_start = max(cursor, start_date)
        window_end = min(month_end, end_date)
        windows.append((window_start, window_end))
        cursor = _next_month(cursor)
    return windows


def _subtract_months(day: dt.date, months: int) -> dt.date:
    total_month = (day.year * 12 + (day.month - 1)) - months
    year = total_month // 12
    month = (total_month % 12) + 1
    month_last_day = calendar.monthrange(year, month)[1]
    target_day = min(day.day, month_last_day)
    return dt.date(year, month, target_day)


def _extract_item_prefix(item_no: Any) -> str | None:
    raw = str(item_no or "").strip()
    if not raw:
        return None
    digits = "".join(ch for ch in raw if ch.isdigit())
    if len(digits) >= 7:
        return digits[:7]
    return raw.split("-", 1)[0].strip() or None


def _extract_operation_suffix(operation_no: Any) -> str | None:
    text = str(operation_no or "").strip().upper().replace("_", "-")
    if not text:
        return None
    tokens = [token.strip() for token in text.split("-") if token.strip()]
    for token in reversed(tokens):
        if token.endswith("OP"):
            digits = "".join(ch for ch in token if ch.isdigit())
            if digits:
                return f"{int(digits)}OP"
            return token
    for token in reversed(tokens):
        digits = "".join(ch for ch in token if ch.isdigit())
        if digits:
            return f"{int(digits)}OP"
    return None


def _build_program(item_no: Any, operation_no: Any) -> str | None:
    item_prefix = _extract_item_prefix(item_no)
    suffix = _extract_operation_suffix(operation_no)
    if not item_prefix or not suffix:
        return None
    return f"{item_prefix}-{suffix}"


def _month_label(value: Any) -> str | None:
    iso = _iso_date(value)
    if not iso:
        return None
    return iso[:7]


class ToolingUsageHistoryService:
    """Builds tooling usage history from BC CapacityLedgerEntries + NC program tools."""

    def __init__(
        self,
        erp_client: ERPClient | None = None,
        nc_program_client: FastemsNCProgramClient | None = None,
    ) -> None:
        self._erp_client = erp_client or ERPClient()
        self._nc_program_client = nc_program_client
        self._nc_program_clients_by_source: dict[str, FastemsNCProgramClient] = {}

    async def get_usage_history(
        self,
        *,
        work_center_no: str = "40253",
        machine_center: str = "DMC100",
        months: int = 12,
        refresh: bool = False,
        tool_source: str | None = None,
    ) -> ToolingUsageHistoryResponse:
        work_center_no = str(work_center_no).strip() or "40253"
        machine_center = str(machine_center).strip() or "DMC100"
        if months < 1 or months > 24:
            raise ValidationException("months must be between 1 and 24", field="months")
        resolved_tool_source = resolve_tool_source(work_center_no, tool_source)

        end_date = dt.date.today()
        start_date = _subtract_months(end_date, months)

        cache_key = (
            f"{resolved_tool_source}|{work_center_no}|{machine_center}|"
            f"{start_date.isoformat()}|{end_date.isoformat()}"
        )
        tooling_usage_history_cache.register_pair(work_center_no, machine_center)
        if not refresh and tooling_usage_history_cache.is_configured:
            cached_payload = tooling_usage_history_cache.get_snapshot(cache_key)
            if cached_payload:
                response = ToolingUsageHistoryResponse.model_validate(cached_payload)
                response.from_cache = True
                return response

        response = await self._build_usage_history(
            work_center_no=work_center_no,
            machine_center=machine_center,
            start_date=start_date,
            end_date=end_date,
            tool_source=resolved_tool_source,
        )
        if tooling_usage_history_cache.is_configured:
            retention_cutoff = dt.datetime.now(dt.UTC) - dt.timedelta(
                days=settings.tooling_usage_history_cache_retention_days
            )
            tooling_usage_history_cache.upsert_snapshot(
                cache_key=cache_key,
                work_center_no=work_center_no,
                machine_center=machine_center,
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
                payload=response.model_dump(),
            )
            tooling_usage_history_cache.prune_before(retention_cutoff.isoformat())
        return response

    async def _build_usage_history(
        self,
        *,
        work_center_no: str,
        machine_center: str,
        start_date: dt.date,
        end_date: dt.date,
        tool_source: str,
    ) -> ToolingUsageHistoryResponse:
        source_rows = await self._load_capacity_rows_by_month(
            work_center_no=work_center_no,
            start_date=start_date,
            end_date=end_date,
        )
        source_entry_count = len(source_rows)

        program_names: set[str] = set()
        for row in source_rows:
            program = _build_program(row.get("Item_No") or row.get("ItemNo"), row.get("Operation_No") or row.get("OperationNo"))
            if program:
                program_names.add(program)

        program_tools = await self._load_program_tools(program_names, tool_source=tool_source)

        detailed_rows: list[ToolingUsageHistoryRow] = []
        tool_totals: dict[str, int] = defaultdict(int)
        tool_rows: dict[str, int] = defaultdict(int)
        tool_programs: dict[str, set[str]] = defaultdict(set)
        tool_months: dict[str, set[str]] = defaultdict(set)

        month_source_entries: dict[str, int] = defaultdict(int)
        month_rows: dict[str, int] = defaultdict(int)
        month_source_quantity: dict[str, float] = defaultdict(float)
        month_time_total: dict[str, int] = defaultdict(int)

        for row in source_rows:
            posting_date = _iso_date(row.get("Posting_Date") or row.get("PostingDate"))
            month = _month_label(posting_date)
            if month:
                month_source_entries[month] += 1
            quantity = _safe_float(row.get("Quantity"))
            if quantity <= 0:
                continue
            if month:
                month_source_quantity[month] += quantity
            item_no = row.get("Item_No") or row.get("ItemNo")
            operation_no = row.get("Operation_No") or row.get("OperationNo")
            operation_suffix = _extract_operation_suffix(operation_no)
            nc_program = _build_program(item_no, operation_no)
            tools = program_tools.get(nc_program or "", [])

            if not tools:
                detailed_rows.append(
                    ToolingUsageHistoryRow(
                        posting_date=posting_date,
                        work_center_no=work_center_no,
                        machine_center=machine_center,
                        order_no=str(row.get("Order_No") or row.get("OrderNo") or "") or None,
                        item_no=str(item_no or "") or None,
                        operation_no=str(operation_no or "") or None,
                        operation_suffix=operation_suffix,
                        nc_program=nc_program,
                        quantity=quantity,
                    )
                )
                if month:
                    month_rows[month] += 1
                continue

            for tool in tools:
                tool_id = get_tool_id(tool)
                use_time = _safe_int(get_tool_use_time_value(tool), default=0) or None
                total_use_time = int(round(use_time * quantity)) if use_time is not None else None
                detailed_rows.append(
                    ToolingUsageHistoryRow(
                        posting_date=posting_date,
                        work_center_no=work_center_no,
                        machine_center=machine_center,
                        order_no=str(row.get("Order_No") or row.get("OrderNo") or "") or None,
                        item_no=str(item_no or "") or None,
                        operation_no=str(operation_no or "") or None,
                        operation_suffix=operation_suffix,
                        nc_program=nc_program,
                        quantity=quantity,
                        tool_id=tool_id,
                        tool_use_time_seconds=use_time,
                        tool_description=get_tool_description(tool),
                        estimated_total_use_time_seconds=total_use_time,
                    )
                )
                if month:
                    month_rows[month] += 1
                    if total_use_time:
                        month_time_total[month] += total_use_time
                if tool_id:
                    tool_rows[tool_id] += 1
                    if total_use_time:
                        tool_totals[tool_id] += total_use_time
                    if nc_program:
                        tool_programs[tool_id].add(nc_program)
                    if month:
                        tool_months[tool_id].add(month)

        tools_summary = [
            ToolingUsageHistoryToolSummary(
                tool_id=tool_id,
                total_estimated_use_time_seconds=tool_totals[tool_id],
                rows_count=tool_rows[tool_id],
                unique_program_count=len(tool_programs[tool_id]),
                months_active=len(tool_months[tool_id]),
            )
            for tool_id in sorted(tool_rows.keys())
        ]

        monthly_summary = [
            ToolingUsageHistoryMonthSummary(
                month=month,
                source_entries_count=month_source_entries.get(month, 0),
                rows_count=month_rows.get(month, 0),
                quantity_total=round(month_source_quantity.get(month, 0.0), 4),
                estimated_use_time_seconds_total=month_time_total.get(month, 0),
            )
            for month in sorted(month_source_entries.keys())
        ]

        return ToolingUsageHistoryResponse(
            work_center_no=work_center_no,
            machine_center=machine_center,
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            generated_at=dt.datetime.now(dt.UTC).isoformat(),
            from_cache=False,
            source_entry_count=source_entry_count,
            unique_program_count=len(program_names),
            rows_count=len(detailed_rows),
            tools_summary=tools_summary,
            monthly_summary=monthly_summary,
            rows=detailed_rows,
        )

    async def _load_capacity_rows_by_month(
        self,
        *,
        work_center_no: str,
        start_date: dt.date,
        end_date: dt.date,
    ) -> list[dict[str, Any]]:
        windows = _month_windows(start_date, end_date)
        rows: list[dict[str, Any]] = []
        for window_start, window_end in windows:
            rows.extend(
                await self._fetch_capacity_rows_window(
                    work_center_no=work_center_no,
                    start_date=window_start,
                    end_date=window_end,
                )
            )
        return rows

    async def _fetch_capacity_rows_window(
        self,
        *,
        work_center_no: str,
        start_date: dt.date,
        end_date: dt.date,
    ) -> list[dict[str, Any]]:
        clauses = [
            (
                f"Posting_Date ge {start_date.isoformat()} and Posting_Date le {end_date.isoformat()} "
                f"and Work_Center_No eq '{work_center_no}' and Order_Type eq 'Production' and Type eq 'Work Center'"
            ),
            (
                f"Posting_Date ge {start_date.isoformat()} and Posting_Date le {end_date.isoformat()} "
                f"and WorkCenterNo eq '{work_center_no}' and OrderType eq 'Production' and Type eq 'Work Center'"
            ),
            (
                f"Posting_Date ge {start_date.isoformat()} and Posting_Date le {end_date.isoformat()} "
                f"and WorkCenter_No eq '{work_center_no}' and Order_Type eq 'Production' and Type eq 'Work Center'"
            ),
        ]
        loaded = await self._erp_client._fetch_with_candidate_resources(
            resource_candidates=["CapacityLedgerEntries"],
            filter_clauses=clauses,
        )

        filtered: list[dict[str, Any]] = []
        for row in loaded:
            posting_date = _iso_date(row.get("Posting_Date") or row.get("PostingDate"))
            if not posting_date:
                continue
            if posting_date < start_date.isoformat() or posting_date > end_date.isoformat():
                continue
            wc = str(row.get("Work_Center_No") or row.get("WorkCenterNo") or row.get("WorkCenter_No") or "").strip()
            if wc != work_center_no:
                continue
            order_type = str(row.get("Order_Type") or row.get("OrderType") or "").strip().lower()
            entry_type = str(row.get("Type") or "").strip().lower()
            if order_type != "production":
                continue
            if entry_type not in {"work center", "workcenter"}:
                continue
            filtered.append(row)
        return filtered

    def _client_for_source(self, tool_source: str) -> FastemsNCProgramClient:
        if self._nc_program_client is not None:
            return self._nc_program_client
        client = self._nc_program_clients_by_source.get(tool_source)
        if client is not None:
            return client
        client = FastemsNCProgramClient(base_url=nc_program_base_url_for_source(tool_source))
        self._nc_program_clients_by_source[tool_source] = client
        return client

    async def _load_program_tools(
        self,
        program_names: set[str],
        *,
        tool_source: str,
    ) -> dict[str, list[dict[str, Any]]]:
        if not program_names:
            return {}
        semaphore = asyncio.Semaphore(12)
        client = self._client_for_source(tool_source)

        async def _fetch(program_name: str) -> tuple[str, list[dict[str, Any]]]:
            async with semaphore:
                rows = await client.get_program_tools(program_name)
                return program_name, rows

        payload = await asyncio.gather(*[_fetch(name) for name in sorted(program_names)])
        return dict(payload)

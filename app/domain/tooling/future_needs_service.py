from __future__ import annotations

import asyncio
import datetime as dt
from collections import defaultdict
from typing import Any

from app.adapters.fastems1.nc_program_client import FastemsNCProgramClient
from app.adapters.fastems1.production_client import FastemsProductionClient
from app.domain.tooling.future_needs_cache import tooling_future_needs_cache
from app.domain.tooling.models import (
    FutureToolingNeedResponse,
    FutureToolingNeedRow,
    FutureToolingToolSummary,
)
from app.domain.tooling.nc_program_source import (
    get_tool_description,
    get_tool_id,
    get_tool_use_time_value,
    nc_program_base_url_for_source,
    resolve_tool_source,
)
from app.settings import settings


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


def _extract_routing_item_no(routing_no: Any, item_no: Any) -> str | None:
    routing_text = (str(routing_no or "")).strip()
    routing_digits = "".join(ch for ch in routing_text if ch.isdigit())
    if len(routing_digits) >= 7:
        return routing_digits[:7]

    item_text = (str(item_no or "")).strip()
    item_digits = "".join(ch for ch in item_text if ch.isdigit())
    if len(item_digits) >= 7:
        return item_digits[:7]

    if routing_text:
        return routing_text.split("-", 1)[0].strip() or None
    if item_text:
        return item_text.split("-", 1)[0].strip() or None
    return None


def _extract_operation_suffix(op_code: Any, line_no: Any) -> str | None:
    op_text = (str(op_code or "")).strip().upper().replace("_", "-")
    if op_text:
        tokens = [token.strip() for token in op_text.split("-") if token.strip()]
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

    line_no_int = _safe_int(line_no, default=0)
    if line_no_int > 0:
        return f"{line_no_int}OP"
    return None


def _build_nc_program(routing_no: Any, item_no: Any, op_code: Any, line_no: Any) -> str | None:
    routing_item_no = _extract_routing_item_no(routing_no, item_no)
    suffix = _extract_operation_suffix(op_code, line_no)
    if not routing_item_no or not suffix:
        return None
    return f"{routing_item_no}-{suffix}"


class FutureToolingNeedService:
    """Aggregates coming production orders and tooling use by NC program."""

    def __init__(
        self,
        production_client: FastemsProductionClient | None = None,
        nc_program_client: FastemsNCProgramClient | None = None,
    ) -> None:
        self._production_client = production_client or FastemsProductionClient()
        self._nc_program_client = nc_program_client
        self._nc_program_clients_by_source: dict[str, FastemsNCProgramClient] = {}

    async def get_future_needs(
        self,
        work_center_no: str = "40253",
        refresh: bool = False,
        tool_source: str | None = None,
    ) -> FutureToolingNeedResponse:
        work_center_no = str(work_center_no).strip()
        if not work_center_no:
            work_center_no = "40253"
        resolved_tool_source = resolve_tool_source(work_center_no, tool_source)

        snapshot_date = dt.date.today().isoformat()
        tooling_future_needs_cache.register_work_center(work_center_no)

        if not refresh and tooling_future_needs_cache.is_configured:
            cached_payload = tooling_future_needs_cache.get_snapshot(work_center_no, snapshot_date)
            if cached_payload:
                response = FutureToolingNeedResponse.model_validate(cached_payload)
                response.from_cache = True
                return response

        response = await self._build_snapshot(
            work_center_no=work_center_no,
            snapshot_date=snapshot_date,
            tool_source=resolved_tool_source,
        )

        if tooling_future_needs_cache.is_configured:
            retention_cutoff = dt.date.today() - dt.timedelta(days=settings.tooling_future_needs_cache_retention_days)
            tooling_future_needs_cache.upsert_snapshot(work_center_no, snapshot_date, response.model_dump())
            tooling_future_needs_cache.prune_before(retention_cutoff.isoformat())
        return response

    async def _build_snapshot(
        self,
        *,
        work_center_no: str,
        snapshot_date: str,
        tool_source: str,
    ) -> FutureToolingNeedResponse:
        rows = await self._production_client.list_unfinished_routing_lines(work_center_no)
        order_count = len(rows)

        program_names: set[str] = set()
        for row in rows:
            program = _build_nc_program(
                routing_no=row.get("routingNo"),
                item_no=row.get("itemNo"),
                op_code=row.get("opCode"),
                line_no=row.get("lineNo"),
            )
            if program:
                program_names.add(program)

        program_tools = await self._load_program_tools(program_names, tool_source=tool_source)

        detailed_rows: list[FutureToolingNeedRow] = []
        tool_totals: dict[str, int] = defaultdict(int)
        tool_row_counts: dict[str, int] = defaultdict(int)
        tool_programs: dict[str, set[str]] = defaultdict(set)

        for row in rows:
            input_qty = _safe_int(row.get("inputQuantity"))
            completed_qty = _safe_int(row.get("qtyfait"))
            remaining_qty = max(input_qty - completed_qty, 0)
            routing_item_no = _extract_routing_item_no(row.get("routingNo"), row.get("itemNo"))
            operation_suffix = _extract_operation_suffix(row.get("opCode"), row.get("lineNo"))
            nc_program = (
                f"{routing_item_no}-{operation_suffix}"
                if routing_item_no and operation_suffix
                else None
            )

            tools = program_tools.get(nc_program or "", [])
            if not tools:
                detailed_rows.append(
                    FutureToolingNeedRow(
                        prod_order_no=row.get("prodOrderNo"),
                        no_prod_order=row.get("noProdOrder"),
                        line_no=_safe_int(row.get("lineNo"), default=0) or None,
                        status=row.get("status"),
                        due_date=_iso_date(row.get("dueDate")),
                        routing_no=row.get("routingNo"),
                        routing_item_no=routing_item_no,
                        op_code=row.get("opCode"),
                        operation_suffix=operation_suffix,
                        nc_program=nc_program,
                        part_no=row.get("itemNo"),
                        description=row.get("description"),
                        input_quantity=input_qty,
                        completed_quantity=completed_qty,
                        remaining_quantity=remaining_qty,
                    )
                )
                continue

            for tool in tools:
                tool_id = get_tool_id(tool)
                use_time = _safe_int(get_tool_use_time_value(tool), default=0) or None
                total_required_use_time = (
                    use_time * remaining_qty if use_time is not None else None
                )
                detailed_rows.append(
                    FutureToolingNeedRow(
                        prod_order_no=row.get("prodOrderNo"),
                        no_prod_order=row.get("noProdOrder"),
                        line_no=_safe_int(row.get("lineNo"), default=0) or None,
                        status=row.get("status"),
                        due_date=_iso_date(row.get("dueDate")),
                        routing_no=row.get("routingNo"),
                        routing_item_no=routing_item_no,
                        op_code=row.get("opCode"),
                        operation_suffix=operation_suffix,
                        nc_program=nc_program,
                        part_no=row.get("itemNo"),
                        description=row.get("description"),
                        input_quantity=input_qty,
                        completed_quantity=completed_qty,
                        remaining_quantity=remaining_qty,
                        tool_id=tool_id,
                        tool_use_time_seconds=use_time,
                        tool_description=get_tool_description(tool),
                        total_required_use_time_seconds=total_required_use_time,
                    )
                )
                if tool_id and total_required_use_time is not None:
                    tool_totals[tool_id] += total_required_use_time
                if tool_id:
                    tool_row_counts[tool_id] += 1
                    if nc_program:
                        tool_programs[tool_id].add(nc_program)

        tool_summary = [
            FutureToolingToolSummary(
                tool_id=tool_id,
                total_required_use_time_seconds=tool_totals[tool_id],
                rows_count=tool_row_counts[tool_id],
                program_count=len(tool_programs[tool_id]),
            )
            for tool_id in sorted(tool_row_counts.keys())
        ]

        return FutureToolingNeedResponse(
            work_center_no=work_center_no,
            snapshot_date=snapshot_date,
            generated_at=dt.datetime.now(dt.UTC).isoformat(),
            from_cache=False,
            source_order_count=order_count,
            unique_program_count=len(program_names),
            rows_count=len(detailed_rows),
            tools_summary=tool_summary,
            rows=detailed_rows,
        )

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

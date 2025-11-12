"""
Data providers for Fastems1 Autopilot.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Set
import asyncio
import logging

from app.adapters.fastems1.production_client import FastemsProductionClient
from app.adapters.fastems1.tooling_client import FastemsToolingClient
from app.adapters.fastems1.material_client import FastemsMaterialClient
from app.adapters.fastems1.pallet_route_client import FastemsPalletRouteClient
from app.adapters.fastems1.nc_program_client import FastemsNCProgramClient
from app.domain.usinage.fastems1.autopilot.models import (
    FixtureState,
    MachinePalletState,
    MaterialPalletState,
    ToolRequirement,
    ToolState,
    WorkOrderOperation,
)
from app.integrations.cedule_autopilot_repository import (
    CeduleAutopilotRepository,
    FixtureMatrixRow,
)

logger = logging.getLogger(__name__)


def _normalize_code(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _format_fixture_label(code: Optional[str], description: Optional[str]) -> Optional[str]:
    code_text = (code or "").strip()
    desc_text = (description or "").strip()
    if code_text and desc_text:
        return f"{code_text} - {desc_text}"
    return code_text or desc_text or None


def _normalize_location(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    squashed = " ".join(value.split())
    if "-" in squashed:
        parts = [part.strip() for part in squashed.split("-", 1)]
        return "-".join(parts)
    return squashed


class WorkOrderProvider:
    """Loads unfinished routing lines and converts them into domain operations."""

    def __init__(self, client: Optional[FastemsProductionClient] = None) -> None:
        self._client = client or FastemsProductionClient()

    async def list_active_operations(self) -> List[WorkOrderOperation]:
        raw_rows = await self._client.list_ready_routing_lines()
        operations: List[WorkOrderOperation] = []
        for row in raw_rows:
            work_order = row.get("prodOrderNo") or row.get("noProdOrder") or row.get("mainKey")
            raw_part_id = row.get("itemNo") or row.get("description") or "UNKNOWN"
            part_id = _normalize_part_code(raw_part_id)
            op_code = row.get("opCode") or ""
            machine_type = row.get("workcenterFlow") or row.get("workCenterNo")
            estimated_cycle = float(row.get("expectedCapacityNeedMin") or 0)
            due_date = _parse_date(row.get("dueDate"))

            normalized_suffix = _normalize_operation_suffix(op_code, row.get("lineNo"))
            operations.append(
                WorkOrderOperation(
                    work_order=work_order,
                    part_id=part_id,
                    raw_part_id=raw_part_id,
                    operation_id=row.get("systemIdLine") or f"{part_id}-{normalized_suffix}",
                    operation_code=normalized_suffix,
                    description=row.get("description"),
                    machine_type=machine_type,
                    required_quantity=int(row.get("inputQuantity") or 0),
                    completed_quantity=int(row.get("qtyfait") or 0),
                    estimated_cycle_minutes=estimated_cycle,
                    priority=int(row.get("priority") or 0),
                    allowed_machines=_parse_machine_flow(machine_type),
                    line_number=_safe_int(row.get("lineNo")),
                    part_numeric_id=_safe_int(part_id),
                    operation_numeric_id=_safe_int(row.get("lineNo")) or _safe_int(row.get("order")),
                    program_name=f"{raw_part_id}-{normalized_suffix}",
                )
            )
        return operations


def _parse_machine_flow(value: Optional[str]) -> Optional[List[str]]:
    if not value:
        return None
    parts = [part.strip().upper() for part in value.replace("→", " ").split() if part.strip()]
    machines = [p for p in parts if p.startswith("DMC")]
    return machines or None


def _safe_int(value: Optional[str]) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        digits = value.strip()
        if not digits:
            return None
        try:
            return int(digits)
        except ValueError:
            cleaned = "".join(ch for ch in digits if ch.isdigit())
            if not cleaned:
                return None
            try:
                return int(cleaned)
            except ValueError:
                return None
    return None


def _normalize_operation_suffix(op_code: Optional[str], line_no: Optional[object]) -> str:
    candidates: List[str] = []
    if op_code:
        cleaned = op_code.strip().upper().replace("_", "-")
        for token in cleaned.split("-"):
            token = token.strip()
            if not token:
                continue
            if token.endswith("OP"):
                suffix_digits = "".join(ch for ch in token if ch.isdigit())
                if suffix_digits:
                    token = f"{int(suffix_digits)}OP"
                candidates.append(token)
            elif token.isdigit():
                candidates.append(f"{int(token)}OP")
    if not candidates and line_no is not None:
        try:
            candidates.append(f"{int(line_no)}OP")
        except (TypeError, ValueError):
            pass
    if not candidates:
        candidates.append("1OP")
    return candidates[0]


def _parse_date(value: Optional[str]):
    if not value:
        return None
    try:
        sanitized = value.replace("Z", "+00:00")
        return datetime.fromisoformat(sanitized).date()
    except Exception:
        return None


class FixtureProvider:
    """Fixture and pallet lookup using the Cedule Autopilot view."""

    def __init__(self, repository: Optional[CeduleAutopilotRepository] = None) -> None:
        self._repository = repository or CeduleAutopilotRepository()
        self._default_pallets = self._repository.list_machine_pallets()

    def _piece_code(self, part_id: str, operation_code: Optional[str]) -> str:
        suffix = (operation_code or "1OP").upper()
        if not suffix.endswith("OP"):
            suffix = f"{suffix}OP"
        digits = "".join(ch for ch in suffix if ch.isdigit())
        if digits:
            suffix = f"{int(digits)}OP"
        return f"{part_id}-{suffix}".upper()

    async def get_fixture_states(
        self, part_id: str, operation_suffix: Optional[str]
    ) -> List[FixtureState]:
        piece_code = self._piece_code(part_id, operation_suffix)
        rows = self._repository.get_fixture_matrix(piece_code)
        if not rows:
            logger.info("Fixture matrix returned no rows", extra={"piece_code": piece_code})
        fixtures: Dict[str, FixtureState] = {}
        for row in rows:
            fixture_code = row.fixture_code or "UNKNOWN"
            # include the code in the description for traceability
            label = _format_fixture_label(fixture_code, row.fixture_description) or row.fixture_description
            if fixture_code not in fixtures:
                fixtures[fixture_code] = FixtureState(
                    fixture_code=fixture_code,
                    description=label,
                    storage_location=_normalize_location(row.storage_location),
                )
        return list(fixtures.values())

    async def get_ready_machine_pallets(
        self, part_id: str, operation_suffix: Optional[str]
    ) -> List[MachinePalletState]:
        piece_code = self._piece_code(part_id, operation_suffix)
        rows = self._repository.get_fixture_matrix(piece_code)
        logger.debug(
            "Loaded fixture rows for pallet selection",
            extra={
                "piece_code": piece_code,
                "row_count": len(rows),
                "with_pallet_assignments": sum(1 for row in rows if row.machine_pallet_id),
            },
        )
        pallets: List[MachinePalletState] = []
        required_plaque = None
        fallback_fixture = None
        for row in rows:
            if row.required_plaque_model:
                required_plaque = _normalize_code(row.required_plaque_model)
            if not fallback_fixture and row.fixture_code:
                fallback_fixture = _normalize_code(row.fixture_code)
            if not row.machine_pallet_id or not row.is_active:
                continue
            pallets.append(
                MachinePalletState(
                    pallet_id=str(row.machine_pallet_id),
                    numeric_id=row.machine_pallet_id,
                    pallet_number=row.machine_pallet_number,
                    fixture_code=_normalize_code(row.fixture_code),
                    machine_id=row.machine_id,
                    is_active=bool(row.is_active),
                    plaque_model=_normalize_code(row.pallet_plaque_model),
                )
            )

        # If no pallets from matrix, fall back to catalog filtered by plaque
        required_plaque = _normalize_code(required_plaque) or fallback_fixture
        if not pallets and required_plaque:
            logger.debug(
                "Falling back to default pallet list",
                extra={"piece_code": piece_code, "required_plaque": required_plaque},
            )
            for ref in self._default_pallets:
                if _normalize_code(ref.plaque_model) == required_plaque:
                    pallets.append(
                        MachinePalletState(
                            pallet_id=str(ref.pallet_id),
                            numeric_id=ref.pallet_id,
                            pallet_number=ref.pallet_number,
                            fixture_code=None,
                            machine_id=ref.machine_id,
                            is_active=False,
                            plaque_model=ref.plaque_model,
                        )
                    )
        logger.debug(
            "Resolved ready machine pallets",
            extra={
                "piece_code": piece_code,
                "selected_pallets": [p.pallet_id for p in pallets],
                "required_plaque": required_plaque,
            },
        )
        return pallets

    async def get_required_plaque_model(self, part_id: str, operation_suffix: Optional[str]) -> Optional[str]:
        piece_code = self._piece_code(part_id, operation_suffix)
        rows = self._repository.get_fixture_matrix(piece_code)
        for row in rows:
            if row.required_plaque_model:
                return _normalize_code(row.required_plaque_model)
        for row in rows:
            if row.fixture_code:
                return row.fixture_code
        return None

    async def get_fixture_details(
        self,
        part_id: str,
        operation_suffix: Optional[str],
        machine_pallet_id: Optional[str]
    ) -> Dict[str, Optional[str]]:
        piece_code = self._piece_code(part_id, operation_suffix)
        rows = self._repository.get_fixture_matrix(piece_code)
        required = None
        for row in rows:
            if row.fixture_code:
                required = _format_fixture_label(_normalize_code(row.fixture_code), row.fixture_description)
                break
        if not required and rows:
            required = _format_fixture_label(rows[0].fixture_code, rows[0].fixture_description)
        current = None
        for row in rows:
            if (
                machine_pallet_id
                and row.machine_pallet_id
                and str(row.machine_pallet_id) == machine_pallet_id
                and row.is_active
            ):
                current = _format_fixture_label(_normalize_code(row.fixture_code) or _normalize_code(row.pallet_plaque_model), row.fixture_description)
                break
        if current is None and machine_pallet_id:
            for ref in self._default_pallets:
                if str(ref.pallet_id) == machine_pallet_id:
                    current = _format_fixture_label(_normalize_code(ref.plaque_model), ref.description) or _normalize_code(ref.plaque_model)
                    break
        logger.debug(
            "Fixture detail lookup",
            extra={
                "piece_code": piece_code,
                "machine_pallet_id": machine_pallet_id,
                "required_fixture": required,
                "current_fixture": current,
            },
        )
        return {"required_fixture": required, "current_fixture": current}

    def get_compatible_machine_pallet(
        self,
        machine_id: str,
        plaque_model: Optional[str],
        exclude_ids: Optional[Set[str]] = None
    ) -> Optional[MachinePalletState]:
        exclude_ids = exclude_ids or set()
        machine_id_upper = (machine_id or "").upper()
        if plaque_model:
            normalized_plaque = _normalize_code(plaque_model)
            for ref in self._default_pallets:
                if (
                    _normalize_code(ref.plaque_model) == normalized_plaque
                    and ref.machine_id
                    and ref.machine_id.upper() == machine_id_upper
                    and str(ref.pallet_id) not in exclude_ids
                ):
                    return MachinePalletState(
                        pallet_id=str(ref.pallet_id),
                        numeric_id=ref.pallet_id,
                        pallet_number=ref.pallet_number,
                        machine_id=ref.machine_id,
                        is_active=False,
                        plaque_model=ref.plaque_model,
                    )
            for ref in self._default_pallets:
                if _normalize_code(ref.plaque_model) == normalized_plaque and str(ref.pallet_id) not in exclude_ids:
                    return MachinePalletState(
                        pallet_id=str(ref.pallet_id),
                        numeric_id=ref.pallet_id,
                        pallet_number=ref.pallet_number,
                        machine_id=ref.machine_id,
                        is_active=False,
                        plaque_model=ref.plaque_model,
                    )

            return None

        for ref in self._default_pallets:
            if ref.machine_id and ref.machine_id.upper() == machine_id_upper and str(ref.pallet_id) not in exclude_ids:
                return MachinePalletState(
                    pallet_id=str(ref.pallet_id),
                    numeric_id=ref.pallet_id,
                    pallet_number=ref.pallet_number,
                    machine_id=ref.machine_id,
                    is_active=False,
                    plaque_model=ref.plaque_model,
                )

        for ref in self._default_pallets:
            if str(ref.pallet_id) not in exclude_ids:
                return MachinePalletState(
                    pallet_id=str(ref.pallet_id),
                    numeric_id=ref.pallet_id,
                    pallet_number=ref.pallet_number,
                    machine_id=ref.machine_id,
                    is_active=False,
                    plaque_model=ref.plaque_model,
                )
        return None


class MaterialProvider:
    """Material pallet lookup via dy_storage API."""

    def __init__(self, client: Optional[FastemsMaterialClient] = None) -> None:
        self._client = client or FastemsMaterialClient()
        self._cache: Dict[str, List[MaterialPalletState]] = {}

    async def get_pallets_for_part(self, part_id: str) -> List[MaterialPalletState]:
        part_id = (part_id or "").strip()
        if not part_id:
            return []
        if part_id in self._cache:
            return self._cache[part_id]

        storage = await self._client.list_storage()
        pallets: List[MaterialPalletState] = []
        for row in storage:
            item = (row.get("ITEM_ID") or "").strip()
            if item != part_id:
                continue
            pallets.append(
                MaterialPalletState(
                    pallet_id=str(row.get("PALLET_NBR")),
                    content_type="raw",
                    work_order=None,
                    part_id=item,
                    quantity_available=row.get("AMOUNT"),
                    location=row.get("BATCH"),
                )
            )
        self._cache[part_id] = pallets
        return pallets


class PalletRouteProvider:
    """Provides live pallet route status."""

    def __init__(self, client: Optional[FastemsPalletRouteClient] = None) -> None:
        self._client = client or FastemsPalletRouteClient()
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._last_refresh: float = 0.0

    async def refresh(self, force: bool = False) -> None:
        import time

        now = time.monotonic()
        if not force and now - self._last_refresh < 5:
            return
        routes = await self._client.list_routes()
        cache: Dict[str, Dict[str, Any]] = {}
        for row in routes:
            pallet_key = str(row.get("PALLET_NBR"))
            cache[pallet_key] = {
                "phase": row.get("PHASE_NAME"),
                "phase_code": row.get("ROUTE_PHASE"),
                "command": row.get("COMMAND_DATA"),
            }
        self._cache = cache
        self._last_refresh = now

    async def ensure_cache(self) -> None:
        await self.refresh()

    def get_status(self, pallet_id: Optional[str]) -> Optional[Dict[str, Any]]:
        if pallet_id is None:
            return None
        return self._cache.get(str(pallet_id))


class ToolingProvider:
    """Combines NC program tool requirements and machine tool inventory."""

    def __init__(
        self,
        tooling_client: Optional[FastemsToolingClient] = None,
        nc_program_client: Optional[FastemsNCProgramClient] = None,
    ) -> None:
        self._tooling_client = tooling_client or FastemsToolingClient()
        self._nc_program_client = nc_program_client or FastemsNCProgramClient()

    async def get_tool_requirements(self, program_name: str) -> List[ToolRequirement]:
        normalized_name = (program_name or "").strip()
        rows = await self._nc_program_client.get_program_tools(normalized_name.lower())
        target_suffix = None
        if normalized_name:
            parts = normalized_name.upper().split("-")
            if parts:
                target_suffix = parts[-1]
        filtered_rows = rows
        if target_suffix:
            matches = []
            for row in rows:
                nc_name = (row.get("NC_NAME") or row.get("ncName") or "").strip().upper()
                if nc_name.endswith(target_suffix):
                    matches.append(row)
            if matches:
                filtered_rows = matches
        requirements: List[ToolRequirement] = []
        for row in filtered_rows:
            tool_id = row.get("TOOL_ID") or row.get("toolId")
            if not tool_id:
                continue
            requirements.append(
                ToolRequirement(
                    tool_id=str(tool_id),
                    description=row.get("DESCRIPTION"),
                    usage_time_seconds=row.get("USE_TIME"),
                )
            )
        return requirements

    async def get_machine_tool_states(self, machine_ids: List[int]) -> Dict[int, List[ToolState]]:
        async def _load(machine_id: int) -> List[ToolState]:
            inventory = await self._tooling_client.list_machine_tools(machine_id)
            results: List[ToolState] = []
            for tool in inventory:
                tool_id = tool.get("toolId") or tool.get("TOOL_ID")
                if not tool_id:
                    continue
                results.append(
                    ToolState(
                        tool_id=str(tool_id),
                        is_present=bool(tool.get("status")),
                        remaining_life_seconds=tool.get("remainingLifetime"),
                        usage_status=tool.get("usageStatus"),
                    )
                )
            return results

        tasks = [_load(machine_id) for machine_id in machine_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        data: Dict[int, List[ToolState]] = {}
        for machine_id, result in zip(machine_ids, results):
            if isinstance(result, Exception):
                logger.error("Failed to load tool inventory for machine %s: %s", machine_id, result)
                data[machine_id] = []
            else:
                data[machine_id] = result
        return data
def _normalize_part_code(value: str) -> str:
    cleaned = value.strip()
    if "_" in cleaned and "-" not in cleaned:
        cleaned = cleaned.replace("_", "-")
    return cleaned

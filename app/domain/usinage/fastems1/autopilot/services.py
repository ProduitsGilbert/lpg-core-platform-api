"""
Service layer for Fastems1 Autopilot.
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Sequence, Set
import logging

from fastapi import HTTPException, status

from app.domain.usinage.fastems1.autopilot.models import (
    ActionPlan,
    ActionPlanStep,
    PlanCandidate,
    ScoreBreakdown,
    ShiftWindow,
    SuggestionResult,
    ToolRequirement,
)
from app.domain.usinage.fastems1.autopilot.providers import (
    FixtureProvider,
    MaterialProvider,
    PalletRouteProvider,
    ToolingProvider,
    WorkOrderProvider,
)
from app.domain.usinage.fastems1.autopilot.repositories import (
    AutopilotRepository,
    PlannedJobRow,
)
from app.settings import settings

logger = logging.getLogger(__name__)


DEFAULT_MACHINE_IDS = ["DMC1", "DMC2", "DMC3", "DMC4"]
MACHINE_NAME_TO_ID = {"DMC1": 1, "DMC2": 2, "DMC3": 4, "DMC4": 5}


def _safe_int_for_id(value: Optional[str]) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        digits = "".join(ch for ch in str(value) if ch.isdigit())
        if not digits:
            return None
        try:
            return int(digits)
        except ValueError:
            return None


class AutopilotPlannerService:
    """Generates short-horizon plans per machine."""

    def __init__(
        self,
        repository: AutopilotRepository,
        workorder_provider: WorkOrderProvider,
        fixture_provider: FixtureProvider,
        tooling_provider: ToolingProvider,
        material_provider: MaterialProvider,
        pallet_route_provider: PalletRouteProvider,
    ) -> None:
        self._repository = repository
        self._workorder_provider = workorder_provider
        self._fixture_provider = fixture_provider
        self._tooling_provider = tooling_provider
        self._material_provider = material_provider
        self._pallet_route_provider = pallet_route_provider
        self._reserved_pallet_ids: Set[str] = set()

    async def refresh_plan(
        self,
        jobs_per_machine: Optional[int] = None,
        machine_ids: Optional[Sequence[str]] = None,
    ) -> Dict[str, object]:
        self._reserved_pallet_ids.clear()
        if jobs_per_machine is not None and jobs_per_machine <= 0:
            jobs_per_machine = None
        jobs_per_machine = jobs_per_machine if jobs_per_machine is not None else settings.fastems1_plan_jobs_per_machine
        machine_ids = list(machine_ids or DEFAULT_MACHINE_IDS)

        operations = await self._workorder_provider.list_active_operations()
        if not operations:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="No active work orders available for planning",
            )

        machine_status = self._repository.list_machine_status()
        available_machines = [
            machine
            for machine in machine_ids
            if _is_machine_available(machine_status.get(machine))
        ]
        if not available_machines:
            available_machines = machine_ids

        plan_entries: List[PlanCandidate] = []
        scheduled_jobs: Set[tuple[str, str, str]] = set()
        for machine_id in available_machines:
            machine_ops = _filter_operations_for_machine(operations, machine_id)
            if jobs_per_machine:
                machine_ops = machine_ops[:jobs_per_machine]
            for seq_index, op in enumerate(machine_ops, start=1):
                job_key = (op.work_order, op.part_id, op.operation_id)
                if job_key in scheduled_jobs:
                    continue
                ready_pallet = await self._pick_ready_pallet(op.part_id, op.operation_code, machine_id)
                estimated_setup = 12.0 if ready_pallet else 25.0
                material_pallet = await self._pick_material_pallet(op.part_id)
                plan_entries.append(
                    PlanCandidate(
                        work_order=op.work_order,
                        part_id=op.part_id,
                        operation_id=op.operation_id,
                        machine_id=machine_id,
                        machine_pallet_id=ready_pallet.pallet_id if ready_pallet else None,
                        material_pallet_id=material_pallet.pallet_id if material_pallet else None,
                        estimated_setup_minutes=estimated_setup,
                        estimated_cycle_minutes=max(op.estimated_cycle_minutes, 1.0),
                        sequence_index=seq_index,
                        part_numeric_id=op.part_numeric_id,
                        operation_numeric_id=op.operation_numeric_id or op.line_number,
                        machine_pallet_numeric_id=ready_pallet.numeric_id if ready_pallet else None,
                        material_pallet_numeric_id=_safe_int_for_id(material_pallet.pallet_id) if material_pallet else None,
                        program_name=op.program_name,
                    )
                )
                scheduled_jobs.add(job_key)

        if not plan_entries:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="No eligible plan entries were generated",
            )

        plan_batch_id = self._repository.create_plan_batch(plan_entries)
        return {
            "plan_batch_id": plan_batch_id,
            "machines": available_machines,
            "planned_jobs": len(plan_entries),
        }

    async def _pick_ready_pallet(self, part_id: str, operation_code: Optional[str], machine_id: str):
        ready_pallets = await self._fixture_provider.get_ready_machine_pallets(part_id, operation_code)
        required_plaque = await self._fixture_provider.get_required_plaque_model(part_id, operation_code)

        await self._pallet_route_provider.ensure_cache()
        status_cache: Dict[str, Optional[Dict[str, Any]]] = {}
        for pallet in ready_pallets:
            status_cache[pallet.pallet_id] = self._pallet_route_provider.get_status(pallet.pallet_id)

        def sort_rank(pallet: MachinePalletState) -> int:
            status = status_cache.get(pallet.pallet_id or "")
            phase = (status.get("phase") if status else "") or ""
            phase_lower = phase.lower()
            if "fin" in phase_lower:
                return 0
            if "usinage" in phase_lower:
                return 2
            return 1

        ready_pallets.sort(key=sort_rank)

        def _normalize_plaque(value: Optional[str]) -> Optional[str]:
            if value is None:
                return None
            cleaned = value.strip()
            return cleaned or None

        def _is_pallet_compatible(pallet: MachinePalletState) -> bool:
            if not required_plaque:
                return True
            candidate = _normalize_plaque(pallet.plaque_model) or _normalize_plaque(pallet.fixture_code)
            if candidate and candidate == required_plaque:
                return True
            return False

        for pallet in ready_pallets:
            if pallet.pallet_id in self._reserved_pallet_ids:
                continue
            if not _is_pallet_compatible(pallet):
                continue
            if not _pallet_phase_is_finished(status_cache.get(pallet.pallet_id or "")):
                continue
            if pallet.machine_id and pallet.machine_id.upper() == machine_id.upper():
                self._reserved_pallet_ids.add(pallet.pallet_id)
                return pallet
        for pallet in ready_pallets:
            if pallet.pallet_id in self._reserved_pallet_ids:
                continue
            if not _is_pallet_compatible(pallet):
                continue
            if not _pallet_phase_is_finished(status_cache.get(pallet.pallet_id or "")):
                continue
            self._reserved_pallet_ids.add(pallet.pallet_id)
            return pallet

        compatible = self._fixture_provider.get_compatible_machine_pallet(
            machine_id,
            required_plaque,
            exclude_ids=self._reserved_pallet_ids,
        )
        if compatible and compatible.pallet_id:
            status = self._pallet_route_provider.get_status(compatible.pallet_id)
            if _pallet_phase_is_finished(status):
                self._reserved_pallet_ids.add(compatible.pallet_id)
                return compatible

        return None

    async def _pick_material_pallet(self, part_id: str):
        pallets = await self._material_provider.get_pallets_for_part(part_id)
        return pallets[0] if pallets else None


def _is_machine_available(status_row: Optional[dict]) -> bool:
    if not status_row:
        return True
    if str(status_row.get("IsAvailable")) in {"0", "False", "false"}:
        return False
    if status_row.get("Status") and status_row["Status"].lower() not in {"available", "idle"}:
        return False
    return True


def _filter_operations_for_machine(operations, machine_id: str):
    machine_id_upper = machine_id.upper()
    filtered = [
        op for op in operations if not op.allowed_machines or machine_id_upper in {m.upper() for m in (op.allowed_machines or [])}
    ]
    if not filtered:
        return operations
    return filtered


class AutopilotSuggestionService:
    """Uses plan entries plus runtime context to pick the best next job."""

    def __init__(
        self,
        repository: AutopilotRepository,
        fixture_provider: FixtureProvider,
        tooling_provider: ToolingProvider,
        pallet_route_provider: PalletRouteProvider,
        workorder_provider: WorkOrderProvider,
    ) -> None:
        self._repository = repository
        self._fixture_provider = fixture_provider
        self._tooling_provider = tooling_provider
        self._pallet_route_provider = pallet_route_provider
        self._workorder_provider = workorder_provider

    async def next_suggestion(self, max_alternatives: int = 0, include_details: bool = False) -> SuggestionResult:
        plan_batch_id = self._repository.fetch_latest_plan_batch()
        if not plan_batch_id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "No plan batch available")

        planned_jobs = self._repository.list_planned_jobs(plan_batch_id)
        await self._hydrate_job_metadata(planned_jobs)
        planned_jobs = [job for job in planned_jobs if job.status == "planned"]
        if not planned_jobs:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "No planned jobs remaining in batch")

        ignores = self._repository.list_active_ignores()

        eligible = [job for job in planned_jobs if not _is_ignored(job, ignores)]
        if not eligible:
            raise HTTPException(status.HTTP_409_CONFLICT, "All planned jobs are currently ignored")

        shift_window = self._repository.get_active_shift_window()

        machine_numeric_ids = sorted(
            {
                MACHINE_NAME_TO_ID.get((job.machine_id or "").upper())
                for job in eligible
                if MACHINE_NAME_TO_ID.get((job.machine_id or "").upper())
            }
        )
        tool_inventories: Dict[int, Dict[str, ToolState]] = {}
        if machine_numeric_ids:
            tool_lists = await self._tooling_provider.get_machine_tool_states(machine_numeric_ids)
            for machine_id, states in tool_lists.items():
                tool_inventories[machine_id] = {
                    str(state.tool_id): state for state in states if state.tool_id is not None
                }
        program_tool_cache: Dict[str, List[ToolRequirement]] = {}
        tool_penalties: Dict[int, float] = {}
        tool_missing: Dict[int, List[str]] = {}
        for job in eligible:
            penalty, missing = await self._tool_penalty(job, tool_inventories, program_tool_cache)
            tool_penalties[job.planned_job_id] = penalty
            tool_missing[job.planned_job_id] = missing
            if missing:
                logger.info(
                    "Job %s/%s on %s missing tools: %s",
                    job.work_order,
                    job.part_id,
                    job.machine_id,
                    ",".join(missing),
                )

        scored = []
        for job in eligible:
            score = self._score_job(job, shift_window, tool_penalties.get(job.planned_job_id, 0.0))
            scored.append((score, job))

        scored.sort(key=lambda item: item[0].total)
        best_score, best_job = scored[0]
        action_plan = await self._build_action_plan(best_job)
        decision_id = self._repository.insert_decision(
            best_job,
            best_score,
            action_plan=asdict(action_plan),
            shift_window_id=shift_window.shift_window_id if shift_window else None,
        )
        if decision_id:
            self._repository.update_planned_job_status(best_job.planned_job_id, "dispatched", decision_id)

        alternatives = [PlanCandidate(
            work_order=job.work_order,
            part_id=job.part_id,
            operation_id=job.operation_id,
            machine_id=job.machine_id,
            machine_pallet_id=job.machine_pallet_id,
            material_pallet_id=job.material_pallet_id,
            estimated_setup_minutes=job.estimated_setup_minutes,
            estimated_cycle_minutes=job.estimated_cycle_minutes,
            sequence_index=job.sequence_index,
            score=self._score_job(job, shift_window, tool_penalties.get(job.planned_job_id, 0.0)),
        ) for _, job in scored[1 : 1 + max(0, max_alternatives)]]

        details_payload = None
        if include_details:
            details_payload = await self._build_details(best_job, tool_missing.get(best_job.planned_job_id, []))

        return SuggestionResult(
            decision_id=decision_id,
            machine_id=best_job.machine_id,
            work_order=best_job.work_order,
            part_id=best_job.part_id,
            operation_id=best_job.operation_id,
            machine_pallet_id=best_job.machine_pallet_id,
            material_pallet_id=best_job.material_pallet_id,
            estimated_setup_minutes=best_job.estimated_setup_minutes,
            estimated_cycle_minutes=best_job.estimated_cycle_minutes,
            score=best_score,
            action_plan=action_plan,
            alternatives=alternatives,
            details=details_payload,
        )

    def _score_job(self, job: PlannedJobRow, shift_window: Optional[ShiftWindow], tool_penalty_value: float = 0.0) -> ScoreBreakdown:
        weight_short = shift_window.weight_short_setup if shift_window else 1.0
        weight_long = shift_window.weight_long_run if shift_window else 1.0
        weight_balance = shift_window.weight_machine_balance if shift_window else 1.0
        weight_tool = shift_window.weight_tool_penalty if shift_window else 1.0

        setup_penalty = float(job.estimated_setup_minutes or 0.0) * weight_short
        cycle_penalty = float(job.estimated_cycle_minutes or 0.0) / max(weight_long, 0.1)
        balance_penalty = job.sequence_index * weight_balance
        tool_penalty = tool_penalty_value * weight_tool
        total = setup_penalty + cycle_penalty + balance_penalty + tool_penalty
        return ScoreBreakdown(
            total=total,
            tool_penalty=tool_penalty,
            setup_penalty=setup_penalty,
            material_penalty=0.0,
            balance_penalty=balance_penalty,
        )

    async def _build_action_plan(self, job: PlannedJobRow) -> ActionPlan:
        await self._pallet_route_provider.ensure_cache()
        pallet_status = self._pallet_route_provider.get_status(job.machine_pallet_id)
        op_suffix = _derive_operation_suffix(job)
        fixture_details = await self._fixture_provider.get_fixture_details(
            job.part_id,
            op_suffix,
            job.machine_pallet_id,
        )
        required_fixture = fixture_details.get("required_fixture")
        current_fixture = fixture_details.get("current_fixture")

        steps: List[ActionPlanStep] = []
        if _pallet_phase_is_finished(pallet_status):
            steps.append(
                ActionPlanStep(
                    step_type="UNLOAD_FINISHED_PART",
                    description=_build_finished_part_description(job.machine_pallet_id, pallet_status),
                    metadata={"phase": pallet_status.get("phase")} if pallet_status else None,
                )
            )
        normalized_current = current_fixture.strip() if current_fixture else None
        normalized_required = required_fixture.strip() if required_fixture else None
        if normalized_required:
            if normalized_current and normalized_current == normalized_required:
                steps.append(
                    ActionPlanStep(
                        step_type="VERIFY_FIXTURE",
                        description=f"Verify fixture {required_fixture} is secure on pallet {_pallet_label(job.machine_pallet_id)}.",
                        metadata={"fixture": required_fixture},
                    )
                )
            elif normalized_current and normalized_current != normalized_required:
                        steps.append(
                            ActionPlanStep(
                                step_type="REMOVE_FIXTURE",
                                description=f"Remove fixture {current_fixture} from pallet {_pallet_label(job.machine_pallet_id)}.",
                                metadata={"fixture": current_fixture},
                            )
                        )
                        steps.append(
                            ActionPlanStep(
                                step_type="INSTALL_FIXTURE",
                                description=f"Install fixture {required_fixture} on pallet {_pallet_label(job.machine_pallet_id)} before setup.",
                                metadata={"fixture": required_fixture},
                            )
                        )
            else:
                steps.append(
                    ActionPlanStep(
                        step_type="INSTALL_FIXTURE",
                        description=f"Install fixture {required_fixture} on pallet {_pallet_label(job.machine_pallet_id)} before setup.",
                        metadata={"fixture": required_fixture},
                    )
                )
        elif normalized_current:
            steps.append(
                ActionPlanStep(
                    step_type="REMOVE_FIXTURE",
                    description=f"Remove fixture {current_fixture} from pallet {_pallet_label(job.machine_pallet_id)}.",
                    metadata={"fixture": current_fixture},
                )
            )
            steps.append(
                ActionPlanStep(
                    step_type="CONFIRM_FIXTURE",
                    description="Confirm required fixture from setup sheet before loading.",
                )
            )
        else:
            steps.append(
                ActionPlanStep(
                    step_type="CONFIRM_FIXTURE",
                    description="Confirm required fixture from setup sheet before loading.",
                )
            )

        steps.append(
            ActionPlanStep(
                step_type="LOAD_RAW_MATERIAL",
                description=f"Load work order {job.work_order} part {job.part_id}",
                metadata={"material_pallet_id": job.material_pallet_id},
            )
        )

        op_suffix = _derive_operation_suffix(job)
        fixture_info = await self._fixture_provider.get_fixture_states(job.part_id, op_suffix)
        hardware = [
            {"item": fixture.fixture_code, "description": fixture.description, "location": fixture.storage_location}
            for fixture in fixture_info[:3]
        ]
        return ActionPlan(steps=steps, fixture_hardware_list=hardware)

    async def _tool_penalty(
        self,
        job: PlannedJobRow,
        tool_inventories: Dict[int, Dict[str, ToolState]],
        cache: Dict[str, List[str]],
    ) -> tuple[float, List[str]]:
        machine_numeric = MACHINE_NAME_TO_ID.get((job.machine_id or "").upper())
        if not machine_numeric:
            return 0.0, []
        program_name = getattr(job, "_program_name_override", None) or _derive_program_name(job)
        if not program_name:
            return 0.0, []
        if program_name not in cache:
            requirements = await self._tooling_provider.get_tool_requirements(program_name)
            cache[program_name] = requirements
        requirements = cache.get(program_name) or []
        if not requirements:
            return 0.0, []
        inventory = tool_inventories.get(machine_numeric)
        if inventory is None:
            logger.warning(
                "Tool inventory unavailable for machine %s; assuming no penalty for %s",
                job.machine_id,
                program_name,
            )
            return 0.0, []
        missing: List[str] = []
        for req in requirements:
            tool_id = str(req.tool_id).strip()
            if tool_id not in inventory:
                missing.append(tool_id)
                continue
            state = inventory[tool_id]
            required_time = (req.usage_time_seconds or 0) / 60.0  # convert seconds to minutes
            remaining = (state.remaining_life_seconds or 0) / 60.0
            if remaining <= 0 or remaining < required_time:
                missing.append(tool_id)
        penalty = float(len(missing)) * 5.0
        return penalty, missing

    async def _build_details(self, job: PlannedJobRow, missing_tools: List[str]) -> Dict[str, Any]:
        suffix = _derive_operation_suffix(job)
        fixture_info = await self._fixture_provider.get_fixture_details(
            job.part_id,
            suffix,
            job.machine_pallet_id,
        )
        pallet_status = self._pallet_route_provider.get_status(job.machine_pallet_id)
        return {
            "machine_pallet": job.machine_pallet_id,
            "material_pallet": job.material_pallet_id,
            "fixture_required": fixture_info.get("required_fixture"),
            "fixture_current": fixture_info.get("current_fixture"),
            "missing_tools_count": len(missing_tools),
            "missing_tools": missing_tools,
        }

    async def _hydrate_job_metadata(self, jobs: List[PlannedJobRow]) -> None:
        if not jobs:
            return
        operations = await self._workorder_provider.list_active_operations()
        lookup: Dict[tuple[str, Optional[int]], WorkOrderOperation] = {}
        for op in operations:
            key = (op.work_order, op.operation_numeric_id or op.line_number)
            lookup[key] = op
        for job in jobs:
            key = (job.work_order, job.operation_numeric_id)
            op = lookup.get(key)
            if not op:
                continue
            job.part_id = op.part_id
            setattr(job, "_program_name_override", op.program_name)


def _is_ignored(job: PlannedJobRow, ignores: Sequence[dict]) -> bool:
    for ignore in ignores:
        if (
            ignore.get("WorkOrder") == job.work_order
            and ignore.get("PartId") == job.part_id
            and ignore.get("OperationId") == job.operation_id
        ):
            return True
    return False


class AutopilotControlService:
    """Handles refusal, machine status, and setup tracking endpoints."""

    def __init__(self, repository: AutopilotRepository) -> None:
        self._repository = repository

    def refuse_job(self, planned_job: PlannedJobRow, decision_id: Optional[int], reason: Optional[str]) -> None:
        ignore_until = datetime.now(timezone.utc) + timedelta(hours=settings.fastems1_ignore_ttl_hours)
        self._repository.insert_ignore(planned_job, ignore_until, reason, decision_id)
        self._repository.update_planned_job_status(planned_job.planned_job_id, "skipped", decision_id)

    def set_machine_status(self, machine_id: str, is_available: bool, status_text: str, reason: Optional[str]) -> Dict[str, dict]:
        self._repository.upsert_machine_status(machine_id, is_available, status_text, reason)
        return self._repository.list_machine_status()

    def start_setup_session(
        self,
        machine_id: str,
        machine_pallet_id: Optional[str],
        work_order: Optional[str],
        part_id: Optional[str],
        operation_id: Optional[str],
        setup_type: Optional[str],
        decision_id: Optional[int],
    ) -> Optional[int]:
        return self._repository.create_setup_session(
            machine_id=machine_id,
            machine_pallet_id=machine_pallet_id,
            work_order=work_order,
            part_id=part_id,
            operation_id=operation_id,
            setup_type=setup_type,
            decision_id=decision_id,
        )

    def end_setup_session(self, setup_id: int) -> bool:
        return self._repository.complete_setup_session(setup_id)


def _derive_operation_suffix(job: PlannedJobRow) -> str:
    op_value = str(job.operation_id or "").strip()
    suffix = None
    try:
        op_num = int(float(op_value))
        if op_num >= 10000:
            suffix = f"{max(op_num // 10000, 1)}OP"
    except ValueError:
        pass
    if not suffix:
        cleaned = op_value.upper()
        if not cleaned.endswith("OP"):
            cleaned = f"{cleaned}OP"
        digits = "".join(ch for ch in cleaned if ch.isdigit())
        if digits:
            suffix = f"{int(digits)}OP"
        else:
            suffix = "1OP"
    return suffix


def _derive_program_name(job: PlannedJobRow) -> Optional[str]:
    part = str(job.part_id or "").strip()
    if not part:
        return None
    suffix = _derive_operation_suffix(job)
    return f"{part}-{suffix}"


def _pallet_label(pallet_id: Optional[str]) -> str:
    return pallet_id or "TBD"


def _build_finished_part_description(pallet_id: Optional[str], status: Optional[Dict[str, Any]]) -> str:
    phase = (status or {}).get("phase")
    if phase:
        return f"Unload finished part from pallet {_pallet_label(pallet_id)} (phase: {phase}) before reloading."
    return f"Unload finished part from pallet {_pallet_label(pallet_id)} before reloading."


def _pallet_phase_is_finished(status: Optional[Dict[str, Any]]) -> bool:
    if status is None:
        return True
    phase = status.get("phase")
    if not phase:
        return True
    return "fin" in phase.lower()

"""
Database access helpers for Fastems1 Autopilot tables.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time as time_type, timedelta, timezone
from typing import Dict, List, Optional, Sequence
import logging
import random
import time
import uuid

import json

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from zoneinfo import ZoneInfo

from app.domain.usinage.fastems1.autopilot.models import PlanCandidate, ScoreBreakdown, ShiftWindow
from app.settings import settings

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


_memory_state: Dict[str, List[PlanCandidate]] = {}
_memory_machine_status: Dict[str, Dict[str, str]] = {}


def _generate_plan_batch_id() -> int:
    base = int(time.time() * 1_000_000)
    return base + random.randint(0, 999)


def _coerce_int(value: Optional[int], fallback: Optional[str], max_value: int = 2_147_483_647) -> int:
    def _bound(number: int) -> int:
        number = abs(int(number))
        if number <= max_value:
            return number
        return number % max_value or max_value

    if value is not None:
        try:
            return _bound(int(value))
        except (TypeError, ValueError):
            pass
    if fallback:
        digits = "".join(ch for ch in fallback if ch.isdigit())
        if digits:
            try:
                return _bound(int(digits))
            except ValueError:
                pass
        return _bound(abs(hash(fallback)))
    return 0


def _coerce_bigint(value: Optional[int], fallback: Optional[str]) -> int:
    if value is not None:
        return int(value)
    if fallback:
        data = abs(hash(fallback)) % 9_000_000_000_000_000
        return data or 1
    return int(time.time() * 1_000_000)


def _normalize_db_pallet_id(value: Optional[int]) -> Optional[str]:
    if value in (None, 0):
        return None
    return str(value)


def _is_time_in_window(current: time_type, start: time_type, end: time_type) -> bool:
    if start <= end:
        return start <= current < end
    return current >= start or current < end


@dataclass
class PlannedJobRow:
    planned_job_id: int
    plan_batch_id: str
    machine_id: str
    sequence_index: int
    work_order: str
    part_id: str
    operation_id: str
    machine_pallet_id: Optional[str]
    material_pallet_id: Optional[str]
    estimated_setup_minutes: float
    estimated_cycle_minutes: float
    status: str
    part_numeric_id: Optional[int] = None
    operation_numeric_id: Optional[int] = None
    machine_pallet_numeric_id: Optional[int] = None
    material_pallet_numeric_id: Optional[int] = None


class AutopilotRepository:
    """Read/write access to fastems1.Autopilot* tables with graceful fallbacks."""

    def __init__(self, session: Optional[Session]) -> None:
        self._session = session

    def _execute(self, statement: str, params: Optional[dict] = None) -> bool:
        if not self._session:
            return False
        try:
            self._session.execute(text(statement), params or {})
            return True
        except SQLAlchemyError as exc:
            logger.error("Autopilot SQL execution failed", exc_info=exc)
            return False

    def create_plan_batch(self, entries: Sequence[PlanCandidate]) -> str:
        plan_batch_numeric = _generate_plan_batch_id()
        plan_batch_id = str(plan_batch_numeric)
        ts_now = _utcnow()
        if not entries:
            return plan_batch_id

        if self._session:
            try:
                self._session.execute(
                    text(
                        """
                        UPDATE fastems1.AutopilotPlannedJob
                        SET Status = 'cancelled'
                        WHERE Status = 'planned'
                        """
                    )
                )
            except SQLAlchemyError as exc:
                logger.error("Failed to retire previous planned jobs", exc_info=exc)
            try:
                insert_stmt = text(
                    """
                    INSERT INTO fastems1.AutopilotPlannedJob
                    (
                        PlanBatchId,
                        TsPlannedUtc,
                        MachineId,
                        SequenceIndex,
                        WorkOrder,
                        PartId,
                        OperationId,
                        MachinePalletId,
                        MaterialPalletId,
                        EstimatedSetupMinutes,
                        EstimatedCycleMinutes,
                        Status
                    )
                    VALUES
                    (
                        :plan_batch_id,
                        :ts_planned,
                        :machine_id,
                        :sequence_index,
                        :work_order,
                        :part_id,
                        :operation_id,
                        :machine_pallet_id,
                        :material_pallet_id,
                        :estimated_setup,
                        :estimated_cycle,
                        'planned'
                    )
                    """
                )
                for entry in entries:
                    part_numeric = _coerce_int(entry.part_numeric_id, entry.part_id)
                    operation_numeric = _coerce_int(entry.operation_numeric_id, entry.operation_id)
                    if entry.machine_pallet_numeric_id is not None:
                        machine_pallet_numeric = entry.machine_pallet_numeric_id
                    elif entry.machine_pallet_id:
                        machine_pallet_numeric = _coerce_int(None, entry.machine_pallet_id)
                    else:
                        machine_pallet_numeric = None

                    if entry.material_pallet_id or entry.material_pallet_numeric_id:
                        material_pallet_numeric = _coerce_int(
                            entry.material_pallet_numeric_id,
                            entry.material_pallet_id or f"MAT-{entry.part_id}",
                        )
                    else:
                        material_pallet_numeric = None
                    self._session.execute(
                        insert_stmt,
                        {
                            "plan_batch_id": plan_batch_numeric,
                            "ts_planned": ts_now,
                            "machine_id": entry.machine_id,
                            "sequence_index": entry.sequence_index,
                            "work_order": entry.work_order,
                            "part_id": part_numeric,
                            "operation_id": operation_numeric,
                            "machine_pallet_id": machine_pallet_numeric,
                            "material_pallet_id": material_pallet_numeric,
                            "estimated_setup": entry.estimated_setup_minutes,
                            "estimated_cycle": entry.estimated_cycle_minutes,
                        },
                    )
                return plan_batch_id
            except SQLAlchemyError as exc:
                logger.error("Failed to insert Autopilot plan batch", exc_info=exc)
                self._session.rollback()

        _memory_state[plan_batch_id] = list(entries)
        return plan_batch_id

    def fetch_latest_plan_batch(self) -> Optional[str]:
        if self._session:
            try:
                result = self._session.execute(
                    text(
                        """
                        SELECT TOP 1 PlanBatchId
                        FROM fastems1.AutopilotPlannedJob
                        ORDER BY TsPlannedUtc DESC
                        """
                    )
                ).scalar()
                if result:
                    return str(result)
            except SQLAlchemyError as exc:
                logger.error("Failed to fetch Autopilot plan batch", exc_info=exc)

        if _memory_state:
            return next(reversed(_memory_state.keys()))
        return None

    def list_planned_jobs(self, plan_batch_id: str) -> List[PlannedJobRow]:
        rows: List[PlannedJobRow] = []
        if self._session:
            try:
                result = self._session.execute(
                    text(
                        """
                        SELECT
                            PlannedJobId,
                            PlanBatchId,
                            MachineId,
                            SequenceIndex,
                            WorkOrder,
                            PartId,
                            OperationId,
                            MachinePalletId,
                            MaterialPalletId,
                            EstimatedSetupMinutes,
                            EstimatedCycleMinutes,
                            Status
                        FROM fastems1.AutopilotPlannedJob
                        WHERE PlanBatchId = :plan_batch_id
                        ORDER BY MachineId, SequenceIndex
                        """
                    ),
                    {"plan_batch_id": plan_batch_id},
                )
                for row in result:
                    machine_pallet_id = _normalize_db_pallet_id(row.MachinePalletId)
                    rows.append(
                        PlannedJobRow(
                            planned_job_id=row.PlannedJobId,
                            plan_batch_id=str(row.PlanBatchId),
                            machine_id=row.MachineId,
                            sequence_index=row.SequenceIndex,
                            work_order=row.WorkOrder,
                            part_id=str(row.PartId),
                            operation_id=str(row.OperationId),
                            machine_pallet_id=machine_pallet_id,
                            material_pallet_id=str(row.MaterialPalletId) if row.MaterialPalletId is not None else None,
                            estimated_setup_minutes=row.EstimatedSetupMinutes,
                            estimated_cycle_minutes=row.EstimatedCycleMinutes,
                            status=row.Status,
                            part_numeric_id=row.PartId,
                            operation_numeric_id=row.OperationId,
                            machine_pallet_numeric_id=row.MachinePalletId if machine_pallet_id is not None else None,
                            material_pallet_numeric_id=row.MaterialPalletId,
                        )
                    )
                return rows
            except SQLAlchemyError as exc:
                logger.error("Failed to list Autopilot planned jobs", exc_info=exc)

        entries = _memory_state.get(plan_batch_id, [])
        for idx, entry in enumerate(entries, start=1):
            rows.append(
                PlannedJobRow(
                    planned_job_id=idx,
                    plan_batch_id=plan_batch_id,
                    machine_id=entry.machine_id,
                    sequence_index=entry.sequence_index,
                    work_order=entry.work_order,
                    part_id=entry.part_id,
                    operation_id=entry.operation_id,
                    machine_pallet_id=entry.machine_pallet_id,
                    material_pallet_id=entry.material_pallet_id,
                    estimated_setup_minutes=entry.estimated_setup_minutes,
                    estimated_cycle_minutes=entry.estimated_cycle_minutes,
                    status="planned",
                    part_numeric_id=entry.part_numeric_id,
                    operation_numeric_id=entry.operation_numeric_id,
                    machine_pallet_numeric_id=entry.machine_pallet_numeric_id,
                    material_pallet_numeric_id=entry.material_pallet_numeric_id,
                )
            )
        return rows

    def get_planned_job(self, planned_job_id: int) -> Optional[PlannedJobRow]:
        if self._session:
            try:
                row = self._session.execute(
                    text(
                        """
                        SELECT
                            PlannedJobId,
                            PlanBatchId,
                            MachineId,
                            SequenceIndex,
                            WorkOrder,
                            PartId,
                            OperationId,
                            MachinePalletId,
                            MaterialPalletId,
                            EstimatedSetupMinutes,
                            EstimatedCycleMinutes,
                            Status
                        FROM fastems1.AutopilotPlannedJob
                        WHERE PlannedJobId = :planned_job_id
                        """
                    ),
                    {"planned_job_id": planned_job_id},
                ).first()
                if row:
                    machine_pallet_id = _normalize_db_pallet_id(row.MachinePalletId)
                    return PlannedJobRow(
                        planned_job_id=row.PlannedJobId,
                        plan_batch_id=str(row.PlanBatchId),
                        machine_id=row.MachineId,
                        sequence_index=row.SequenceIndex,
                        work_order=row.WorkOrder,
                        part_id=str(row.PartId),
                        operation_id=str(row.OperationId),
                        machine_pallet_id=machine_pallet_id,
                        material_pallet_id=str(row.MaterialPalletId) if row.MaterialPalletId is not None else None,
                        estimated_setup_minutes=row.EstimatedSetupMinutes,
                        estimated_cycle_minutes=row.EstimatedCycleMinutes,
                        status=row.Status,
                        part_numeric_id=row.PartId,
                        operation_numeric_id=row.OperationId,
                        machine_pallet_numeric_id=row.MachinePalletId if machine_pallet_id is not None else None,
                        material_pallet_numeric_id=row.MaterialPalletId,
                    )
            except SQLAlchemyError as exc:
                logger.error("Failed to retrieve planned job", exc_info=exc)
        for batch_entries in _memory_state.values():
            for idx, entry in enumerate(batch_entries, start=1):
                if idx == planned_job_id:
                    return PlannedJobRow(
                        planned_job_id=idx,
                        plan_batch_id="memory",
                        machine_id=entry.machine_id,
                        sequence_index=entry.sequence_index,
                        work_order=entry.work_order,
                        part_id=entry.part_id,
                        operation_id=entry.operation_id,
                        machine_pallet_id=entry.machine_pallet_id,
                        material_pallet_id=entry.material_pallet_id,
                        estimated_setup_minutes=entry.estimated_setup_minutes,
                        estimated_cycle_minutes=entry.estimated_cycle_minutes,
                        status="planned",
                    )
        return None

    def insert_decision(
        self,
        job: PlannedJobRow,
        score: ScoreBreakdown,
        action_plan: dict,
        shift_window_id: Optional[int],
    ) -> Optional[int]:
        if not self._session:
            return None

        try:
            result = self._session.execute(
                text(
                    """
                    INSERT INTO fastems1.AutopilotDecision
                    (
                        TsUtc,
                        MachineId,
                        WorkOrder,
                        PartId,
                        OperationId,
                        SuggestedMachinePalletId,
                        SuggestedMaterialPalletId,
                        EstimatedSetupMinutes,
                        EstimatedCycleMinutes,
                        ScoreTotal,
                        ScoreToolPenalty,
                        ScoreSetupPenalty,
                        ScoreMaterialPenalty,
                        ScoreBalancePenalty,
                        ShiftWindowId,
                        PayloadJson
                    )
                    OUTPUT Inserted.DecisionId
                    VALUES
                    (
                        SYSUTCDATETIME(),
                        :machine_id,
                        :work_order,
                        :part_id,
                        :operation_id,
                        :machine_pallet_id,
                        :material_pallet_id,
                        :estimated_setup,
                        :estimated_cycle,
                        :score_total,
                        :score_tool,
                        :score_setup,
                        :score_material,
                        :score_balance,
                        :shift_window_id,
                        :payload_json
                    )
                    """
                ),
                {
                    "machine_id": job.machine_id,
                    "work_order": job.work_order,
                    "part_id": job.part_numeric_id or _coerce_int(None, job.part_id),
                    "operation_id": job.operation_numeric_id or _coerce_int(None, job.operation_id),
                    "machine_pallet_id": job.machine_pallet_numeric_id,
                    "material_pallet_id": job.material_pallet_numeric_id,
                    "estimated_setup": job.estimated_setup_minutes,
                    "estimated_cycle": job.estimated_cycle_minutes,
                    "score_total": score.total,
                    "score_tool": score.tool_penalty,
                    "score_setup": score.setup_penalty,
                    "score_material": score.material_penalty,
                    "score_balance": score.balance_penalty,
                    "shift_window_id": shift_window_id,
                    "payload_json": json.dumps(action_plan),
                },
            )
            decision_id = result.scalar_one()
            return int(decision_id)
        except SQLAlchemyError as exc:
            logger.error("Failed to insert Autopilot decision", exc_info=exc)
            return None

    def update_planned_job_status(self, planned_job_id: int, status: str, decision_id: Optional[int] = None) -> None:
        if not self._session:
            return
        try:
            self._session.execute(
                text(
                    """
                    UPDATE fastems1.AutopilotPlannedJob
                    SET Status = :status,
                        DecisionId = COALESCE(:decision_id, DecisionId)
                    WHERE PlannedJobId = :planned_job_id
                    """
                ),
                {
                    "status": status,
                    "decision_id": decision_id,
                    "planned_job_id": planned_job_id,
                },
            )
        except SQLAlchemyError as exc:
            logger.error("Failed to update planned job status", exc_info=exc)

    def insert_ignore(self, job: PlannedJobRow, ignore_until: datetime, reason: Optional[str], decision_id: Optional[int]) -> None:
        if self._session:
            try:
                self._session.execute(
                    text(
                        """
                        INSERT INTO fastems1.AutopilotJobIgnore
                        (
                            TsUtc,
                            WorkOrder,
                            PartId,
                            OperationId,
                            MachinePalletId,
                            IgnoreUntilUtc,
                            Reason,
                            DecisionId
                        )
                        VALUES
                        (
                            SYSUTCDATETIME(),
                            :work_order,
                            :part_id,
                            :operation_id,
                            :machine_pallet_id,
                            :ignore_until,
                            :reason,
                            :decision_id
                        )
                        """
                    ),
                    {
                        "work_order": job.work_order,
                        "part_id": job.part_numeric_id or _coerce_int(None, job.part_id),
                        "operation_id": job.operation_numeric_id or _coerce_int(None, job.operation_id),
                        "machine_pallet_id": job.machine_pallet_numeric_id,
                        "ignore_until": ignore_until,
                        "reason": reason,
                        "decision_id": decision_id,
                    },
                )
                return
            except SQLAlchemyError as exc:
                logger.error("Failed to insert AutopilotJobIgnore", exc_info=exc)
        logger.info(
            "Falling back to in-memory ignore list; this is not persisted",
            extra={"work_order": job.work_order, "part_id": job.part_id, "operation_id": job.operation_id},
        )

    def list_active_ignores(self) -> List[dict]:
        if self._session:
            try:
                result = self._session.execute(
                    text(
                        """
                        SELECT WorkOrder, PartId, OperationId, MachinePalletId, IgnoreUntilUtc
                        FROM fastems1.AutopilotJobIgnore
                        WHERE IgnoreUntilUtc > SYSUTCDATETIME()
                        """
                    )
                )
                ignores = []
                for row in result:
                    mapping = dict(row._mapping)  # type: ignore[attr-defined]
                    mapping["PartId"] = str(mapping.get("PartId")) if mapping.get("PartId") is not None else None
                    mapping["OperationId"] = str(mapping.get("OperationId")) if mapping.get("OperationId") is not None else None
                    mapping["MachinePalletId"] = _normalize_db_pallet_id(mapping.get("MachinePalletId"))
                    ignores.append(mapping)
                return ignores
            except SQLAlchemyError as exc:
                logger.error("Failed to list AutopilotJobIgnore", exc_info=exc)
        return []

    def upsert_machine_status(self, machine_id: str, is_available: bool, status: str, reason: Optional[str]) -> None:
        if not self._session:
            _memory_machine_status[machine_id] = {
                "MachineId": machine_id,
                "IsAvailable": "1" if is_available else "0",
                "Status": status,
                "Reason": reason or "",
            }
            return

        try:
            result = self._session.execute(
                text(
                    """
                    UPDATE fastems1.AutopilotMachineStatus
                    SET IsAvailable = :is_available,
                        Status = :status,
                        Reason = :reason,
                        TsUpdatedUtc = SYSUTCDATETIME()
                    WHERE MachineId = :machine_id
                    """
                ),
                {
                    "machine_id": machine_id,
                    "is_available": 1 if is_available else 0,
                    "status": status,
                    "reason": reason,
                },
            )
            if result.rowcount == 0:
                self._session.execute(
                    text(
                        """
                        INSERT INTO fastems1.AutopilotMachineStatus
                        (MachineId, IsAvailable, Status, Reason, TsUpdatedUtc)
                        VALUES (:machine_id, :is_available, :status, :reason, SYSUTCDATETIME())
                        """
                    ),
                    {
                        "machine_id": machine_id,
                        "is_available": 1 if is_available else 0,
                        "status": status,
                        "reason": reason,
                    },
                )
        except SQLAlchemyError as exc:
            logger.error("Failed to upsert Autopilot machine status", exc_info=exc)

    def list_machine_status(self) -> Dict[str, dict]:
        if not self._session:
            return _memory_machine_status
        try:
            result = self._session.execute(
                text(
                    """
                    SELECT MachineId, IsAvailable, Status, Reason
                    FROM fastems1.AutopilotMachineStatus
                    """
                )
            )
            return {row.MachineId: dict(row._mapping) for row in result}  # type: ignore[attr-defined]
        except SQLAlchemyError as exc:
            logger.error("Failed to fetch machine status", exc_info=exc)
            return {}

    def get_active_shift_window(self, now: Optional[datetime] = None) -> Optional[ShiftWindow]:
        if not self._session:
            return None
        now = now or datetime.now(timezone.utc)
        local_tz = ZoneInfo(settings.fastems1_default_shift_timezone)
        local_time = now.astimezone(local_tz).time()
        try:
            rows = self._session.execute(
                text(
                    """
                    SELECT
                        ShiftWindowId,
                        Name,
                        StartTime,
                        EndTime,
                        Mode,
                        WeightShortSetup,
                        WeightLongRun,
                        WeightToolPenalty,
                        WeightMaterialPenalty,
                        WeightMachineBalance
                    FROM fastems1.AutopilotShiftWindow
                    ORDER BY ShiftWindowId
                    """
                )
            ).all()
        except SQLAlchemyError as exc:
            logger.error("Failed to load AutopilotShiftWindow", exc_info=exc)
            return None

        def _row_to_window(row) -> ShiftWindow:
            return ShiftWindow(
                shift_window_id=row.ShiftWindowId,
                name=row.Name,
                start_time=row.StartTime,
                end_time=row.EndTime,
                mode=row.Mode,
                weight_short_setup=float(row.WeightShortSetup or 1),
                weight_long_run=float(row.WeightLongRun or 1),
                weight_tool_penalty=float(row.WeightToolPenalty or 1),
                weight_material_penalty=float(row.WeightMaterialPenalty or 1),
                weight_machine_balance=float(row.WeightMachineBalance or 1),
            )

        for row in rows:
            window = _row_to_window(row)
            if _is_time_in_window(local_time, window.start_time, window.end_time):
                return window
        if rows:
            return _row_to_window(rows[0])
        return None

    def create_setup_session(
        self,
        machine_id: str,
        machine_pallet_id: Optional[str],
        work_order: Optional[str],
        part_id: Optional[str],
        operation_id: Optional[str],
        setup_type: Optional[str],
        decision_id: Optional[int],
    ) -> Optional[int]:
        if not self._session:
            return None
        try:
            result = self._session.execute(
                text(
                    """
                    INSERT INTO fastems1.AutopilotSetupSession
                    (
                        TsStartUtc,
                        MachineId,
                        MachinePalletId,
                        WorkOrder,
                        PartId,
                        OperationId,
                        SetupType,
                        DecisionId
                    )
                    OUTPUT Inserted.SetupId
                    VALUES
                    (
                        SYSUTCDATETIME(),
                        :machine_id,
                        :machine_pallet_id,
                        :work_order,
                        :part_id,
                        :operation_id,
                        :setup_type,
                        :decision_id
                    )
                    """
                ),
                {
                    "machine_id": machine_id,
                    "machine_pallet_id": machine_pallet_id,
                    "work_order": work_order,
                    "part_id": part_id,
                    "operation_id": operation_id,
                    "setup_type": setup_type,
                    "decision_id": decision_id,
                },
            )
            return result.scalar_one()
        except SQLAlchemyError as exc:
            logger.error("Failed to insert AutopilotSetupSession", exc_info=exc)
            return None

    def complete_setup_session(self, setup_id: int) -> bool:
        if not self._session:
            return False
        try:
            result = self._session.execute(
                text(
                    """
                    UPDATE fastems1.AutopilotSetupSession
                    SET TsEndUtc = COALESCE(TsEndUtc, SYSUTCDATETIME())
                    WHERE SetupId = :setup_id
                    """
                ),
                {"setup_id": setup_id},
            )
            return result.rowcount > 0
        except SQLAlchemyError as exc:
            logger.error("Failed to complete AutopilotSetupSession", exc_info=exc)
            return False

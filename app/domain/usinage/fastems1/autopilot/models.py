"""
Domain models for the Fastems1 Autopilot planner.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from typing import List, Optional, Sequence


@dataclass(slots=True)
class WorkOrderOperation:
    """Single operation eligible for planning."""

    work_order: str
    part_id: str
    operation_id: str
    raw_part_id: Optional[str] = None
    operation_code: Optional[str] = None
    description: Optional[str] = None
    machine_type: Optional[str] = None
    required_quantity: int = 0
    completed_quantity: int = 0
    estimated_cycle_minutes: float = 0.0
    due_date: Optional[date] = None
    priority: int = 0
    allowed_machines: Optional[List[str]] = None
    line_number: Optional[int] = None
    part_numeric_id: Optional[int] = None
    operation_numeric_id: Optional[int] = None
    program_name: Optional[str] = None

    @property
    def remaining_quantity(self) -> int:
        return max(self.required_quantity - self.completed_quantity, 0)


@dataclass(slots=True)
class ToolRequirement:
    tool_id: str
    description: Optional[str] = None
    usage_time_seconds: Optional[float] = None


@dataclass(slots=True)
class ToolState:
    tool_id: str
    is_present: bool
    remaining_life_seconds: Optional[int] = None
    usage_status: Optional[str] = None


@dataclass(slots=True)
class FixtureState:
    fixture_code: str
    description: Optional[str]
    storage_location: Optional[str]
    quantity_total: Optional[int] = None
    quantity_in_use: Optional[int] = None

    @property
    def quantity_available(self) -> Optional[int]:
        if self.quantity_total is None:
            return None
        in_use = self.quantity_in_use or 0
        return max(self.quantity_total - in_use, 0)


@dataclass(slots=True)
class MachinePalletState:
    pallet_id: str
    numeric_id: Optional[int] = None
    pallet_number: Optional[str] = None
    fixture_code: Optional[str] = None
    machine_id: Optional[str] = None
    is_active: bool = False
    operation_in_progress: Optional[str] = None
    plaque_model: Optional[str] = None


@dataclass(slots=True)
class MaterialPalletState:
    pallet_id: str
    content_type: Optional[str] = None
    work_order: Optional[str] = None
    part_id: Optional[str] = None
    quantity_available: Optional[int] = None
    location: Optional[str] = None


@dataclass(slots=True)
class ScoreBreakdown:
    total: float = 0.0
    tool_penalty: float = 0.0
    setup_penalty: float = 0.0
    material_penalty: float = 0.0
    balance_penalty: float = 0.0


@dataclass(slots=True)
class ActionPlanStep:
    step_type: str
    description: Optional[str] = None
    metadata: Optional[dict] = None


@dataclass(slots=True)
class ActionPlan:
    steps: List[ActionPlanStep] = field(default_factory=list)
    fixture_hardware_list: List[dict] = field(default_factory=list)


@dataclass(slots=True)
class PlanCandidate:
    work_order: str
    part_id: str
    operation_id: str
    machine_id: str
    machine_pallet_id: Optional[str]
    material_pallet_id: Optional[str]
    estimated_setup_minutes: float
    estimated_cycle_minutes: float
    sequence_index: int
    score: ScoreBreakdown = field(default_factory=ScoreBreakdown)
    part_numeric_id: Optional[int] = None
    operation_numeric_id: Optional[int] = None
    machine_pallet_numeric_id: Optional[int] = None
    material_pallet_numeric_id: Optional[int] = None
    program_name: Optional[str] = None


@dataclass(slots=True)
class SuggestionResult:
    decision_id: Optional[int]
    machine_id: str
    work_order: str
    part_id: str
    operation_id: str
    machine_pallet_id: Optional[str]
    material_pallet_id: Optional[str]
    estimated_setup_minutes: float
    estimated_cycle_minutes: float
    score: ScoreBreakdown
    action_plan: ActionPlan
    alternatives: Sequence[PlanCandidate] = ()
    details: Optional[dict] = None


@dataclass(slots=True)
class ShiftWindow:
    shift_window_id: int
    name: str
    start_time: time
    end_time: time
    mode: str
    weight_short_setup: float
    weight_long_run: float
    weight_tool_penalty: float
    weight_material_penalty: float
    weight_machine_balance: float

"""
Pydantic schemas for Fastems1 Autopilot endpoints.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class PlanRefreshResponse(BaseModel):
    plan_batch_id: str
    machines: List[str]
    planned_jobs: int


class ActionPlanStepModel(BaseModel):
    step_type: str
    description: Optional[str] = None
    metadata: Optional[dict] = None


class ActionPlanModel(BaseModel):
    steps: List[ActionPlanStepModel]
    fixture_hardware_list: List[dict] = Field(default_factory=list)


class SuggestionResponse(BaseModel):
    decision_id: Optional[int]
    machine_id: str
    work_order: str
    part_id: str
    operation_id: str
    machine_pallet_id: Optional[str]
    material_pallet_id: Optional[str]
    estimated_setup_minutes: float
    estimated_cycle_minutes: float
    score_total: float
    score_breakdown: dict
    action_plan: ActionPlanModel
    alternatives: List[dict] = Field(default_factory=list)
    details: Optional[dict] = None


class NextRequest(BaseModel):
    max_alternatives: int = Field(default=0, ge=0, le=5)
    details: bool = Field(default=False, description="Include diagnostic details in the response")


class RefuseRequest(BaseModel):
    planned_job_id: int
    decision_id: Optional[int] = None
    reason: Optional[str] = None


class MachineStatusRequest(BaseModel):
    machine_id: str
    is_available: bool
    status: str = Field(default="available")
    reason: Optional[str] = None


class SetupStartRequest(BaseModel):
    machine_id: str
    machine_pallet_id: Optional[str] = None
    work_order: Optional[str] = None
    part_id: Optional[str] = None
    operation_id: Optional[str] = None
    setup_type: Optional[str] = Field(default="auto_detected")
    decision_id: Optional[int] = None


class SetupStartResponse(BaseModel):
    setup_id: Optional[int]


class SetupEndResponse(BaseModel):
    setup_id: int
    completed: bool

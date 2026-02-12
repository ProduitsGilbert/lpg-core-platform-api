from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


QuoteStatus = Literal["draft", "in_review", "sent", "won", "lost", "cancelled"]
StepSource = Literal["llm", "rules", "user"]


class QuoteCreateRequest(BaseModel):
    customer_id: UUID
    quote_number: Optional[str] = Field(default=None, max_length=50)
    status: QuoteStatus = "draft"
    currency: str = Field(default="CAD", max_length=10)
    due_date: Optional[date] = None
    notes: Optional[str] = None


class QuoteUpdateRequest(BaseModel):
    quote_number: Optional[str] = Field(default=None, max_length=50)
    customer_id: Optional[UUID] = None
    status: Optional[QuoteStatus] = None
    currency: Optional[str] = Field(default=None, max_length=10)
    due_date: Optional[date] = None
    notes: Optional[str] = None


class QuoteStatusUpdateRequest(BaseModel):
    status: Literal["won", "lost", "sent", "cancelled", "in_review", "draft"]
    loss_reason_code: Optional[str] = Field(default=None, max_length=50)
    loss_reason_note: Optional[str] = None


class QuoteSummary(BaseModel):
    quote_id: UUID
    quote_number: Optional[str] = None
    customer_id: UUID
    status: QuoteStatus
    currency: str
    due_date: Optional[date] = None
    sent_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    loss_reason_code: Optional[str] = None
    loss_reason_note: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class RoutingCreateRequest(BaseModel):
    scenario_name: str = Field(min_length=1, max_length=200)
    created_by: Optional[str] = Field(default=None, max_length=200)
    selected: bool = False
    rationale: Optional[str] = None


class RoutingUpdateRequest(BaseModel):
    scenario_name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    created_by: Optional[str] = Field(default=None, max_length=200)
    selected: Optional[bool] = None
    rationale: Optional[str] = None


class RoutingResponse(BaseModel):
    routing_id: UUID
    part_id: UUID
    scenario_name: str
    created_by: Optional[str] = None
    selected: bool
    rationale: Optional[str] = None
    created_at: datetime


class RoutingStepCreateRequest(BaseModel):
    step_no: Optional[int] = Field(default=None, ge=1)
    operation_id: UUID
    machine_group_id: Optional[str] = Field(default=None, max_length=100)
    description: Optional[str] = None
    setup_time_min: Decimal = Field(default=Decimal("0"), ge=0)
    cycle_time_min: Decimal = Field(default=Decimal("0"), ge=0)
    handling_time_min: Decimal = Field(default=Decimal("0"), ge=0)
    inspection_time_min: Decimal = Field(default=Decimal("0"), ge=0)
    qty_basis: int = Field(default=1, ge=1)
    estimator_note: Optional[str] = None
    time_confidence: Optional[Decimal] = Field(default=None, ge=0, le=1)
    source: StepSource = "llm"


class RoutingStepUpdateRequest(BaseModel):
    machine_group_id: Optional[str] = Field(default=None, max_length=100)
    description: Optional[str] = None
    setup_time_min: Optional[Decimal] = Field(default=None, ge=0)
    cycle_time_min: Optional[Decimal] = Field(default=None, ge=0)
    handling_time_min: Optional[Decimal] = Field(default=None, ge=0)
    inspection_time_min: Optional[Decimal] = Field(default=None, ge=0)
    qty_basis: Optional[int] = Field(default=None, ge=1)
    estimator_note: Optional[str] = None
    time_confidence: Optional[Decimal] = Field(default=None, ge=0, le=1)
    source: Optional[StepSource] = None
    user_override: Optional[bool] = None


class RoutingStepResponse(BaseModel):
    step_id: UUID
    routing_id: UUID
    step_no: int
    operation_id: UUID
    machine_group_id: Optional[str] = None
    description: Optional[str] = None
    setup_time_min: Decimal
    cycle_time_min: Decimal
    handling_time_min: Decimal
    inspection_time_min: Decimal
    qty_basis: int
    user_override: bool
    estimator_note: Optional[str] = None
    time_confidence: Optional[Decimal] = None
    source: StepSource


class QuoteAnalysisStartResponse(BaseModel):
    job_id: UUID
    quote_id: UUID
    status: str


class JobStatusResponse(BaseModel):
    job_id: UUID
    status: str
    stage: str
    progress: float = Field(ge=0, le=1)
    started_at: datetime
    ended_at: Optional[datetime] = None
    error_text: Optional[str] = None
    output_json: Optional[str] = None

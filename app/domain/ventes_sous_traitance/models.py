from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal, Optional
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


class CustomerSummary(BaseModel):
    customer_id: UUID
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    ship_to_address: Optional[str] = None
    contact_name: Optional[str] = None
    global_quote_comment: Optional[str] = None
    created_at: datetime


class CustomerCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    email: Optional[str] = Field(default=None, max_length=200)
    phone: Optional[str] = Field(default=None, max_length=50)
    ship_to_address: Optional[str] = None
    contact_name: Optional[str] = Field(default=None, max_length=200)
    global_quote_comment: Optional[str] = None


class CustomerUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    email: Optional[str] = Field(default=None, max_length=200)
    phone: Optional[str] = Field(default=None, max_length=50)
    ship_to_address: Optional[str] = None
    contact_name: Optional[str] = Field(default=None, max_length=200)
    global_quote_comment: Optional[str] = None


class MachineGroupSummary(BaseModel):
    machine_group_id: str
    name: str
    process_families_json: Optional[str] = None
    config_json: Optional[str] = None
    updated_at: datetime


class MachineGroupCreateRequest(BaseModel):
    machine_group_id: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=200)
    process_families_json: Optional[str] = None
    config_json: Optional[str] = None


class MachineGroupUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    process_families_json: Optional[str] = None
    config_json: Optional[str] = None


class MachineCapabilityInput(BaseModel):
    capability_code: str = Field(min_length=1, max_length=100)
    capability_value: Optional[str] = Field(default=None, max_length=200)
    numeric_value: Optional[Decimal] = None
    bool_value: Optional[bool] = None
    unit: Optional[str] = Field(default=None, max_length=20)
    notes: Optional[str] = None


class MachineCapabilityResponse(BaseModel):
    capability_id: UUID
    machine_id: UUID
    capability_code: str
    capability_value: Optional[str] = None
    numeric_value: Optional[Decimal] = None
    bool_value: Optional[bool] = None
    unit: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class MachineCapabilityOption(BaseModel):
    capability_code: str
    capability_value: Optional[str] = None
    unit: Optional[str] = None
    usage_count: int = 0


class MachineCapabilityOptionCreateRequest(BaseModel):
    capability_code: str = Field(min_length=1, max_length=100)
    capability_value: Optional[str] = Field(default=None, max_length=200)
    unit: Optional[str] = Field(default=None, max_length=20)
    is_active: bool = True
    notes: Optional[str] = None


class MachineCapabilityOptionUpdateRequest(BaseModel):
    capability_code: Optional[str] = Field(default=None, min_length=1, max_length=100)
    capability_value: Optional[str] = Field(default=None, max_length=200)
    unit: Optional[str] = Field(default=None, max_length=20)
    is_active: Optional[bool] = None
    notes: Optional[str] = None


class MachineCapabilityOptionEntry(BaseModel):
    option_id: UUID
    capability_code: str
    capability_value: Optional[str] = None
    unit: Optional[str] = None
    is_active: bool
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class MachineCapabilityCatalogItem(BaseModel):
    capability_code: str
    recommended_input_type: str
    suggested_unit: Optional[str] = None
    usage_count: int = 0
    example_values: list[str] = Field(default_factory=list)


class MachineCreateRequest(BaseModel):
    machine_code: str = Field(min_length=1, max_length=100)
    machine_name: str = Field(min_length=1, max_length=200)
    machine_group_id: Optional[str] = Field(default=None, max_length=100)
    is_active: bool = True
    default_setup_time_min: Decimal = Field(default=Decimal("0"), ge=0)
    default_runtime_min: Decimal = Field(default=Decimal("0"), ge=0)
    envelope_x_mm: Optional[Decimal] = Field(default=None, ge=0)
    envelope_y_mm: Optional[Decimal] = Field(default=None, ge=0)
    envelope_z_mm: Optional[Decimal] = Field(default=None, ge=0)
    max_part_weight_kg: Optional[Decimal] = Field(default=None, ge=0)
    notes: Optional[str] = None
    capabilities: list[MachineCapabilityInput] = Field(default_factory=list)


class MachineUpdateRequest(BaseModel):
    machine_name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    machine_group_id: Optional[str] = Field(default=None, max_length=100)
    is_active: Optional[bool] = None
    default_setup_time_min: Optional[Decimal] = Field(default=None, ge=0)
    default_runtime_min: Optional[Decimal] = Field(default=None, ge=0)
    envelope_x_mm: Optional[Decimal] = Field(default=None, ge=0)
    envelope_y_mm: Optional[Decimal] = Field(default=None, ge=0)
    envelope_z_mm: Optional[Decimal] = Field(default=None, ge=0)
    max_part_weight_kg: Optional[Decimal] = Field(default=None, ge=0)
    notes: Optional[str] = None
    capabilities: Optional[list[MachineCapabilityInput]] = None


class MachineResponse(BaseModel):
    machine_id: UUID
    machine_code: str
    machine_name: str
    machine_group_id: Optional[str] = None
    is_active: bool
    default_setup_time_min: Decimal
    default_runtime_min: Decimal
    envelope_x_mm: Optional[Decimal] = None
    envelope_y_mm: Optional[Decimal] = None
    envelope_z_mm: Optional[Decimal] = None
    max_part_weight_kg: Optional[Decimal] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    capabilities: list[MachineCapabilityResponse] = Field(default_factory=list)


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


class PartFeatureCreateRequest(BaseModel):
    source: Literal["llm", "rules", "user"] = "user"
    source_run_id: Optional[UUID] = None
    feature_ref: Optional[str] = Field(default=None, max_length=50)
    feature_type: str = Field(min_length=1, max_length=100)
    description: Optional[str] = None
    quantity: int = Field(default=1, ge=1)
    width_mm: Optional[Decimal] = Field(default=None, ge=0)
    length_mm: Optional[Decimal] = Field(default=None, ge=0)
    depth_mm: Optional[Decimal] = Field(default=None, ge=0)
    diameter_mm: Optional[Decimal] = Field(default=None, ge=0)
    thread_spec: Optional[str] = Field(default=None, max_length=50)
    tolerance_note: Optional[str] = Field(default=None, max_length=100)
    surface_finish_ra_um: Optional[Decimal] = Field(default=None, ge=0)
    location_note: Optional[str] = Field(default=None, max_length=200)
    complexity_factors: list[str] = Field(default_factory=list)
    estimated_operation_time_min: Optional[Decimal] = Field(default=None, ge=0)
    is_user_override: bool = True


class PartFeatureUpdateRequest(BaseModel):
    source: Optional[Literal["llm", "rules", "user"]] = None
    source_run_id: Optional[UUID] = None
    feature_ref: Optional[str] = Field(default=None, max_length=50)
    feature_type: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = None
    quantity: Optional[int] = Field(default=None, ge=1)
    width_mm: Optional[Decimal] = Field(default=None, ge=0)
    length_mm: Optional[Decimal] = Field(default=None, ge=0)
    depth_mm: Optional[Decimal] = Field(default=None, ge=0)
    diameter_mm: Optional[Decimal] = Field(default=None, ge=0)
    thread_spec: Optional[str] = Field(default=None, max_length=50)
    tolerance_note: Optional[str] = Field(default=None, max_length=100)
    surface_finish_ra_um: Optional[Decimal] = Field(default=None, ge=0)
    location_note: Optional[str] = Field(default=None, max_length=200)
    complexity_factors: Optional[list[str]] = None
    estimated_operation_time_min: Optional[Decimal] = Field(default=None, ge=0)
    is_user_override: Optional[bool] = None


class PartFeatureResponse(BaseModel):
    feature_id: UUID
    part_id: UUID
    source: Literal["llm", "rules", "user"]
    source_run_id: Optional[UUID] = None
    feature_ref: Optional[str] = None
    feature_type: str
    description: Optional[str] = None
    quantity: int
    width_mm: Optional[Decimal] = None
    length_mm: Optional[Decimal] = None
    depth_mm: Optional[Decimal] = None
    diameter_mm: Optional[Decimal] = None
    thread_spec: Optional[str] = None
    tolerance_note: Optional[str] = None
    surface_finish_ra_um: Optional[Decimal] = None
    location_note: Optional[str] = None
    complexity_factors: list[str] = Field(default_factory=list)
    estimated_operation_time_min: Optional[Decimal] = None
    is_user_override: bool
    created_at: datetime
    updated_at: datetime


class PartFeatureSetUpsertRequest(BaseModel):
    source: Literal["llm", "rules", "user"] = "user"
    source_run_id: Optional[UUID] = None
    feature_confidence: Optional[Decimal] = Field(default=None, ge=0, le=1)
    part_summary: Optional[dict[str, Any]] = None
    additional_operations: list[str] = Field(default_factory=list)
    general_notes: list[str] = Field(default_factory=list)
    features: list[PartFeatureCreateRequest] = Field(default_factory=list)


class PartFeatureSetResponse(BaseModel):
    feature_set_id: Optional[UUID] = None
    part_id: UUID
    source: Optional[Literal["llm", "rules", "user"]] = None
    source_run_id: Optional[UUID] = None
    feature_confidence: Optional[Decimal] = None
    part_summary: Optional[dict[str, Any]] = None
    additional_operations: list[str] = Field(default_factory=list)
    general_notes: list[str] = Field(default_factory=list)
    features: list[PartFeatureResponse] = Field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


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

from __future__ import annotations

from pydantic import BaseModel, Field


class FutureToolingNeedRow(BaseModel):
    prod_order_no: str | None = None
    no_prod_order: str | None = None
    line_no: int | None = None
    status: str | None = None
    due_date: str | None = None
    routing_no: str | None = None
    routing_item_no: str | None = None
    op_code: str | None = None
    operation_suffix: str | None = None
    nc_program: str | None = None
    part_no: str | None = None
    description: str | None = None
    input_quantity: int = 0
    completed_quantity: int = 0
    remaining_quantity: int = 0
    tool_id: str | None = None
    tool_use_time_seconds: int | None = None
    tool_description: str | None = None
    total_required_use_time_seconds: int | None = None


class FutureToolingToolSummary(BaseModel):
    tool_id: str
    total_required_use_time_seconds: int
    rows_count: int
    program_count: int


class FutureToolingNeedResponse(BaseModel):
    work_center_no: str
    snapshot_date: str
    generated_at: str
    from_cache: bool = False
    source_order_count: int = 0
    unique_program_count: int = 0
    rows_count: int = 0
    tools_summary: list[FutureToolingToolSummary] = Field(default_factory=list)
    rows: list[FutureToolingNeedRow] = Field(default_factory=list)


class ToolingUsageHistoryRow(BaseModel):
    posting_date: str | None = None
    work_center_no: str | None = None
    machine_center: str | None = None
    order_no: str | None = None
    item_no: str | None = None
    operation_no: str | None = None
    operation_suffix: str | None = None
    nc_program: str | None = None
    quantity: float = 0.0
    tool_id: str | None = None
    tool_use_time_seconds: int | None = None
    tool_description: str | None = None
    estimated_total_use_time_seconds: int | None = None


class ToolingUsageHistoryToolSummary(BaseModel):
    tool_id: str
    total_estimated_use_time_seconds: int
    rows_count: int
    unique_program_count: int
    months_active: int


class ToolingUsageHistoryMonthSummary(BaseModel):
    month: str
    source_entries_count: int
    rows_count: int
    quantity_total: float
    estimated_use_time_seconds_total: int


class ToolingUsageHistoryResponse(BaseModel):
    work_center_no: str
    machine_center: str
    start_date: str
    end_date: str
    generated_at: str
    from_cache: bool = False
    source_entry_count: int = 0
    unique_program_count: int = 0
    rows_count: int = 0
    tools_summary: list[ToolingUsageHistoryToolSummary] = Field(default_factory=list)
    monthly_summary: list[ToolingUsageHistoryMonthSummary] = Field(default_factory=list)
    rows: list[ToolingUsageHistoryRow] = Field(default_factory=list)

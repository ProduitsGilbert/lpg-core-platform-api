from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class PlannerDailyCustomerLoad(BaseModel):
    minutes_done: float = Field(ge=0)
    hours_done: float = Field(ge=0)
    minutes_remaining: float = Field(ge=0)
    hours_remaining: float = Field(ge=0)


class PlannerDailyWorkCenter(BaseModel):
    work_center_no: str
    work_center_name: Optional[str] = None
    mo_done: int = Field(ge=0)
    mo_remaining: int = Field(ge=0)


class PlannerDailyReportResponse(BaseModel):
    posting_date: str
    customer_load_gi: PlannerDailyCustomerLoad
    workcenters: List[PlannerDailyWorkCenter]


class PlannerDailyHistoryPoint(BaseModel):
    date: str
    mo_done: int = Field(ge=0)
    mo_remaining: int = Field(ge=0)


class PlannerDailyWorkcenterHistoryResponse(BaseModel):
    work_center_no: str
    work_center_name: Optional[str] = None
    start_date: str
    end_date: str
    days: int = Field(ge=1)
    points: List[PlannerDailyHistoryPoint]


class FastemsPalletUsageBase(BaseModel):
    pallet_number: str
    latest_snapshot_id: Optional[int] = None
    latest_snapshot_time_utc: Optional[datetime] = None
    change_count_24h: int = Field(ge=0)
    change_count_7d: int = Field(ge=0)
    change_count_30d: int = Field(ge=0)
    change_count_90d: int = Field(ge=0)


class Fastems1PalletUsage(FastemsPalletUsageBase):
    route_phase: Optional[str] = None
    phase_name: Optional[str] = None
    command_data: Optional[str] = None


class Fastems2PalletUsage(FastemsPalletUsageBase):
    routing_mode: Optional[str] = None
    stage: Optional[str] = None
    status: Optional[str] = None


class WindchillCreatedDrawingsPerUser(BaseModel):
    count: int = Field(ge=0)
    creation_date: str
    created_by: str


class WindchillModifiedDrawingsPerUser(BaseModel):
    count: int = Field(ge=0)
    last_modified: str
    modified_by: str


class SalesStatsBiggestCustomer(BaseModel):
    customer_no: str
    customer_name: Optional[str] = None
    order_amount: float = Field(ge=0)


class SalesStatsSnapshotResponse(BaseModel):
    snapshot_date: str
    new_orders_count: int = Field(ge=0)
    last_week_orders_amount: float = Field(ge=0)
    total_quotes_count: int = Field(ge=0)
    pending_quotes_amount: float = Field(ge=0)
    biggest_customer_last_month: Optional[SalesStatsBiggestCustomer] = None


class SalesStatsHistoryResponse(BaseModel):
    start_date: str
    end_date: str
    days: int = Field(ge=1)
    points: List[SalesStatsSnapshotResponse]


class JobKpiSnapshotItem(BaseModel):
    job_no: str
    job_name: Optional[str] = None
    job_status: Optional[str] = None
    avancement_bom_percent: float = Field(ge=0)
    division: Optional[str] = None
    region: Optional[str] = None


class JobKpiDailySnapshotResponse(BaseModel):
    snapshot_date: str
    total_jobs: int = Field(ge=0)
    jobs: List[JobKpiSnapshotItem]


class JobKpiSnapshotHistoryPoint(JobKpiSnapshotItem):
    snapshot_date: str


class JobKpiSnapshotHistoryResponse(BaseModel):
    start_date: str
    end_date: str
    days: int = Field(ge=1)
    points: List[JobKpiSnapshotHistoryPoint]


class JobKpiProgressPoint(BaseModel):
    snapshot_date: str
    avancement_bom_percent: float = Field(ge=0)


class JobKpiProgressResponse(BaseModel):
    job_no: str
    job_name: Optional[str] = None
    job_status: Optional[str] = None
    division: Optional[str] = None
    region: Optional[str] = None
    start_date: str
    end_date: str
    days: int = Field(ge=1)
    points: List[JobKpiProgressPoint]


class JobKpiWarmupResponse(BaseModel):
    snapshot_date: str
    refreshed: bool
    total_jobs: int = Field(ge=0)
    duration_seconds: float = Field(ge=0)


class PayablesStageStats(BaseModel):
    invoice_count: int = Field(ge=0)
    total_amount: float = Field(ge=0)


class ContiniaStatusStats(BaseModel):
    status: str
    invoice_count: int = Field(ge=0)
    total_amount: float = Field(ge=0)


class PayablesInvoiceStatsResponse(BaseModel):
    continia: PayablesStageStats
    purchase_invoice: PayablesStageStats
    posted_purchase_order: PayablesStageStats
    continia_statuses: List[ContiniaStatusStats]

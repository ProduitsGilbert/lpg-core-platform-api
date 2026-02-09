from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class CRMAccountSummary(BaseModel):
    account_id: str
    name: str
    account_number: Optional[str] = None
    telephone: Optional[str] = None
    email: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    annual_revenue: Optional[float] = None
    modified_on: Optional[datetime] = None


class CRMAccountsResponse(BaseModel):
    items: List[CRMAccountSummary] = Field(default_factory=list)
    count: int


class CRMContactSummary(BaseModel):
    contact_id: str
    full_name: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    mobile_phone: Optional[str] = None
    business_phone: Optional[str] = None
    parent_customer_id: Optional[str] = None
    parent_customer_name: Optional[str] = None
    modified_on: Optional[datetime] = None


class CRMContactsResponse(BaseModel):
    items: List[CRMContactSummary] = Field(default_factory=list)
    count: int


class CRMSalesStatsResponse(BaseModel):
    as_of: date
    open_opportunities_count: int
    open_pipeline_amount: float
    weighted_pipeline_amount: float
    won_this_month_count: int
    won_this_month_amount: float
    lost_this_month_count: int


class CRMForecastBucket(BaseModel):
    month: str
    open_opportunities_count: int
    weighted_amount: float
    unweighted_amount: float


class CRMSalesForecastResponse(BaseModel):
    as_of: date
    months: int
    buckets: List[CRMForecastBucket] = Field(default_factory=list)


class CRMPipelineOpportunity(BaseModel):
    opportunity_id: str
    name: str
    customer_name: Optional[str] = None
    estimated_close_date: Optional[date] = None
    estimated_value: float
    probability_percent: Optional[float] = None
    weighted_estimated_value: float
    stage: Optional[str] = None
    status: Optional[str] = None
    owner_name: Optional[str] = None


class CRMSalesPipelineResponse(BaseModel):
    as_of: date
    total_open_opportunities: int
    total_pipeline_amount: float
    total_weighted_pipeline_amount: float
    items: List[CRMPipelineOpportunity] = Field(default_factory=list)


class CRMRawCollectionResponse(BaseModel):
    items: List[Dict[str, Any]] = Field(default_factory=list)
    count: int

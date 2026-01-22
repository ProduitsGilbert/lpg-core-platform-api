from __future__ import annotations

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



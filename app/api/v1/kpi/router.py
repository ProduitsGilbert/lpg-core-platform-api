from __future__ import annotations

from typing import Optional

import logfire
from fastapi import APIRouter, Depends, Query, status

from app.domain.kpi.models import PlannerDailyReportResponse, PlannerDailyWorkcenterHistoryResponse
from app.domain.kpi.planner_daily_report_service import (
    PlannerDailyReportService,
    parse_report_date,
)
from app.errors import ValidationException

router = APIRouter(prefix="/kpi", tags=["KPI"])


def get_planner_daily_report_service() -> PlannerDailyReportService:
    return PlannerDailyReportService()


@router.get(
    "/planning/daily-report",
    response_model=PlannerDailyReportResponse,
    responses={
        status.HTTP_200_OK: {"description": "Planner daily report retrieved successfully"},
        status.HTTP_422_UNPROCESSABLE_ENTITY: {"description": "Invalid report date"},
        status.HTTP_502_BAD_GATEWAY: {"description": "Failed to reach Business Central"},
        status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Business Central unavailable"},
    },
    summary="Planner daily report",
    description=(
        "Return the planning department daily report with MO done/remaining per work center "
        "and factory-wide GI###### load metrics."
    ),
)
async def get_planner_daily_report(
    date: str = Query(
        default="yesterday",
        description="Posting date (YYYY-MM-DD) or 'yesterday' for last business day.",
    ),
    work_center_no: Optional[str] = Query(
        default=None,
        description="Optional Work Center No to filter accomplished/future data.",
    ),
    tasklist_filter: Optional[str] = Query(
        default=None,
        description="Optional extra OData filter to apply on WorkCenterTaskList.",
    ),
    service: PlannerDailyReportService = Depends(get_planner_daily_report_service),
) -> PlannerDailyReportResponse:
    try:
        posting_date = parse_report_date(date)
    except ValueError as exc:
        raise ValidationException(str(exc), field="date") from exc

    with logfire.span(
        "kpi.planning.daily_report",
        posting_date=posting_date.isoformat(),
        has_tasklist_filter=bool(tasklist_filter),
    ):
        return await service.generate_report(
            posting_date=posting_date,
            tasklist_filter=tasklist_filter,
            work_center_no=work_center_no,
        )


@router.get(
    "/planning/daily-report/history",
    response_model=PlannerDailyWorkcenterHistoryResponse,
    responses={
        status.HTTP_200_OK: {"description": "Planner daily report history retrieved successfully"},
        status.HTTP_422_UNPROCESSABLE_ENTITY: {"description": "Invalid input"},
        status.HTTP_502_BAD_GATEWAY: {"description": "Failed to reach Business Central"},
        status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Business Central unavailable"},
    },
    summary="Planner daily report history",
    description=(
        "Return per-business-day history of MO done/remaining for a work center over the past N days."
    ),
)
async def get_planner_daily_report_history(
    date: str = Query(
        default="yesterday",
        description="End date (YYYY-MM-DD) or 'yesterday' for last business day.",
    ),
    days: int = Query(
        default=7,
        ge=1,
        le=120,
        description="Number of calendar days to look back (week=7, month≈30).",
    ),
    work_center_no: str = Query(
        ...,
        description="Work Center No to filter the history.",
        min_length=1,
    ),
    tasklist_filter: Optional[str] = Query(
        default=None,
        description="Optional extra OData filter to apply on WorkCenterTaskList.",
    ),
    service: PlannerDailyReportService = Depends(get_planner_daily_report_service),
) -> PlannerDailyWorkcenterHistoryResponse:
    try:
        posting_date = parse_report_date(date)
    except ValueError as exc:
        raise ValidationException(str(exc), field="date") from exc

    with logfire.span(
        "kpi.planning.daily_report_history",
        posting_date=posting_date.isoformat(),
        days=days,
        work_center_no=work_center_no,
    ):
        try:
            return await service.generate_workcenter_history(
                posting_date=posting_date,
                days=days,
                work_center_no=work_center_no,
                tasklist_filter=tasklist_filter,
            )
        except ValueError as exc:
            raise ValidationException(str(exc), field="days") from exc


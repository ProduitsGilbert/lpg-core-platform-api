from __future__ import annotations

from functools import lru_cache
from typing import Literal, Optional

import logfire
from fastapi import APIRouter, Depends, Path, Query, status

from app.api.v1.models import CollectionResponse, ErrorResponse
from app.domain.kpi.fastems_pallet_usage_service import FastemsPalletUsageService
from app.domain.kpi.models import (
    Fastems1PalletUsage,
    Fastems2PalletUsage,
    JobKpiDailySnapshotResponse,
    JobKpiProgressResponse,
    JobKpiSnapshotHistoryResponse,
    JobKpiWarmupResponse,
    PayablesInvoiceStatsResponse,
    PurchasingStatsResponse,
    SalesStatsHistoryResponse,
    SalesStatsSnapshotResponse,
    PlannerDailyReportResponse,
    PlannerDailyWorkcenterHistoryResponse,
    WindchillCreatedDrawingsPerUser,
    WindchillModifiedDrawingsPerUser,
)
from app.domain.kpi.payables_invoice_stats_service import PayablesInvoiceStatsService
from app.domain.kpi.purchasing_stats_service import (
    PurchasingStatsService,
    parse_purchasing_stats_date,
)
from app.domain.kpi.planner_daily_report_service import (
    PlannerDailyReportService,
    parse_report_date,
)
from app.domain.kpi.jobs_snapshot_service import JobsSnapshotService, parse_jobs_snapshot_date
from app.domain.kpi.sales_stats_service import SalesStatsService, parse_snapshot_date
from app.domain.kpi.windchill_service import WindchillKpiService
from app.errors import DatabaseError, ValidationException

router = APIRouter(prefix="/kpi", tags=["KPI"])


def get_planner_daily_report_service() -> PlannerDailyReportService:
    return PlannerDailyReportService()


def get_sales_stats_service() -> SalesStatsService:
    return SalesStatsService()


def get_jobs_snapshot_service() -> JobsSnapshotService:
    return JobsSnapshotService()


def get_payables_invoice_stats_service() -> PayablesInvoiceStatsService:
    return PayablesInvoiceStatsService()


def get_purchasing_stats_service() -> PurchasingStatsService:
    return PurchasingStatsService()


@lru_cache(maxsize=1)
def _get_fastems_pallet_usage_service() -> FastemsPalletUsageService:
    return FastemsPalletUsageService()


def get_fastems_pallet_usage_service() -> FastemsPalletUsageService:
    service = _get_fastems_pallet_usage_service()
    if not service.is_configured:
        raise DatabaseError("Cedule database not configured")
    return service


@lru_cache(maxsize=1)
def _get_windchill_kpi_service() -> WindchillKpiService:
    return WindchillKpiService()


def get_windchill_kpi_service() -> WindchillKpiService:
    service = _get_windchill_kpi_service()
    if not service.is_configured:
        raise DatabaseError("Windchill database not configured")
    return service


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
        le=90,
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


@router.get(
    "/sales/stats",
    response_model=SalesStatsSnapshotResponse,
    responses={
        status.HTTP_200_OK: {"description": "Sales stats snapshot retrieved successfully"},
        status.HTTP_422_UNPROCESSABLE_ENTITY: {"description": "Invalid snapshot date"},
        status.HTTP_502_BAD_GATEWAY: {"description": "Failed to reach Business Central"},
        status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Business Central unavailable"},
    },
    summary="Sales stats snapshot",
    description=(
        "Return a daily sales KPI snapshot from Business Central SalesQuotes and SalesOrder data. "
        "Includes new orders count, last week order amount, quote totals, pending quote amount, "
        "and biggest customer of last month."
    ),
)
async def get_sales_stats_snapshot(
    date: Optional[str] = Query(
        default=None,
        description="Snapshot date (YYYY-MM-DD) or 'today'. Defaults to latest cached snapshot.",
    ),
    refresh: bool = Query(
        default=False,
        description="Force recomputing the snapshot from Business Central instead of cache.",
    ),
    service: SalesStatsService = Depends(get_sales_stats_service),
) -> SalesStatsSnapshotResponse:
    if date is None and not refresh:
        return await service.get_latest_snapshot()
    try:
        snapshot_date = parse_snapshot_date(date)
    except ValueError as exc:
        raise ValidationException(str(exc), field="date") from exc
    return await service.get_snapshot(snapshot_date=snapshot_date, refresh=refresh)


@router.get(
    "/sales/stats/history",
    response_model=SalesStatsHistoryResponse,
    responses={
        status.HTTP_200_OK: {"description": "Sales stats snapshot history retrieved successfully"},
        status.HTTP_422_UNPROCESSABLE_ENTITY: {"description": "Invalid input"},
    },
    summary="Sales stats snapshot history",
    description=(
        "Return historical sales KPI points from stored daily snapshots over a date window."
    ),
)
async def get_sales_stats_history(
    end_date: str = Query(
        default="today",
        description="End date (YYYY-MM-DD) or 'today'.",
    ),
    days: int = Query(
        default=30,
        ge=1,
        le=365,
        description="Number of calendar days to look back from end_date.",
    ),
    ensure_end_snapshot: bool = Query(
        default=True,
        description="If true, compute and cache end_date snapshot when missing.",
    ),
    service: SalesStatsService = Depends(get_sales_stats_service),
) -> SalesStatsHistoryResponse:
    try:
        parsed_end_date = parse_snapshot_date(end_date)
    except ValueError as exc:
        raise ValidationException(str(exc), field="end_date") from exc
    return await service.get_history(
        end_date=parsed_end_date,
        days=days,
        ensure_end_snapshot=ensure_end_snapshot,
    )


@router.get(
    "/jobs/snapshots",
    response_model=JobKpiDailySnapshotResponse,
    responses={
        status.HTTP_200_OK: {"description": "Jobs KPI snapshot retrieved successfully"},
        status.HTTP_422_UNPROCESSABLE_ENTITY: {"description": "Invalid snapshot date"},
        status.HTTP_502_BAD_GATEWAY: {"description": "Failed to reach Business Central"},
        status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Business Central unavailable"},
    },
    summary="Jobs KPI daily snapshot",
    description=(
        "Return a daily snapshot of jobs progress including AvancementBOM percent "
        "with optional filtering by division and region."
    ),
)
async def get_jobs_snapshot(
    date: Optional[str] = Query(
        default=None,
        description="Snapshot date (YYYY-MM-DD) or 'today'. Defaults to latest cached snapshot.",
    ),
    refresh: bool = Query(
        default=False,
        description="Force recomputing the snapshot from Business Central instead of cache.",
    ),
    division: Optional[str] = Query(default=None, description="Optional division filter (DefaultDimensions)."),
    region: Optional[str] = Query(default=None, description="Optional region filter (DefaultDimensions)."),
    job_no: Optional[str] = Query(default=None, description="Optional exact job number filter."),
    job_status: Optional[str] = Query(default="Open", description="Job status filter. Defaults to Open."),
    service: JobsSnapshotService = Depends(get_jobs_snapshot_service),
) -> JobKpiDailySnapshotResponse:
    if date is None and not refresh:
        return await service.get_latest_snapshot(
            division=division,
            region=region,
            job_no=job_no,
            job_status=job_status,
        )
    try:
        snapshot_date = parse_jobs_snapshot_date(date)
    except ValueError as exc:
        raise ValidationException(str(exc), field="date") from exc
    return await service.get_snapshot(
        snapshot_date=snapshot_date,
        refresh=refresh,
        division=division,
        region=region,
        job_no=job_no,
        job_status=job_status,
    )


@router.get(
    "/jobs/snapshots/history",
    response_model=JobKpiSnapshotHistoryResponse,
    responses={
        status.HTTP_200_OK: {"description": "Jobs KPI snapshot history retrieved successfully"},
        status.HTTP_422_UNPROCESSABLE_ENTITY: {"description": "Invalid input"},
    },
    summary="Jobs KPI snapshot history",
    description=(
        "Return historical jobs KPI snapshot points over a date window to track AvancementBOM evolution."
    ),
)
async def get_jobs_snapshot_history(
    end_date: str = Query(
        default="today",
        description="End date (YYYY-MM-DD) or 'today'.",
    ),
    days: int = Query(
        default=30,
        ge=1,
        le=365,
        description="Number of calendar days to look back from end_date.",
    ),
    ensure_end_snapshot: bool = Query(
        default=True,
        description="If true, compute and cache end_date snapshot when missing.",
    ),
    division: Optional[str] = Query(default=None, description="Optional division filter."),
    region: Optional[str] = Query(default=None, description="Optional region filter."),
    job_no: Optional[str] = Query(default=None, description="Optional exact job number filter."),
    job_status: Optional[str] = Query(default="Open", description="Job status filter. Defaults to Open."),
    service: JobsSnapshotService = Depends(get_jobs_snapshot_service),
) -> JobKpiSnapshotHistoryResponse:
    try:
        parsed_end_date = parse_jobs_snapshot_date(end_date)
    except ValueError as exc:
        raise ValidationException(str(exc), field="end_date") from exc
    return await service.get_history(
        end_date=parsed_end_date,
        days=days,
        ensure_end_snapshot=ensure_end_snapshot,
        division=division,
        region=region,
        job_no=job_no,
        job_status=job_status,
    )


@router.get(
    "/jobs/{job_no}/snapshots/history",
    response_model=JobKpiProgressResponse,
    responses={
        status.HTTP_200_OK: {"description": "Job progress history retrieved successfully"},
        status.HTTP_422_UNPROCESSABLE_ENTITY: {"description": "Invalid input"},
    },
    summary="Specific job progress history",
    description="Return AvancementBOM trend points for a specific job over a date window.",
)
async def get_job_progress_history(
    job_no: str = Path(..., min_length=1, description="Job number (No)."),
    end_date: str = Query(
        default="today",
        description="End date (YYYY-MM-DD) or 'today'.",
    ),
    days: int = Query(
        default=30,
        ge=1,
        le=365,
        description="Number of calendar days to look back from end_date.",
    ),
    ensure_end_snapshot: bool = Query(
        default=True,
        description="If true, ensure end_date snapshot exists for this job only.",
    ),
    division: Optional[str] = Query(default=None, description="Optional division filter."),
    region: Optional[str] = Query(default=None, description="Optional region filter."),
    job_status: Optional[str] = Query(default="Open", description="Job status filter. Defaults to Open."),
    service: JobsSnapshotService = Depends(get_jobs_snapshot_service),
) -> JobKpiProgressResponse:
    try:
        parsed_end_date = parse_jobs_snapshot_date(end_date)
    except ValueError as exc:
        raise ValidationException(str(exc), field="end_date") from exc
    return await service.get_job_progress_history(
        job_no=job_no,
        end_date=parsed_end_date,
        days=days,
        ensure_end_snapshot=ensure_end_snapshot,
        division=division,
        region=region,
        job_status=job_status,
    )


@router.post(
    "/jobs/snapshots/warmup",
    response_model=JobKpiWarmupResponse,
    responses={
        status.HTTP_200_OK: {"description": "Jobs snapshot cache warmup completed"},
        status.HTTP_422_UNPROCESSABLE_ENTITY: {"description": "Invalid snapshot date"},
    },
    summary="Warm up jobs snapshot cache",
    description="Compute and persist jobs snapshot cache for a specific date (defaults to today).",
)
async def warmup_jobs_snapshot_cache(
    date: str = Query(default="today", description="Snapshot date (YYYY-MM-DD) or 'today'."),
    job_status: Optional[str] = Query(default="Open", description="Job status filter. Defaults to Open."),
    service: JobsSnapshotService = Depends(get_jobs_snapshot_service),
) -> JobKpiWarmupResponse:
    try:
        snapshot_date = parse_jobs_snapshot_date(date)
    except ValueError as exc:
        raise ValidationException(str(exc), field="date") from exc
    return await service.warmup_snapshot(snapshot_date=snapshot_date, job_status=job_status)


@router.get(
    "/payables/invoices/stats",
    response_model=PayablesInvoiceStatsResponse,
    responses={
        status.HTTP_200_OK: {"description": "Payables invoice stats retrieved successfully"},
        status.HTTP_502_BAD_GATEWAY: {"description": "Failed to reach Business Central"},
        status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Business Central unavailable"},
    },
    summary="Payables invoice stats",
    description=(
        "Return Accounts Payable invoice KPIs by workflow section: Continia, Purchase Invoice, "
        "and Posted Purchase Order. Includes count and amount totals plus Continia status breakdown."
    ),
)
async def get_payables_invoice_stats(
    refresh: bool = Query(
        default=False,
        description="Force recomputing payables stats from Business Central instead of cache.",
    ),
    service: PayablesInvoiceStatsService = Depends(get_payables_invoice_stats_service),
) -> PayablesInvoiceStatsResponse:
    return await service.get_stats(refresh=refresh)


@router.get(
    "/purchasing/stats",
    response_model=PurchasingStatsResponse,
    responses={
        status.HTTP_200_OK: {"description": "Purchasing stats retrieved successfully"},
        status.HTTP_422_UNPROCESSABLE_ENTITY: {"description": "Invalid input"},
        status.HTTP_502_BAD_GATEWAY: {"description": "Failed to reach Business Central"},
        status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Business Central unavailable"},
    },
    summary="Purchasing KPI stats",
    description=(
        "Return purchasing KPIs over a date window: PO creation timeline and amount totals from "
        "Business Central PurchaseOrderHeaders, plus Cedule order action update counts by action category."
    ),
)
async def get_purchasing_stats(
    end_date: str = Query(
        default="today",
        description="End date (YYYY-MM-DD) or 'today'.",
    ),
    days: int = Query(
        default=90,
        ge=1,
        le=365,
        description="Number of calendar days to look back from end_date.",
    ),
    period: Literal["day", "week", "month"] = Query(
        default="week",
        description="Timeline aggregation period.",
    ),
    refresh: bool = Query(
        default=False,
        description="Force recomputing purchasing stats from Business Central/Cedule instead of cache.",
    ),
    service: PurchasingStatsService = Depends(get_purchasing_stats_service),
) -> PurchasingStatsResponse:
    try:
        parsed_end_date = parse_purchasing_stats_date(end_date)
    except ValueError as exc:
        raise ValidationException(str(exc), field="end_date") from exc

    return await service.get_stats(
        end_date=parsed_end_date,
        days=days,
        period=period,
        refresh=refresh,
    )


@router.get(
    "/fastems1/pallet-usage",
    response_model=CollectionResponse[Fastems1PalletUsage],
    responses={
        status.HTTP_200_OK: {"description": "Fastems1 pallet usage retrieved successfully"},
        status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Cedule database unavailable", "model": ErrorResponse},
    },
    summary="Fastems1 pallet usage stats",
    description=(
        "Return pallet usage statistics for Fastems1 from Cedule.fastems1.vw_MachinePallet_Usage."
    ),
)
async def list_fastems1_pallet_usage(
    service: FastemsPalletUsageService = Depends(get_fastems_pallet_usage_service),
) -> CollectionResponse[Fastems1PalletUsage]:
    usage = service.list_fastems1_usage()
    return CollectionResponse(data=usage)


@router.get(
    "/fastems2/pallet-usage",
    response_model=CollectionResponse[Fastems2PalletUsage],
    responses={
        status.HTTP_200_OK: {"description": "Fastems2 pallet usage retrieved successfully"},
        status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Cedule database unavailable", "model": ErrorResponse},
    },
    summary="Fastems2 pallet usage stats",
    description=(
        "Return pallet usage statistics for Fastems2 from Cedule.fastems2.vw_MachinePallet_Usage."
    ),
)
async def list_fastems2_pallet_usage(
    service: FastemsPalletUsageService = Depends(get_fastems_pallet_usage_service),
) -> CollectionResponse[Fastems2PalletUsage]:
    usage = service.list_fastems2_usage()
    return CollectionResponse(data=usage)


@router.get(
    "/windchill/created-drawings-per-user",
    response_model=CollectionResponse[WindchillCreatedDrawingsPerUser],
    responses={
        status.HTTP_200_OK: {"description": "Windchill created drawings KPI retrieved successfully"},
        status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Windchill database unavailable", "model": ErrorResponse},
    },
    summary="Windchill created drawings per user",
    description=(
        "Return daily count of CADASSEMBLY created drawings by user from Windchill "
        "for the last 365 days."
    ),
)
async def list_windchill_created_drawings_per_user(
    service: WindchillKpiService = Depends(get_windchill_kpi_service),
) -> CollectionResponse[WindchillCreatedDrawingsPerUser]:
    data = service.list_created_drawings_per_user()
    return CollectionResponse(data=data)


@router.get(
    "/windchill/modified-drawings-per-user",
    response_model=CollectionResponse[WindchillModifiedDrawingsPerUser],
    responses={
        status.HTTP_200_OK: {"description": "Windchill modified drawings KPI retrieved successfully"},
        status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Windchill database unavailable", "model": ErrorResponse},
    },
    summary="Windchill modified drawings per user",
    description=(
        "Return daily count of CADASSEMBLY modified drawings by user from Windchill "
        "for the last 365 days."
    ),
)
async def list_windchill_modified_drawings_per_user(
    service: WindchillKpiService = Depends(get_windchill_kpi_service),
) -> CollectionResponse[WindchillModifiedDrawingsPerUser]:
    data = service.list_modified_drawings_per_user()
    return CollectionResponse(data=data)

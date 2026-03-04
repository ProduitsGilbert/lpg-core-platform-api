from __future__ import annotations

from functools import lru_cache

from fastapi import APIRouter, Depends, Query, status

from app.domain.tooling.future_needs_service import FutureToolingNeedService
from app.domain.tooling.models import FutureToolingNeedResponse, ToolingUsageHistoryResponse
from app.domain.tooling.usage_history_service import ToolingUsageHistoryService

router = APIRouter(prefix="/tooling", tags=["Tooling"])


@lru_cache(maxsize=1)
def _get_future_tooling_need_service() -> FutureToolingNeedService:
    return FutureToolingNeedService()


def get_future_tooling_need_service() -> FutureToolingNeedService:
    return _get_future_tooling_need_service()


@lru_cache(maxsize=1)
def _get_tooling_usage_history_service() -> ToolingUsageHistoryService:
    return ToolingUsageHistoryService()


def get_tooling_usage_history_service() -> ToolingUsageHistoryService:
    return _get_tooling_usage_history_service()


@router.get(
    "/future-needs",
    response_model=FutureToolingNeedResponse,
    responses={
        status.HTTP_200_OK: {"description": "Future tooling needs retrieved successfully"},
    },
    summary="Future tooling needs by work center",
    description=(
        "Return coming production orders with NC program tooling requirements and use-time "
        "for a work center. Results are cached daily for fast reads."
    ),
)
async def get_future_tooling_needs(
    work_center_no: str = Query(
        default="40253",
        min_length=1,
        description="Work center number used for unfinished routing lines lookup.",
    ),
    refresh: bool = Query(
        default=False,
        description="Force recomputing today's snapshot from upstream systems.",
    ),
    service: FutureToolingNeedService = Depends(get_future_tooling_need_service),
) -> FutureToolingNeedResponse:
    return await service.get_future_needs(work_center_no=work_center_no, refresh=refresh)


@router.get(
    "/history-usage",
    response_model=ToolingUsageHistoryResponse,
    responses={
        status.HTTP_200_OK: {"description": "Tooling usage history retrieved successfully"},
        status.HTTP_422_UNPROCESSABLE_ENTITY: {"description": "Invalid query parameters"},
    },
    summary="Tooling usage history by work center",
    description=(
        "Return last-N-month tooling usage history for a work center based on Business Central "
        "CapacityLedgerEntries (Production / Work Center), enriched with NC program tool use-time."
    ),
)
async def get_tooling_usage_history(
    work_center_no: str = Query(
        default="40253",
        min_length=1,
        description="Work center number for CapacityLedgerEntries filtering.",
    ),
    machine_center: str = Query(
        default="DMC100",
        min_length=1,
        description="Machine-center label carried in the response (default DMC100).",
    ),
    months: int = Query(
        default=12,
        ge=1,
        le=24,
        description="History window in months. Defaults to 12.",
    ),
    refresh: bool = Query(
        default=False,
        description="Force rebuilding history from upstream systems.",
    ),
    service: ToolingUsageHistoryService = Depends(get_tooling_usage_history_service),
) -> ToolingUsageHistoryResponse:
    return await service.get_usage_history(
        work_center_no=work_center_no,
        machine_center=machine_center,
        months=months,
        refresh=refresh,
    )


@router.get(
    "/fastems2/future-needs",
    response_model=FutureToolingNeedResponse,
    responses={
        status.HTTP_200_OK: {"description": "Fastems2 future tooling needs retrieved successfully"},
    },
    summary="Fastems2 future tooling needs by work center",
    description=(
        "Return coming production orders for a Fastems2 work center with NC program tooling "
        "requirements and use-time. Results are cached daily for fast reads."
    ),
)
async def get_fastems2_future_tooling_needs(
    work_center_no: str = Query(
        default="40279",
        min_length=1,
        description="Fastems2 work center number used for unfinished routing lines lookup.",
    ),
    refresh: bool = Query(
        default=False,
        description="Force recomputing today's snapshot from upstream systems.",
    ),
    service: FutureToolingNeedService = Depends(get_future_tooling_need_service),
) -> FutureToolingNeedResponse:
    return await service.get_future_needs(
        work_center_no=work_center_no,
        refresh=refresh,
        tool_source="fastems2",
    )


@router.get(
    "/fastems2/history-usage",
    response_model=ToolingUsageHistoryResponse,
    responses={
        status.HTTP_200_OK: {"description": "Fastems2 tooling usage history retrieved successfully"},
        status.HTTP_422_UNPROCESSABLE_ENTITY: {"description": "Invalid query parameters"},
    },
    summary="Fastems2 tooling usage history by work center",
    description=(
        "Return last-N-month tooling usage history for a Fastems2 work center based on Business "
        "Central CapacityLedgerEntries, enriched with Fastems2 NC program tool use-time."
    ),
)
async def get_fastems2_tooling_usage_history(
    work_center_no: str = Query(
        default="40279",
        min_length=1,
        description="Fastems2 work center number for CapacityLedgerEntries filtering.",
    ),
    machine_center: str = Query(
        default="FASTEMS2",
        min_length=1,
        description="Machine-center label carried in the response.",
    ),
    months: int = Query(
        default=12,
        ge=1,
        le=24,
        description="History window in months. Defaults to 12.",
    ),
    refresh: bool = Query(
        default=False,
        description="Force rebuilding history from upstream systems.",
    ),
    service: ToolingUsageHistoryService = Depends(get_tooling_usage_history_service),
) -> ToolingUsageHistoryResponse:
    return await service.get_usage_history(
        work_center_no=work_center_no,
        machine_center=machine_center,
        months=months,
        refresh=refresh,
        tool_source="fastems2",
    )

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.domain.crm.models import (
    CRMAccountsResponse,
    CRMContactsResponse,
    CRMSalesForecastResponse,
    CRMSalesPipelineResponse,
    CRMSalesStatsResponse,
)
from app.domain.crm.service import CRMService

router = APIRouter(prefix="/crm", tags=["CRM"])


def get_crm_service() -> CRMService:
    return CRMService()


@router.get(
    "/accounts",
    response_model=CRMAccountsResponse,
    summary="List CRM accounts",
    description="Return account records from Dynamics 365 CRM for internal usage.",
)
async def get_accounts(
    top: int = Query(default=100, ge=1, le=500),
    search: str | None = Query(default=None, min_length=1),
    service: CRMService = Depends(get_crm_service),
) -> CRMAccountsResponse:
    return await service.get_accounts(top=top, search=search)


@router.get(
    "/contacts",
    response_model=CRMContactsResponse,
    summary="List CRM contacts",
    description="Return contact records from Dynamics 365 CRM for internal usage.",
)
async def get_contacts(
    top: int = Query(default=100, ge=1, le=500),
    search: str | None = Query(default=None, min_length=1),
    service: CRMService = Depends(get_crm_service),
) -> CRMContactsResponse:
    return await service.get_contacts(top=top, search=search)


@router.get(
    "/sales/stats",
    response_model=CRMSalesStatsResponse,
    summary="CRM sales KPI snapshot",
    description=(
        "Return a basic sales KPI snapshot built from Dynamics 365 opportunities "
        "(open pipeline, weighted pipeline, won/lost this month)."
    ),
)
async def get_sales_stats(
    service: CRMService = Depends(get_crm_service),
) -> CRMSalesStatsResponse:
    return await service.get_sales_stats()


@router.get(
    "/sales/forecast",
    response_model=CRMSalesForecastResponse,
    summary="CRM sales forecast",
    description="Return weighted and unweighted pipeline forecast buckets by month.",
)
async def get_sales_forecast(
    months: int = Query(default=6, ge=1, le=12),
    service: CRMService = Depends(get_crm_service),
) -> CRMSalesForecastResponse:
    return await service.get_sales_forecast(months=months)


@router.get(
    "/sales/pipeline",
    response_model=CRMSalesPipelineResponse,
    summary="CRM sales pipeline",
    description="Return open opportunities with estimated close date, stage, and weighted value.",
)
async def get_sales_pipeline(
    top: int = Query(default=200, ge=1, le=5000),
    service: CRMService = Depends(get_crm_service),
) -> CRMSalesPipelineResponse:
    return await service.get_sales_pipeline(top=top)

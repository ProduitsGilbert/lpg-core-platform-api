"""
ERP Production endpoints (routing + BOM cost views).
"""

from __future__ import annotations

import logging
import logfire
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.v1.models import SingleResponse, ErrorResponse
from app.domain.erp.production_costing_snapshot_service import ProductionCostingSnapshotService
from app.domain.erp.production_service import ProductionService
from app.domain.erp.models import (
    ProductionItemInfo,
    ProductionBomCostShareResponse,
    ProductionRoutingCostResponse,
    ProductionCostingGroupedItemResponse,
    ProductionCostingScanRequest,
    ProductionCostingScanResponse,
)
from app.errors import ERPError, ERPNotFound

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/production", tags=["ERP - Production"])


def get_production_service() -> ProductionService:
    """Dependency injector for ProductionService."""
    return ProductionService()


def get_production_costing_snapshot_service() -> ProductionCostingSnapshotService:
    """Dependency injector for production costing snapshot service."""
    return ProductionCostingSnapshotService()


def _error_payload(exc: ERPError) -> dict:
    return {
        "error": {
            "code": exc.error_code,
            "message": exc.detail,
            "context": getattr(exc, "context", {}),
        }
    }


@router.get(
    "/items/{item_no}",
    response_model=SingleResponse[ProductionItemInfo],
    responses={
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
        status.HTTP_502_BAD_GATEWAY: {"model": ErrorResponse},
    },
    summary="Get production item info",
    description="Returns item with Routing_No and Production_BOM_No for downstream production calculations.",
)
async def get_production_item(
    item_no: str,
    service: ProductionService = Depends(get_production_service),
) -> SingleResponse[ProductionItemInfo]:
    try:
        with logfire.span("production.get_item", item_no=item_no):
            data = await service.get_item_info(item_no)
        return SingleResponse(data=data)
    except ERPNotFound as exc:
        raise HTTPException(status_code=exc.status_code, detail=_error_payload(exc))
    except ERPError as exc:
        raise HTTPException(status_code=exc.status_code, detail=_error_payload(exc))


@router.get(
    "/items/{item_no}/bom-cost-share",
    response_model=SingleResponse[ProductionBomCostShareResponse],
    responses={
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
        status.HTTP_502_BAD_GATEWAY: {"model": ErrorResponse},
    },
    summary="Get BOM cost share for item",
    description="Uses Business Central BOM_CostShares to detail material and capacity costs for the item.",
)
async def get_bom_cost_share(
    item_no: str,
    service: ProductionService = Depends(get_production_service),
) -> SingleResponse[ProductionBomCostShareResponse]:
    try:
        with logfire.span("production.get_bom_cost_share", item_no=item_no):
            data = await service.get_bom_cost_shares(item_no)
        return SingleResponse(data=data)
    except ERPNotFound as exc:
        raise HTTPException(status_code=exc.status_code, detail=_error_payload(exc))
    except ERPError as exc:
        raise HTTPException(status_code=exc.status_code, detail=_error_payload(exc))


@router.get(
    "/items/{item_no}/routing-costs",
    response_model=SingleResponse[ProductionRoutingCostResponse],
    responses={
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
        status.HTTP_502_BAD_GATEWAY: {"model": ErrorResponse},
    },
    summary="Get routing lines with cost",
    description=(
        "Expands BomRoutingLines for the item's routing, joins Work Centers to derive per-minute rates, "
        "and returns setup/run/total costs per line."
    ),
)
async def get_routing_costs(
    item_no: str,
    service: ProductionService = Depends(get_production_service),
) -> SingleResponse[ProductionRoutingCostResponse]:
    try:
        with logfire.span("production.get_routing_costs", item_no=item_no):
            data = await service.get_routing_costs(item_no)
        return SingleResponse(data=data)
    except ERPNotFound as exc:
        raise HTTPException(status_code=exc.status_code, detail=_error_payload(exc))
    except ERPError as exc:
        raise HTTPException(status_code=exc.status_code, detail=_error_payload(exc))


@router.post(
    "/costing/scans",
    response_model=SingleResponse[ProductionCostingScanResponse],
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {"model": ErrorResponse},
    },
    summary="Run production costing snapshot scan",
    description=(
        "Trigger a scan that snapshots RoutingLines and ProductionBOMLines into Cedule. "
        "Use full_refresh=true for initial load."
    ),
)
async def run_costing_scan(
    payload: ProductionCostingScanRequest,
    service: ProductionCostingSnapshotService = Depends(get_production_costing_snapshot_service),
) -> SingleResponse[ProductionCostingScanResponse]:
    with logfire.span(
        "production.costing.run_scan",
        full_refresh=payload.full_refresh,
    ):
        data = await service.run_scan(full_refresh=payload.full_refresh, trigger_source="manual")
    return SingleResponse(data=data)


@router.get(
    "/costing/items/{item_no}",
    response_model=SingleResponse[ProductionCostingGroupedItemResponse],
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {"model": ErrorResponse},
    },
    summary="Get grouped costing snapshots by base item number",
    description=(
        "Return grouped routing/BOM snapshot data for a base item number (e.g., 0115105). "
        "By default only the latest scan per source number is returned."
    ),
)
async def get_grouped_costing_snapshot(
    item_no: str,
    latest_only: bool = Query(
        default=True,
        description="When true, only the latest scan per source number is returned.",
    ),
    include_lines: bool = Query(
        default=True,
        description="When false, returns only grouped metadata/counts without full raw lines.",
    ),
    service: ProductionCostingSnapshotService = Depends(get_production_costing_snapshot_service),
) -> SingleResponse[ProductionCostingGroupedItemResponse]:
    with logfire.span(
        "production.costing.grouped_item",
        item_no=item_no,
        latest_only=latest_only,
        include_lines=include_lines,
    ):
        data = await service.get_grouped_item_snapshot(
            item_no=item_no,
            latest_only=latest_only,
            include_lines=include_lines,
        )
    return SingleResponse(data=data)

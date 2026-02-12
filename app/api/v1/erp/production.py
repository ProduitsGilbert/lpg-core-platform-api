"""
ERP Production endpoints (routing + BOM cost views).
"""

from __future__ import annotations

import logging
import logfire
from fastapi import APIRouter, Depends, HTTPException, status

from app.api.v1.models import SingleResponse, ErrorResponse
from app.domain.erp.production_service import ProductionService
from app.domain.erp.models import (
    ProductionItemInfo,
    ProductionBomCostShareResponse,
    ProductionRoutingCostResponse,
)
from app.errors import ERPError, ERPNotFound

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/production", tags=["ERP - Production"])


def get_production_service() -> ProductionService:
    """Dependency injector for ProductionService."""
    return ProductionService()


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


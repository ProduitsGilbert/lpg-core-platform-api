"""Toolkit endpoints for Advanced MRP production order monitoring."""

from __future__ import annotations

import io
import logging
from typing import Optional

import httpx
import logfire
from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import StreamingResponse

from app.api.v1.models import CollectionResponse, PaginationMeta
from app.domain.toolkit import AdvancedMRPService
from app.domain.toolkit.models import ProductionOrder

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mrp", tags=["Toolkit - Advanced MRP"])

mrp_service = AdvancedMRPService()


@router.get(
    "/production-orders",
    response_model=CollectionResponse[ProductionOrder],
    responses={
        status.HTTP_200_OK: {"description": "Production orders retrieved successfully"},
        status.HTTP_502_BAD_GATEWAY: {"description": "Failed to reach upstream MRP service"},
    },
    summary="List production orders",
    description="Retrieve Advanced MRP production orders with optional filtering.",
)
async def list_production_orders(
    critical: Optional[bool] = Query(
        default=None,
        description="Forward the critical flag to the upstream API",
    ),
    prod_order_no: Optional[str] = Query(
        default=None,
        description="Case-insensitive substring filter on production order number",
    ),
    job_no: Optional[str] = Query(
        default=None,
        description="Case-insensitive substring filter on job number",
    ),
) -> CollectionResponse[ProductionOrder]:
    """Return production order monitoring data as JSON."""
    try:
        with logfire.span(
            "toolkit.list_production_orders",
            critical=critical,
            prod_order_no=prod_order_no,
            job_no=job_no,
        ):
            result = await mrp_service.fetch_production_orders(
                critical=critical,
                prod_order_no=prod_order_no,
                job_no=job_no,
            )
    except httpx.HTTPStatusError as exc:
        status_code = exc.response.status_code if exc.response else status.HTTP_502_BAD_GATEWAY
        detail = exc.response.text if exc.response else "Upstream MRP service failed"
        logger.error(
            "Advanced MRP upstream call returned HTTP error",
            extra={
                "status_code": status_code,
                "detail": detail[:500],
            },
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "error": {
                    "code": "UPSTREAM_ERROR",
                    "message": "Failed to retrieve production orders from Advanced MRP",
                    "upstream_status": status_code,
                }
            },
        ) from exc
    except httpx.RequestError as exc:
        logger.error("Advanced MRP upstream call failed", extra={"error": str(exc)})
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "error": {
                    "code": "UPSTREAM_UNAVAILABLE",
                    "message": "Advanced MRP service is unreachable",
                }
            },
        ) from exc

    pagination = PaginationMeta(
        pagination={
            "total": result.total_count,
            "count": result.filtered_count,
        }
    )

    return CollectionResponse(data=result.orders, meta=pagination)


@router.get(
    "/production-orders/export",
    responses={
        status.HTTP_200_OK: {
            "description": "Excel export generated successfully",
            "content": {
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": {}
            },
        },
        status.HTTP_502_BAD_GATEWAY: {"description": "Failed to reach upstream MRP service"},
    },
    summary="Export production orders to Excel",
    description="Download an Excel file containing the filtered production orders.",
)
async def export_production_orders(
    critical: Optional[bool] = Query(
        default=None,
        description="Forward the critical flag to the upstream API",
    ),
    prod_order_no: Optional[str] = Query(
        default=None,
        description="Case-insensitive substring filter on production order number",
    ),
    job_no: Optional[str] = Query(
        default=None,
        description="Case-insensitive substring filter on job number",
    ),
) -> StreamingResponse:
    """Return production order monitoring data as an Excel workbook."""
    try:
        with logfire.span(
            "toolkit.export_production_orders",
            critical=critical,
            prod_order_no=prod_order_no,
            job_no=job_no,
        ):
            result = await mrp_service.fetch_production_orders(
                critical=critical,
                prod_order_no=prod_order_no,
                job_no=job_no,
            )
            content = mrp_service.build_excel(result.orders)
    except httpx.HTTPStatusError as exc:
        status_code = exc.response.status_code if exc.response else status.HTTP_502_BAD_GATEWAY
        detail = exc.response.text if exc.response else "Upstream MRP service failed"
        logger.error(
            "Advanced MRP upstream call returned HTTP error during export",
            extra={
                "status_code": status_code,
                "detail": detail[:500],
            },
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "error": {
                    "code": "UPSTREAM_ERROR",
                    "message": "Failed to retrieve production orders from Advanced MRP",
                    "upstream_status": status_code,
                }
            },
        ) from exc
    except httpx.RequestError as exc:
        logger.error("Advanced MRP upstream call failed during export", extra={"error": str(exc)})
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "error": {
                    "code": "UPSTREAM_UNAVAILABLE",
                    "message": "Advanced MRP service is unreachable",
                }
            },
        ) from exc

    filename = "production-orders.xlsx"
    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
        "Cache-Control": "no-cache",
    }

    return StreamingResponse(
        io.BytesIO(content),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )

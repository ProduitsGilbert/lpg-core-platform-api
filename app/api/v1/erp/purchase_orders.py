"""
ERP Purchase Orders endpoints
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, status
from sqlalchemy.orm import Session
import logging
import logfire
from datetime import datetime, date

from app.deps import (
    get_db,
    get_request_context,
    get_idempotency_key,
    RequestContext
)
from app.api.v1.models import SingleResponse, CollectionResponse, ErrorResponse
from app.domain.erp.purchase_order_service import PurchaseOrderService
from app.domain.erp.models import (
    PurchaseOrderResponse,
    PurchaseOrderLineResponse,
    PurchaseOrderReopenRequest,
    PurchaseOrderReopenResponse,
)
from app.domain.purchasing_service import PurchasingService
from app.domain.dtos import (
    POLineDTO,
    UpdatePOLineDateBody,
    UpdatePOLinePriceBody,
    UpdatePOLineQuantityBody,
    UpdatePOLineDateCommand,
    UpdatePOLinePriceCommand,
    UpdatePOLineQuantityCommand,
    CreateReceiptBody,
    CreateReceiptCommand,
    CreateReturnBody,
    CreateReturnCommand,
    ReceiptDTO,
    ReturnDTO
)
from app.errors import BaseAPIException

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/po", tags=["ERP - Purchase Orders"])

# Initialize service
po_service = PurchaseOrderService()
try:
    purchasing_service: Optional[PurchasingService] = PurchasingService()
except ImportError as exc:  # pyodbc not available in test/runtime
    logger.warning("Purchasing service disabled: %s", exc)
    purchasing_service = None


def _get_purchasing_service() -> PurchasingService:
    if purchasing_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Purchasing service is not configured"
        )
    return purchasing_service

@router.get(
    "/{po_id}",
    response_model=SingleResponse[PurchaseOrderResponse],
    responses={
        200: {"description": "Purchase order retrieved successfully"},
        404: {"description": "Purchase order not found", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse}
    },
    summary="Get purchase order by ID",
    description="""
    Retrieves a single purchase order from Business Central by its ID.
    
    Returns:
    - Purchase order header information
    - Vendor details
    - Order totals and status
    - Dates (order, expected receipt, etc.)
    """
)
async def get_purchase_order(
    po_id: str,
    db: Session = Depends(get_db)
) -> SingleResponse[PurchaseOrderResponse]:
    """Get a single purchase order by ID"""
    try:
        with logfire.span(f"get_purchase_order", po_id=po_id):
            order = await po_service.get_purchase_order(po_id)
            
        if not order:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": {
                        "code": "PO_NOT_FOUND",
                        "message": f"Purchase order '{po_id}' not found",
                        "trace_id": getattr(db, 'trace_id', 'unknown')
                    }
                }
            )
        
        return SingleResponse(data=order)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching purchase order {po_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "Failed to retrieve purchase order",
                    "trace_id": getattr(db, 'trace_id', 'unknown')
                }
            }
        )

@router.get(
    "/{po_id}/lines",
    response_model=CollectionResponse[PurchaseOrderLineResponse],
    responses={
        200: {"description": "Purchase order lines retrieved successfully"},
        404: {"description": "Purchase order not found", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse}
    },
    summary="Get purchase order lines",
    description="""
    Retrieves all lines for a specific purchase order.
    
    Returns:
    - Line items with quantities and prices
    - Item descriptions
    - Delivery dates
    - Receipt status per line
    """
)
async def get_purchase_order_lines(
    po_id: str,
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db)
) -> CollectionResponse[PurchaseOrderLineResponse]:
    """Get all lines for a purchase order"""
    try:
        with logfire.span(f"get_purchase_order_lines", po_id=po_id):
            lines = await po_service.get_purchase_order_lines(po_id)
            
        if lines is None:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": {
                        "code": "PO_NOT_FOUND",
                        "message": f"Purchase order '{po_id}' not found",
                        "trace_id": getattr(db, 'trace_id', 'unknown')
                    }
                }
            )
        
        # Simple pagination
        total_items = len(lines)
        total_pages = (total_items + per_page - 1) // per_page
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_lines = lines[start_idx:end_idx]
        
        return CollectionResponse(
            data=paginated_lines,
            meta={
                "timestamp": datetime.utcnow(),
                "version": "1.0",
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total_pages": total_pages,
                    "total_items": total_items
                }
            },
            links={
                "self": f"/api/v1/erp/po/{po_id}/lines?page={page}&per_page={per_page}",
                "next": f"/api/v1/erp/po/{po_id}/lines?page={page+1}&per_page={per_page}" if page < total_pages else None,
                "prev": f"/api/v1/erp/po/{po_id}/lines?page={page-1}&per_page={per_page}" if page > 1 else None,
                "last": f"/api/v1/erp/po/{po_id}/lines?page={total_pages}&per_page={per_page}"
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching purchase order lines for {po_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "Failed to retrieve purchase order lines",
                    "trace_id": getattr(db, 'trace_id', 'unknown')
                }
            }
        )


@router.post(
    "/reopen",
    response_model=SingleResponse[PurchaseOrderReopenResponse],
    status_code=status.HTTP_200_OK,
    summary="Reopen purchase order",
    description="Invoke Business Central action to set a purchase order back to Open so it can be edited"
)
async def reopen_purchase_order_endpoint(
    body: PurchaseOrderReopenRequest,
    ctx: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db)
) -> SingleResponse[PurchaseOrderReopenResponse]:
    try:
        with logfire.span(
            "POST /erp/po/reopen",
            po_id=body.header_no,
            actor=ctx.actor,
        ):
            result = await po_service.reopen_purchase_order(body.header_no)
            return SingleResponse(data=result)
    except BaseAPIException:
        raise
    except Exception as exc:
        logger.error("Error reopening purchase order %s: %s", body.header_no, exc)
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "Failed to reopen purchase order",
                    "trace_id": ctx.trace_id or getattr(db, 'trace_id', 'unknown')
                }
            }
        )


@router.post(
    "/{po_id}/lines/{line_no}/date",
    response_model=POLineDTO,
    status_code=status.HTTP_200_OK,
    summary="Update PO line promise date",
    description="Update the promise date for a purchase order line with business rule validation"
)
async def update_poline_date(
    po_id: str,
    line_no: int,
    body: UpdatePOLineDateBody,
    background_tasks: BackgroundTasks,
    ctx: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db),
    idempotency_key: Optional[str] = Depends(get_idempotency_key)
) -> POLineDTO:
    with logfire.span(
        "POST /purchase-orders/{po_id}/lines/{line_no}/date",
        po_id=po_id,
        line_no=line_no,
        new_date=str(body.new_date)
    ):
        command = UpdatePOLineDateCommand(
            po_id=po_id,
            line_no=line_no,
            new_date=body.new_date,
            reason=body.reason,
            actor=ctx.actor,
            trace_id=ctx.trace_id,
            idempotency_key=idempotency_key or body.idempotency_key
        )

        service = _get_purchasing_service()
        result = await service.update_poline_date(command, db)

        background_tasks.add_task(
            log_date_change,
            po_id=po_id,
            line_no=line_no,
            new_date=body.new_date,
            actor=ctx.actor
        )

        return result


@router.post(
    "/{po_id}/lines/{line_no}/price",
    response_model=POLineDTO,
    status_code=status.HTTP_200_OK,
    summary="Update PO line unit price",
    description="Update the unit price for a purchase order line"
)
async def update_poline_price(
    po_id: str,
    line_no: int,
    body: UpdatePOLinePriceBody,
    background_tasks: BackgroundTasks,
    ctx: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db),
    idempotency_key: Optional[str] = Depends(get_idempotency_key)
) -> POLineDTO:
    with logfire.span(
        "POST /purchase-orders/{po_id}/lines/{line_no}/price",
        po_id=po_id,
        line_no=line_no,
        new_price=str(body.new_price)
    ):
        command = UpdatePOLinePriceCommand(
            po_id=po_id,
            line_no=line_no,
            new_price=body.new_price,
            reason=body.reason,
            actor=ctx.actor,
            trace_id=ctx.trace_id,
            idempotency_key=idempotency_key or body.idempotency_key
        )

        service = _get_purchasing_service()
        result = await service.update_poline_price(command, db)

        background_tasks.add_task(
            analyze_price_change,
            po_id=po_id,
            line_no=line_no,
            new_price=body.new_price,
            reason=body.reason
        )

        return result


@router.post(
    "/{po_id}/lines/{line_no}/quantity",
    response_model=POLineDTO,
    status_code=status.HTTP_200_OK,
    summary="Update PO line quantity",
    description="Update the quantity for a purchase order line"
)
async def update_poline_quantity(
    po_id: str,
    line_no: int,
    body: UpdatePOLineQuantityBody,
    ctx: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db),
    idempotency_key: Optional[str] = Depends(get_idempotency_key)
) -> POLineDTO:
    with logfire.span(
        "POST /purchase-orders/{po_id}/lines/{line_no}/quantity",
        po_id=po_id,
        line_no=line_no,
        new_quantity=str(body.new_quantity)
    ):
        command = UpdatePOLineQuantityCommand(
            po_id=po_id,
            line_no=line_no,
            new_quantity=body.new_quantity,
            reason=body.reason,
            actor=ctx.actor,
            trace_id=ctx.trace_id,
            idempotency_key=idempotency_key or body.idempotency_key
        )

        service = _get_purchasing_service()
        return await service.update_poline_quantity(command, db)


@router.post(
    "/{po_id}/receipts",
    response_model=ReceiptDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Create goods receipt",
    description="Create a new goods receipt for purchase order lines"
)
async def create_receipt(
    po_id: str,
    body: CreateReceiptBody,
    background_tasks: BackgroundTasks,
    ctx: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db),
    idempotency_key: Optional[str] = Depends(get_idempotency_key)
) -> ReceiptDTO:
    with logfire.span(
        "POST /purchase-orders/{po_id}/receipts",
        po_id=po_id,
        line_count=len(body.lines)
    ):
        if body.po_id != po_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Body purchase order does not match path parameter"
            )
        command = CreateReceiptCommand(
            po_id=po_id,
            lines=body.lines,
            receipt_date=body.receipt_date or datetime.utcnow().date(),
            notes=body.notes,
            vendor_shipment_no=body.vendor_shipment_no,
            job_check_delay_seconds=body.job_check_delay_seconds,
            actor=ctx.actor,
            trace_id=ctx.trace_id,
            idempotency_key=idempotency_key or body.idempotency_key
        )

        service = _get_purchasing_service()
        result = await service.create_receipt(command, db)

        background_tasks.add_task(
            update_inventory_levels,
            receipt_id=result.receipt_id,
            po_id=body.po_id
        )

        return result


@router.post(
    "/{po_id}/returns",
    response_model=ReturnDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Create purchase return",
    description="Create a return for previously received goods"
)
async def create_return(
    po_id: str,
    body: CreateReturnBody,
    ctx: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db),
    idempotency_key: Optional[str] = Depends(get_idempotency_key)
) -> ReturnDTO:
    with logfire.span(
        "POST /purchase-orders/{po_id}/returns",
        receipt_id=body.receipt_id,
        line_count=len(body.lines)
    ):
        command = CreateReturnCommand(
            receipt_id=body.receipt_id,
            lines=body.lines,
            reason=body.reason,
            return_date=body.return_date or datetime.utcnow().date(),
            actor=ctx.actor,
            trace_id=ctx.trace_id,
            idempotency_key=idempotency_key or body.idempotency_key,
        )

        service = _get_purchasing_service()
        result = await service.create_return(command, db)

        if result.po_id and result.po_id != po_id:
            logfire.warning(
                "Return order PO mismatch",
                expected_po=po_id,
                actual_po=result.po_id,
                return_id=result.return_id,
            )

        return result


@router.get(
    "/returns/{return_id}",
    response_model=ReturnDTO,
    responses={
        200: {"description": "Purchase return order retrieved successfully"},
        404: {"description": "Return order not found", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse}
    },
    summary="Get purchase return order",
    description="Retrieve a purchase return order with its lines"
)
async def get_return_order(
    return_id: str,
    db: Session = Depends(get_db)
) -> ReturnDTO:
    try:
        with logfire.span("get_return_order", return_id=return_id):
            service = _get_purchasing_service()
            result = await service.get_return_order(return_id)

        if not result:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": {
                        "code": "RETURN_NOT_FOUND",
                        "message": f"Return order '{return_id}' not found",
                        "trace_id": getattr(db, 'trace_id', 'unknown')
                    }
                }
            )

        return result

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Error fetching return order %s: %s", return_id, exc)
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "Failed to retrieve return order",
                    "trace_id": getattr(db, 'trace_id', 'unknown')
                }
            }
        )


async def log_date_change(po_id: str, line_no: int, new_date: date, actor: str):
    """Background logging helper for PO date changes."""
    logfire.info(
        "Date change logged for analytics",
        po_id=po_id,
        line_no=line_no,
        new_date=str(new_date),
        actor=actor
    )


async def analyze_price_change(po_id: str, line_no: int, new_price, reason: str):
    try:
        from app.adapters.ai_client import AIClient
        ai = AIClient()

        analysis = ai.analyze_purchase_order(
            {
                "po_id": po_id,
                "line_no": line_no,
                "new_price": float(new_price),
                "reason": reason
            },
            analysis_type="optimization"
        )

        logfire.info(
            "Price change analysis completed",
            po_id=po_id,
            line_no=line_no,
            risk_score=analysis.get("risk_score"),
            recommendations=analysis.get("recommendations")
        )
    except Exception as e:
        logfire.error(f"Price change analysis failed: {e}")


async def update_inventory_levels(receipt_id: str, po_id: str):
    logfire.info(
        "Inventory update triggered",
        receipt_id=receipt_id,
        po_id=po_id
    )

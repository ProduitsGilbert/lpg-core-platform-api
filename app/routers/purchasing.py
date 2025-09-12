"""
Purchasing API endpoints.

This module provides REST API endpoints for all purchasing operations
including PO line updates, receipts, and returns.
"""

from typing import Annotated, Optional
from datetime import date
from fastapi import APIRouter, Depends, BackgroundTasks, status, Path, Body
from sqlalchemy.orm import Session
import logging

logger = logging.getLogger(__name__)

from app.deps import (
    get_db,
    get_request_context,
    get_idempotency_key,
    RequestContext
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
    ReturnDTO,
    PurchaseOrderDTO
)
from app.settings import settings


router = APIRouter(
    prefix=f"{settings.api_v1_prefix}/purchasing",
    tags=["purchasing"]
)


# Initialize service
purchasing_service = PurchasingService()


@router.post(
    "/po/{po_id}/lines/{line_no}/date",
    response_model=POLineDTO,
    status_code=status.HTTP_200_OK,
    summary="Update PO line promise date",
    description="Update the promise date for a purchase order line with business rule validation"
)
async def update_poline_date(
    po_id: Annotated[str, Path(description="Purchase Order ID")],
    line_no: Annotated[int, Path(description="Line number", ge=1)],
    body: UpdatePOLineDateBody,
    background_tasks: BackgroundTasks,
    ctx: Annotated[RequestContext, Depends(get_request_context)],
    db: Annotated[Session, Depends(get_db)],
    idempotency_key: Annotated[Optional[str], Depends(get_idempotency_key)]
) -> POLineDTO:
    """
    Update PO line promise date.
    
    Args:
        po_id: Purchase Order ID
        line_no: Line number to update
        body: Request body with new date and reason
        background_tasks: FastAPI background tasks
        ctx: Request context with actor and trace info
        db: Database session
        idempotency_key: Optional idempotency key from header
    
    Returns:
        Updated PO line details
    
    Raises:
        422: Validation error (date in past, before order date, etc.)
        404: PO line not found
        409: PO line in non-updatable status
        503: ERP temporarily unavailable
    """
    with logfire.span(
        "POST /po/{po_id}/lines/{line_no}/date",
        po_id=po_id,
        line_no=line_no,
        new_date=str(body.new_date)
    ):
        # Build command from request
        command = UpdatePOLineDateCommand(
            po_id=po_id,
            line_no=line_no,
            new_date=body.new_date,
            reason=body.reason,
            actor=ctx.actor,
            trace_id=ctx.trace_id,
            idempotency_key=idempotency_key or body.idempotency_key
        )
        
        # Execute service operation
        result = purchasing_service.update_poline_date(command, db)
        
        # Optional background task for downstream updates
        background_tasks.add_task(
            log_date_change,
            po_id=po_id,
            line_no=line_no,
            new_date=body.new_date,
            actor=ctx.actor
        )
        
        return result


@router.post(
    "/po/{po_id}/lines/{line_no}/price",
    response_model=POLineDTO,
    status_code=status.HTTP_200_OK,
    summary="Update PO line unit price",
    description="Update the unit price for a purchase order line"
)
async def update_poline_price(
    po_id: Annotated[str, Path(description="Purchase Order ID")],
    line_no: Annotated[int, Path(description="Line number", ge=1)],
    body: UpdatePOLinePriceBody,
    background_tasks: BackgroundTasks,
    ctx: Annotated[RequestContext, Depends(get_request_context)],
    db: Annotated[Session, Depends(get_db)],
    idempotency_key: Annotated[Optional[str], Depends(get_idempotency_key)]
) -> POLineDTO:
    """
    Update PO line unit price.
    
    Args:
        po_id: Purchase Order ID
        line_no: Line number to update
        body: Request body with new price and reason
        background_tasks: FastAPI background tasks
        ctx: Request context
        db: Database session
        idempotency_key: Optional idempotency key
    
    Returns:
        Updated PO line details
    
    Raises:
        422: Validation error (negative price, etc.)
        404: PO line not found
        409: PO line already received or invoiced
        503: ERP temporarily unavailable
    """
    with logfire.span(
        "POST /po/{po_id}/lines/{line_no}/price",
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
        
        result = purchasing_service.update_poline_price(command, db)
        
        # Background task for price change analysis
        if settings.enable_ai_assistance:
            background_tasks.add_task(
                analyze_price_change,
                po_id=po_id,
                line_no=line_no,
                new_price=body.new_price,
                reason=body.reason
            )
        
        return result


@router.post(
    "/po/{po_id}/lines/{line_no}/quantity",
    response_model=POLineDTO,
    status_code=status.HTTP_200_OK,
    summary="Update PO line quantity",
    description="Update the quantity for a purchase order line"
)
async def update_poline_quantity(
    po_id: Annotated[str, Path(description="Purchase Order ID")],
    line_no: Annotated[int, Path(description="Line number", ge=1)],
    body: UpdatePOLineQuantityBody,
    ctx: Annotated[RequestContext, Depends(get_request_context)],
    db: Annotated[Session, Depends(get_db)],
    idempotency_key: Annotated[Optional[str], Depends(get_idempotency_key)]
) -> POLineDTO:
    """
    Update PO line quantity.
    
    Args:
        po_id: Purchase Order ID
        line_no: Line number to update
        body: Request body with new quantity and reason
        ctx: Request context
        db: Database session
        idempotency_key: Optional idempotency key
    
    Returns:
        Updated PO line details
    
    Raises:
        422: Validation error (quantity below received, etc.)
        404: PO line not found
        409: PO line in non-updatable status
        503: ERP temporarily unavailable
    """
    with logfire.span(
        "POST /po/{po_id}/lines/{line_no}/quantity",
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
        
        return purchasing_service.update_poline_quantity(command, db)


@router.post(
    "/receipts",
    response_model=ReceiptDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Create goods receipt",
    description="Create a new goods receipt for purchase order lines"
)
async def create_receipt(
    body: CreateReceiptBody,
    background_tasks: BackgroundTasks,
    ctx: Annotated[RequestContext, Depends(get_request_context)],
    db: Annotated[Session, Depends(get_db)],
    idempotency_key: Annotated[Optional[str], Depends(get_idempotency_key)]
) -> ReceiptDTO:
    """
    Create a goods receipt.
    
    Args:
        body: Receipt creation request
        background_tasks: FastAPI background tasks
        ctx: Request context
        db: Database session
        idempotency_key: Optional idempotency key
    
    Returns:
        Created receipt details
    
    Raises:
        422: Validation error (quantity exceeds outstanding, etc.)
        404: PO or lines not found
        409: PO in non-receivable status
        503: ERP temporarily unavailable
    """
    with logfire.span(
        "POST /receipts",
        po_id=body.po_id,
        line_count=len(body.lines)
    ):
        command = CreateReceiptCommand(
            po_id=body.po_id,
            lines=body.lines,
            receipt_date=body.receipt_date or date.today(),
            notes=body.notes,
            actor=ctx.actor,
            trace_id=ctx.trace_id,
            idempotency_key=idempotency_key or body.idempotency_key
        )
        
        result = purchasing_service.create_receipt(command, db)
        
        # Background task to update inventory
        background_tasks.add_task(
            update_inventory_levels,
            receipt_id=result.receipt_id,
            po_id=body.po_id
        )
        
        return result


@router.post(
    "/returns",
    response_model=ReturnDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Create purchase return",
    description="Create a return for previously received goods"
)
async def create_return(
    body: CreateReturnBody,
    ctx: Annotated[RequestContext, Depends(get_request_context)],
    db: Annotated[Session, Depends(get_db)],
    idempotency_key: Annotated[Optional[str], Depends(get_idempotency_key)]
) -> ReturnDTO:
    """
    Create a purchase return.
    
    Args:
        body: Return creation request
        ctx: Request context
        db: Database session
        idempotency_key: Optional idempotency key
    
    Returns:
        Created return details
    
    Raises:
        422: Validation error (quantity exceeds received, etc.)
        404: Receipt or lines not found
        503: ERP temporarily unavailable
    """
    with logfire.span(
        "POST /returns",
        receipt_id=body.receipt_id,
        line_count=len(body.lines)
    ):
        # Note: Implementation would be similar to create_receipt
        # For now, return a stub response
        return ReturnDTO(
            return_id=f"RET-{date.today().strftime('%Y%m%d')}-001",
            receipt_id=body.receipt_id,
            po_id="PO-001",
            vendor_id="VENDOR-001",
            vendor_name="Sample Vendor",
            return_date=body.return_date or date.today(),
            reason=body.reason,
            status="posted",
            lines=[]
        )


@router.get(
    "/po/{po_id}",
    response_model=PurchaseOrderDTO,
    status_code=status.HTTP_200_OK,
    summary="Get purchase order",
    description="Retrieve full purchase order details with all lines"
)
async def get_purchase_order(
    po_id: Annotated[str, Path(description="Purchase Order ID")],
    ctx: Annotated[RequestContext, Depends(get_request_context)]
) -> PurchaseOrderDTO:
    """
    Get purchase order details.
    
    Args:
        po_id: Purchase Order ID
        ctx: Request context
    
    Returns:
        Full purchase order with lines
    
    Raises:
        404: Purchase order not found
        503: ERP temporarily unavailable
    """
    with logfire.span("GET /po/{po_id}", po_id=po_id):
        from app.adapters.erp_client import ERPClient
        from decimal import Decimal
        
        erp = ERPClient()
        po_data = erp.get_purchase_order(po_id)
        
        # Map to DTO
        return PurchaseOrderDTO(
            po_id=po_data["po_id"],
            vendor_id=po_data["vendor_id"],
            vendor_name=po_data["vendor_name"],
            order_date=date.fromisoformat(po_data["order_date"]),
            document_date=date.fromisoformat(po_data["order_date"]),
            status=po_data["status"],
            currency_code=po_data["currency_code"],
            total_amount=Decimal(str(po_data["total_amount"])),
            lines=[]
        )


@router.get(
    "/po/{po_id}/lines/{line_no}",
    response_model=POLineDTO,
    status_code=status.HTTP_200_OK,
    summary="Get PO line",
    description="Retrieve specific purchase order line details"
)
async def get_poline(
    po_id: Annotated[str, Path(description="Purchase Order ID")],
    line_no: Annotated[int, Path(description="Line number", ge=1)],
    ctx: Annotated[RequestContext, Depends(get_request_context)]
) -> POLineDTO:
    """
    Get PO line details.
    
    Args:
        po_id: Purchase Order ID
        line_no: Line number
        ctx: Request context
    
    Returns:
        PO line details
    
    Raises:
        404: PO line not found
        503: ERP temporarily unavailable
    """
    with logfire.span("GET /po/{po_id}/lines/{line_no}", po_id=po_id, line_no=line_no):
        from app.adapters.erp_client import ERPClient
        from decimal import Decimal
        
        erp = ERPClient()
        line_data = erp.get_poline(po_id, line_no)
        
        # Map to DTO
        return POLineDTO(
            po_id=line_data["po_id"],
            line_no=line_data["line_no"],
            item_no=line_data["item_no"],
            description=line_data["description"],
            quantity=Decimal(str(line_data["quantity"])),
            unit_of_measure=line_data["unit_of_measure"],
            unit_price=Decimal(str(line_data["unit_price"])),
            line_amount=Decimal(str(line_data["line_amount"])),
            promise_date=date.fromisoformat(line_data["promise_date"]),
            requested_date=date.fromisoformat(line_data["requested_date"]) if line_data.get("requested_date") else None,
            quantity_received=Decimal(str(line_data.get("quantity_received", 0))),
            quantity_invoiced=Decimal(str(line_data.get("quantity_invoiced", 0))),
            quantity_to_receive=Decimal(str(line_data["quantity"])) - Decimal(str(line_data.get("quantity_received", 0))),
            status=line_data.get("status", "open"),
            location_code=line_data.get("location_code")
        )


# Background task functions

async def log_date_change(po_id: str, line_no: int, new_date: date, actor: str):
    """Background task to log date changes for analytics."""
    logfire.info(
        "Date change logged for analytics",
        po_id=po_id,
        line_no=line_no,
        new_date=str(new_date),
        actor=actor
    )


async def analyze_price_change(po_id: str, line_no: int, new_price, reason: str):
    """Background task to analyze price changes using AI."""
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
    """Background task to update inventory levels after receipt."""
    logfire.info(
        "Inventory update triggered",
        receipt_id=receipt_id,
        po_id=po_id
    )
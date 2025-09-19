"""
ERP Items endpoints
"""
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, status
import logging
import logfire
from app.api.v1.models import SingleResponse, ErrorResponse
from app.domain.erp.item_service import ItemService
from app.domain.erp.models import ItemResponse, ItemUpdateRequest, CreateItemRequest
from app.errors import ERPNotFound, ERPConflict, ERPError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/items", tags=["ERP - Items"])

def get_item_service():
    """Dependency to get ItemService instance."""
    return ItemService()

@router.get(
    "/{item_id}",
    response_model=SingleResponse[ItemResponse],
    responses={
        200: {"description": "Item retrieved successfully"},
        404: {"description": "Item not found", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse}
    },
    summary="Get item by ID",
    description="""
    Retrieves a single item from the ERP system by its ID.
    
    This endpoint connects to Business Central to fetch real-time item data including:
    - Basic item information (description, unit of measure)
    - Inventory levels
    - Pricing information
    - Item categories and attributes
    """
)
async def get_item(
    item_id: str,
    item_service: ItemService = Depends(get_item_service)
) -> SingleResponse[ItemResponse]:
    """Get a single item by ID from Business Central"""
    try:
        with logfire.span(f"get_item", item_id=item_id):
            item = await item_service.get_item(item_id)
            
        if not item:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": {
                        "code": "ITEM_NOT_FOUND",
                        "message": f"Item with ID '{item_id}' not found",
                        "trace_id": "unknown"
                    }
                }
            )
        
        return SingleResponse(data=item)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching item {item_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "Failed to retrieve item",
                    "trace_id": "unknown"
                }
            }
        )


def _error_payload(exc: ERPError) -> dict:
    """Format ERP errors for standardized response body."""
    return {
        "error": {
            "code": exc.error_code,
            "message": exc.detail,
            "context": getattr(exc, "context", {})
        }
    }


@router.post(
    "/{item_id}/update",
    status_code=status.HTTP_200_OK,
    response_model=SingleResponse[ItemResponse],
    summary="Update item fields",
    description="Apply field updates to an item after refreshing concurrency tokens from Business Central."
)
async def update_item(
    item_id: str,
    payload: ItemUpdateRequest,
    item_service: ItemService = Depends(get_item_service)
) -> SingleResponse[ItemResponse]:
    try:
        with logfire.span("update_item", item_id=item_id, field_count=len(payload.updates)):
            updated = await item_service.update_item(item_id, payload.updates)
        return SingleResponse(data=updated)
    except ERPNotFound as exc:
        raise HTTPException(status_code=exc.status_code, detail=_error_payload(exc))
    except ERPConflict as exc:
        raise HTTPException(status_code=exc.status_code, detail=_error_payload(exc))
    except ERPError as exc:
        raise HTTPException(status_code=exc.status_code, detail=_error_payload(exc))


@router.post(
    "/purchased",
    status_code=status.HTTP_201_CREATED,
    response_model=SingleResponse[ItemResponse],
    summary="Create purchased item",
    description="Create a purchased item by copying template 000 in Business Central."
)
async def create_purchased_item(
    payload: CreateItemRequest,
    item_service: ItemService = Depends(get_item_service)
) -> SingleResponse[ItemResponse]:
    try:
        with logfire.span("create_purchased_item", item_no=payload.item_no):
            created = await item_service.create_purchased_item(payload.item_no)
        return SingleResponse(data=created)
    except ERPConflict as exc:
        raise HTTPException(status_code=exc.status_code, detail=_error_payload(exc))
    except ERPError as exc:
        raise HTTPException(status_code=exc.status_code, detail=_error_payload(exc))


@router.post(
    "/manufactured",
    status_code=status.HTTP_201_CREATED,
    response_model=SingleResponse[ItemResponse],
    summary="Create manufactured item",
    description="Create a manufactured item by copying template 00000 in Business Central."
)
async def create_manufactured_item(
    payload: CreateItemRequest,
    item_service: ItemService = Depends(get_item_service)
) -> SingleResponse[ItemResponse]:
    try:
        with logfire.span("create_manufactured_item", item_no=payload.item_no):
            created = await item_service.create_manufactured_item(payload.item_no)
        return SingleResponse(data=created)
    except ERPConflict as exc:
        raise HTTPException(status_code=exc.status_code, detail=_error_payload(exc))
    except ERPError as exc:
        raise HTTPException(status_code=exc.status_code, detail=_error_payload(exc))

"""
ERP Items endpoints
"""
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, status, Query
import logging
import logfire
from app.api.v1.models import SingleResponse, ErrorResponse
from app.domain.erp.item_service import ItemService
from app.domain.erp.models import (
    ItemResponse,
    ItemUpdateRequest,
    CreateItemRequest,
    ItemPricesResponse,
    TariffCalculationResponse,
)
from app.domain.erp.tariff_service import TariffCalculationService
from app.errors import ERPNotFound, ERPConflict, ERPError, BaseAPIException

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/items", tags=["ERP - Items"])

def get_item_service():
    """Dependency to get ItemService instance."""
    return ItemService()


def get_tariff_service():
    """Dependency to run tariff calculations."""
    return TariffCalculationService()

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


@router.get(
    "/{item_id}/prices",
    response_model=SingleResponse[ItemPricesResponse],
    responses={
        200: {"description": "Item prices retrieved successfully"},
        404: {"description": "Item not found", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
    summary="Get item sales prices in CAD, USD, and EUR",
    description=(
        "Retrieves the active sales prices for the specified item in CAD and USD directly from Business Central, "
        "and derives the EUR price using the latest CAD→EUR exchange rate."
    ),
)
async def get_item_prices(
    item_id: str,
    item_service: ItemService = Depends(get_item_service),
) -> SingleResponse[ItemPricesResponse]:
    try:
        with logfire.span("get_item_prices", item_id=item_id):
            prices = await item_service.get_item_prices(item_id)

        if prices is None:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": {
                        "code": "ITEM_NOT_FOUND",
                        "message": f"Active prices for item '{item_id}' were not found",
                        "trace_id": "unknown",
                    }
                },
            )

        return SingleResponse(data=prices)

    except HTTPException:
        raise
    except ERPError as exc:
        logger.error("Error retrieving prices for item %s: %s", item_id, exc)
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(exc),
                    "trace_id": "unknown",
                }
            },
        )
    except Exception as exc:
        logger.exception("Unexpected error retrieving prices for item %s", item_id)
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "Failed to retrieve item prices",
                    "trace_id": "unknown",
                }
            },
        )


@router.get(
    "/{item_id}/tariff",
    response_model=SingleResponse[TariffCalculationResponse],
    responses={
        200: {"description": "Tariff calculation completed"},
        404: {"description": "Item or BOM not found", "model": ErrorResponse},
        500: {"description": "Tariff calculation failed", "model": ErrorResponse},
    },
    summary="Calculate steel weight/value for an item",
    description=(
        "Runs the internal tariff calculator for the item's production BOM to return steel weights, "
        "CAD/USD value, and melt/pour metadata sourced from Cedule mill test certificates."
    ),
)
async def get_item_tariff(
    item_id: str,
    tariff_service: TariffCalculationService = Depends(get_tariff_service),
    include_details: bool = Query(
        False,
        description="Set to true to include the detailed materials table and formatted report.",
    ),
) -> SingleResponse[TariffCalculationResponse]:
    try:
        result = await tariff_service.calculate(item_id)
        if not include_details:
            result = TariffCalculationResponse(
                item_id=result.item_id,
                production_bom_no=result.production_bom_no,
                summary=result.summary,
                materials=None,
                parent_country_of_melt_and_pour=result.parent_country_of_melt_and_pour,
                parent_country_of_manufacture=result.parent_country_of_manufacture,
                report=None,
            )
        return SingleResponse(data=result)
    except BaseAPIException:
        raise
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Unexpected error calculating tariff for item %s", item_id)
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "Failed to calculate tariff for the requested item",
                    "trace_id": "unknown",
                }
            },
        ) from exc


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

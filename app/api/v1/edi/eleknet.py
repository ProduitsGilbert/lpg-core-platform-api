"""EDI-category endpoints that encapsulate ElekNet/Lumen XML APIs."""

from fastapi import APIRouter, status

from app.api.v1.models import SingleResponse
from app.domain.edi.eleknet import (
    ElekNetOrderRequest,
    ElekNetOrderResponse,
    ElekNetPriceAvailabilityRequest,
    ElekNetPriceAvailabilityResponse,
    ElekNetService,
)

router = APIRouter(prefix="/edi/eleknet", tags=["EDI"])

eleknet_service = ElekNetService()


@router.post(
    "/price-availability",
    response_model=SingleResponse[ElekNetPriceAvailabilityResponse],
    status_code=status.HTTP_200_OK,
    summary="Fetch price and availability from Lumen via ElekNet",
)
async def price_availability(
    request: ElekNetPriceAvailabilityRequest,
) -> SingleResponse[ElekNetPriceAvailabilityResponse]:
    result = await eleknet_service.fetch_price_availability(request)
    return SingleResponse(data=result)


@router.post(
    "/order",
    response_model=SingleResponse[ElekNetOrderResponse],
    status_code=status.HTTP_200_OK,
    summary="Submit an order to Lumen via ElekNet",
)
async def submit_order(request: ElekNetOrderRequest) -> SingleResponse[ElekNetOrderResponse]:
    result = await eleknet_service.create_order(request)
    return SingleResponse(data=result)

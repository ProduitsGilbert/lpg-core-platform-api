import pytest

from app.domain.edi.eleknet.errors import ElekNetUnauthorizedError, ElekNetUpstreamError
from app.domain.edi.eleknet.schemas import (
    ElekNetOrderHeader,
    ElekNetOrderLine,
    ElekNetOrderRequest,
    ElekNetPriceAvailabilityItemRequest,
    ElekNetPriceAvailabilityRequest,
)
from app.domain.edi.eleknet.service import ElekNetService


class _FakeClient:
    username = "user"
    password = "pass"

    def __init__(self, xpa_response: str = "", order_response: str = ""):
        self._xpa_response = xpa_response
        self._order_response = order_response

    async def post_xpa(self, _xml_payload: str) -> str:
        return self._xpa_response

    async def post_order(self, _xml_payload: str) -> str:
        return self._order_response


@pytest.mark.asyncio
async def test_fetch_price_availability_maps_access_denied_to_unauthorized():
    client = _FakeClient(xpa_response="<xPAResponse><returnCode>A</returnCode><returnMessage>Access denied</returnMessage></xPAResponse>")
    service = ElekNetService(client=client)
    request = ElekNetPriceAvailabilityRequest(
        items=[ElekNetPriceAvailabilityItemRequest(productCode="ABC-001", qty=1)]
    )

    with pytest.raises(ElekNetUnauthorizedError):
        await service.fetch_price_availability(request)


@pytest.mark.asyncio
async def test_create_order_maps_error_return_code_to_bad_gateway():
    client = _FakeClient(order_response="<orderResponse><returnCode>E</returnCode><returnMessage>Validation failed</returnMessage></orderResponse>")
    service = ElekNetService(client=client)
    request = ElekNetOrderRequest(
        orderHeader=ElekNetOrderHeader(
            partner="Lumen",
            type="Order",
            custno="CUST-01",
            shipTo="SHIP-01",
            whse="WH-1",
            po="PO-100",
            delivery="Y",
            shipComplete="N",
        ),
        orderLines=[ElekNetOrderLine(productCode="ABC-001", qty=1)],
    )

    with pytest.raises(ElekNetUpstreamError):
        await service.create_order(request)

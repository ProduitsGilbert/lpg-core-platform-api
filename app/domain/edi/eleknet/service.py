"""Service layer for ElekNet EDI-category operations."""

from __future__ import annotations

import asyncio
from time import perf_counter

import logfire

from app.settings import settings

from .client import ElekNetClient
from .errors import ElekNetUnauthorizedError, ElekNetUpstreamError
from .parsers import (
    build_order_request_xml,
    build_xpa_request_xml,
    parse_order_response,
    parse_xpa_response,
)
from .schemas import (
    ElekNetOrderRequest,
    ElekNetOrderResponse,
    ElekNetPriceAvailabilityRequest,
    ElekNetPriceAvailabilityResponse,
)


class ElekNetService:
    """Encapsulate ElekNet XML protocol behind stable JSON models."""

    def __init__(self, client: ElekNetClient | None = None):
        self.client = client or ElekNetClient()
        self._semaphore = asyncio.Semaphore(settings.eleknet_max_concurrency)

    async def fetch_price_availability(
        self, request: ElekNetPriceAvailabilityRequest
    ) -> ElekNetPriceAvailabilityResponse:
        started = perf_counter()
        response: ElekNetPriceAvailabilityResponse | None = None

        async with self._semaphore:
            xml_request = build_xpa_request_xml(
                username=self.client.username or "",
                password=self.client.password or "",
                request=request,
            )
            xml_response = await self.client.post_xpa(xml_request)
            response = parse_xpa_response(xml_response)
            self._validate_return_code(response.returnCode, response.returnMessage)

        elapsed_ms = int((perf_counter() - started) * 1000)
        logfire.info(
            "ElekNet xPA completed",
            endpoint="price-availability",
            item_count=len(request.items),
            duration_ms=elapsed_ms,
            return_code=response.returnCode if response else None,
        )
        return response

    async def create_order(self, request: ElekNetOrderRequest) -> ElekNetOrderResponse:
        started = perf_counter()
        response: ElekNetOrderResponse | None = None

        async with self._semaphore:
            xml_request = build_order_request_xml(
                username=self.client.username or "",
                password=self.client.password or "",
                request=request,
            )
            xml_response = await self.client.post_order(xml_request)
            response = parse_order_response(xml_response)
            self._validate_return_code(response.returnCode, response.returnMessage)

        elapsed_ms = int((perf_counter() - started) * 1000)
        logfire.info(
            "ElekNet order completed",
            endpoint="order",
            line_count=len(request.orderLines),
            duration_ms=elapsed_ms,
            return_code=response.returnCode if response else None,
            po=response.po or request.orderHeader.po,
            order_number=response.orderNumber,
        )
        return response

    @staticmethod
    def _validate_return_code(return_code: str | None, return_message: str | None) -> None:
        if return_code is None:
            return

        normalized = return_code.strip().upper()
        if normalized == "S":
            return
        if normalized == "A":
            raise ElekNetUnauthorizedError(return_message or "ElekNet access denied")
        if normalized == "E":
            raise ElekNetUpstreamError(return_message or "ElekNet returned an error")
        raise ElekNetUpstreamError(
            f"Unexpected ElekNet returnCode '{return_code}'"
            + (f": {return_message}" if return_message else "")
        )

"""Business Central data retrieval endpoints."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional

import httpx
import logfire
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.domain.erp.business_central_data_service import BusinessCentralODataService
from app.domain.erp.customer_geocode_cache import customer_geocode_cache
from app.domain.erp.models import (
    CustomerAddressResponse,
    CustomerSalesStatsResponse,
    CustomerSummaryResponse,
    GeocodedLocation,
    VendorContactResponse,
)
from app.domain.erp.vendor_contact_service import VendorContactService
from app.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/bc", tags=["ERP - Business Central Data"])


def get_odata_service() -> BusinessCentralODataService:
    """FastAPI dependency for the Business Central OData service."""
    return BusinessCentralODataService()


def get_vendor_contact_service(
    service: BusinessCentralODataService = Depends(get_odata_service),
) -> VendorContactService:
    """Dependency wrapper for vendor contact lookups."""
    return VendorContactService(service)


async def _fetch_with_handling(
    *,
    resource: str,
    filter_field: Optional[str],
    filter_value: Optional[str],
    top: Optional[int],
    service: BusinessCentralODataService,
) -> List[Dict[str, Any]]:
    """Centralized error handling for upstream fetch operations."""
    try:
        return await service.fetch_collection(
            resource,
            filter_field=filter_field,
            filter_value=filter_value,
            top=top,
        )
    except httpx.HTTPStatusError as exc:
        status_code = exc.response.status_code if exc.response else status.HTTP_502_BAD_GATEWAY
        logger.error(
            "Business Central returned HTTP error",
            extra={"resource": resource, "status_code": status_code},
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "error": {
                    "code": "BC_UPSTREAM_ERROR",
                    "message": "Business Central request failed",
                    "upstream_status": status_code,
                }
            },
        ) from exc
    except httpx.RequestError as exc:
        logger.error(
            "Business Central request failed",
            extra={"resource": resource, "error": str(exc)},
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "error": {
                    "code": "BC_UPSTREAM_UNAVAILABLE",
                    "message": "Business Central service unreachable",
                }
            },
        ) from exc


async def _fetch_ship_to_addresses(
    customer_no: str,
    service: BusinessCentralODataService,
    semaphore: asyncio.Semaphore,
) -> List[Dict[str, Any]]:
    resource_candidates = (
        "ShipToAddress",
        "ShipToAddresses",
        "Ship_to_Address",
        "Ship_to_Addresses",
    )
    filter_candidates = ("Customer_No", "CustomerNo")

    async with semaphore:
        for resource in resource_candidates:
            for filter_field in filter_candidates:
                try:
                    records = await service.fetch_collection(
                        resource,
                        filter_field=filter_field,
                        filter_value=customer_no,
                        top=None,
                    )
                except httpx.HTTPStatusError as exc:
                    status_code = exc.response.status_code if exc.response else None
                    if status_code in {400, 404}:
                        continue
                    logger.warning(
                        "Ship-to lookup failed",
                        extra={
                            "resource": resource,
                            "status_code": status_code,
                            "customer_no": customer_no,
                        },
                    )
                    return []
                except httpx.RequestError as exc:
                    logger.warning(
                        "Ship-to lookup unavailable",
                        extra={"error": str(exc), "customer_no": customer_no},
                    )
                    return []
                return records
    return []


def _ship_to_code(record: Dict[str, Any]) -> Optional[str]:
    for key in ("Code", "ShipToCode", "Ship_to_Code", "ShipTo_Code"):
        value = record.get(key)
        if value:
            return str(value)
    return None


def _ship_to_name(record: Dict[str, Any]) -> Optional[str]:
    for key in ("Name", "ShipToName", "Ship_to_Name", "ShipTo_Name"):
        value = record.get(key)
        if value:
            return str(value)
    return None


def _has_address_fields(address: str) -> bool:
    return bool(address and address.strip())


@router.get(
    "/posted-sales-invoice-headers",
    response_model=List[Dict[str, Any]],
    summary="List posted sales invoice headers",
    description="Retrieve posted sales invoice headers from Business Central with optional filtering on document number.",
)
async def list_posted_sales_invoice_headers(
    no: Optional[str] = Query(
        default=None,
        description="Filter by invoice number (No).",
    ),
    top: Optional[int] = Query(
        default=None,
        ge=1,
        le=500,
        description="Limit the number of records returned.",
    ),
    service: BusinessCentralODataService = Depends(get_odata_service),
) -> List[Dict[str, Any]]:
    """Return posted sales invoice headers."""
    with logfire.span("bc_api.list_posted_sales_invoice_headers", no=no, top=top):
        records = await _fetch_with_handling(
            resource="PostedSalesInvoiceHeaders",
            filter_field="No",
            filter_value=no,
            top=top,
            service=service,
        )
    return records


@router.get(
    "/purchase-order-lines",
    response_model=List[Dict[str, Any]],
    summary="List purchase order lines",
    description="Retrieve Gilbert purchase order lines with optional filtering by document number.",
)
async def list_purchase_order_lines(
    document_no: Optional[str] = Query(
        default=None,
        description="Filter by purchase order number (Document_No).",
    ),
    top: Optional[int] = Query(
        default=None,
        ge=1,
        le=500,
        description="Limit the number of records returned.",
    ),
    service: BusinessCentralODataService = Depends(get_odata_service),
) -> List[Dict[str, Any]]:
    """Return purchase order lines from the Gilbert-specific view."""
    with logfire.span("bc_api.list_purchase_order_lines", document_no=document_no, top=top):
        records = await _fetch_with_handling(
            resource="Gilbert_PurchaseOrderLines",
            filter_field="Document_No",
            filter_value=document_no,
            top=top,
            service=service,
        )
    return records


@router.get(
    "/vendors",
    response_model=List[Dict[str, Any]],
    summary="List vendors",
    description="Retrieve vendors with optional filtering by vendor number.",
)
async def list_vendors(
    no: Optional[str] = Query(
        default=None,
        description="Filter by vendor number (No).",
    ),
    top: Optional[int] = Query(
        default=None,
        ge=1,
        le=500,
        description="Limit the number of records returned.",
    ),
    service: BusinessCentralODataService = Depends(get_odata_service),
) -> List[Dict[str, Any]]:
    """Return vendor records."""
    with logfire.span("bc_api.list_vendors", no=no, top=top):
        records = await _fetch_with_handling(
            resource="Vendors",
            filter_field="No",
            filter_value=no,
            top=top,
            service=service,
        )
    return records


@router.get(
    "/customers",
    response_model=List[CustomerSummaryResponse],
    summary="List customers",
    description="Retrieve customers with optional filtering by customer number. Returns address details including ship-to locations.",
)
async def list_customers(
    no: Optional[str] = Query(
        default=None,
        description="Filter by customer number (No).",
    ),
    top: Optional[int] = Query(
        default=None,
        ge=1,
        le=500,
        description="Limit the number of records returned.",
    ),
    service: BusinessCentralODataService = Depends(get_odata_service),
) -> List[CustomerSummaryResponse]:
    """Return customer summaries with ship-to address locations."""
    with logfire.span("bc_api.list_customers", no=no, top=top):
        records = await _fetch_with_handling(
            resource="Customers",
            filter_field="No",
            filter_value=no,
            top=top,
            service=service,
        )

        summaries: List[CustomerSummaryResponse] = []
        refresh_tasks: List[asyncio.Task] = []
        blocking_pairs: List[tuple[Any, asyncio.Task]] = []
        ship_to_semaphore = asyncio.Semaphore(settings.google_geocode_max_concurrency)
        ship_to_tasks: Dict[str, asyncio.Task] = {}

        for record in records:
            customer_no = str(record.get("No") or "")
            if not customer_no:
                continue
            ship_to_tasks[customer_no] = asyncio.create_task(
                _fetch_ship_to_addresses(customer_no, service, ship_to_semaphore)
            )

        for record in records:
            customer_no = str(record.get("No") or "")
            if not customer_no:
                continue
            address = customer_geocode_cache.build_address(record)
            if _has_address_fields(address):
                geocode = customer_geocode_cache.get_cached(customer_no, address)
            else:
                geocode = GeocodedLocation(status="MISSING_ADDRESS")
            summaries.append(
                CustomerSummaryResponse(
                    customer_no=customer_no,
                    name=str(record.get("Name") or ""),
                    city=record.get("City"),
                    postal_code=record.get("Post_Code") or record.get("PostCode"),
                    address_1=record.get("Address"),
                    address_2=record.get("Address_2") or record.get("Address2"),
                    address_3=record.get("Address_3") or record.get("Address3"),
                    address_4=record.get("Address_4") or record.get("Address4"),
                    county=record.get("County"),
                    country=record.get("Country_Region_Code")
                    or record.get("CountryRegionCode")
                    or record.get("Country"),
                    geocode=geocode,
                    ship_to_addresses=[],
                )
            )

            if customer_no and _has_address_fields(address) and geocode is None:
                if settings.google_geocode_block_on_miss and geocode is None:
                    blocking_pairs.append(
                        (
                            summaries[-1],
                            asyncio.create_task(
                                customer_geocode_cache.get_or_fetch(customer_no, address)
                            ),
                        )
                    )
                else:
                    refresh_tasks.append(
                        asyncio.create_task(
                            customer_geocode_cache.schedule_refresh(customer_no, address)
                        )
                    )

            ship_to_records = []
            if customer_no in ship_to_tasks:
                try:
                    ship_to_records = await asyncio.wait_for(
                        ship_to_tasks[customer_no],
                        timeout=settings.bc_ship_to_timeout_seconds,
                    )
                except asyncio.TimeoutError:
                    ship_to_tasks[customer_no].cancel()
                    ship_to_records = []

            if ship_to_records:
                for ship_to in ship_to_records:
                    ship_to_address = customer_geocode_cache.build_address_from_ship_to(
                        ship_to
                    )
                    if _has_address_fields(ship_to_address):
                        ship_to_geocode = customer_geocode_cache.get_cached(
                            customer_no, ship_to_address
                        )
                    else:
                        ship_to_geocode = GeocodedLocation(status="MISSING_ADDRESS")
                    ship_to_entry = CustomerAddressResponse(
                        source="ship_to",
                        ship_to_code=_ship_to_code(ship_to),
                        name=_ship_to_name(ship_to),
                        address_1=ship_to.get("Address"),
                        address_2=ship_to.get("Address_2") or ship_to.get("Address2"),
                        address_3=ship_to.get("Address_3") or ship_to.get("Address3"),
                        address_4=ship_to.get("Address_4") or ship_to.get("Address4"),
                        city=ship_to.get("City"),
                        county=ship_to.get("County"),
                        postal_code=ship_to.get("Post_Code") or ship_to.get("PostCode"),
                        country=ship_to.get("Country_Region_Code")
                        or ship_to.get("CountryRegionCode")
                        or ship_to.get("Country"),
                        geocode=ship_to_geocode,
                    )
                    summaries[-1].ship_to_addresses.append(ship_to_entry)

                    if customer_no and _has_address_fields(ship_to_address) and ship_to_geocode is None:
                        if (
                            settings.google_geocode_block_on_miss
                            and ship_to_geocode is None
                        ):
                            blocking_pairs.append(
                                (
                                    ship_to_entry,
                                    asyncio.create_task(
                                        customer_geocode_cache.get_or_fetch(
                                            customer_no, ship_to_address
                                        )
                                    ),
                                )
                            )
                        else:
                            refresh_tasks.append(
                                asyncio.create_task(
                                    customer_geocode_cache.schedule_refresh(
                                        customer_no, ship_to_address
                                    )
                                )
                            )
            else:
                fallback_entry = CustomerAddressResponse(
                    source="customer",
                    name=str(record.get("Name") or ""),
                    address_1=record.get("Address"),
                    address_2=record.get("Address_2") or record.get("Address2"),
                    address_3=record.get("Address_3") or record.get("Address3"),
                    address_4=record.get("Address_4") or record.get("Address4"),
                    city=record.get("City"),
                    county=record.get("County"),
                    postal_code=record.get("Post_Code") or record.get("PostCode"),
                    country=record.get("Country_Region_Code")
                    or record.get("CountryRegionCode")
                    or record.get("Country"),
                    geocode=geocode,
                )
                summaries[-1].ship_to_addresses.append(fallback_entry)

        if blocking_pairs:
            tasks = {task for _, task in blocking_pairs}
            timeout = settings.google_geocode_block_timeout_seconds
            if timeout > 0:
                done, _pending = await asyncio.wait(tasks, timeout=timeout)
            else:
                done, _pending = await asyncio.wait(tasks, timeout=0)

            for target, task in blocking_pairs:
                if task in done:
                    try:
                        target.geocode = task.result()
                    except Exception:
                        continue

            for summary in summaries:
                if summary.ship_to_addresses and summary.geocode:
                    for address_entry in summary.ship_to_addresses:
                        if address_entry.source == "customer":
                            address_entry.geocode = summary.geocode

        # Do not block response on refresh tasks; let them run in background.
    return summaries


@router.get(
    "/customers/{customer_no}",
    response_model=Dict[str, Any],
    summary="Get customer details",
    description="Retrieve full Business Central customer record by customer number.",
)
async def get_customer(
    customer_no: str,
    service: BusinessCentralODataService = Depends(get_odata_service),
) -> Dict[str, Any]:
    """Return the full customer record for the provided customer number."""
    with logfire.span("bc_api.get_customer", customer_no=customer_no):
        records = await _fetch_with_handling(
            resource="Customers",
            filter_field="No",
            filter_value=customer_no,
            top=1,
            service=service,
        )

    if not records:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "BC_CUSTOMER_NOT_FOUND",
                    "message": "Customer not found",
                }
            },
        )

    return records[0]


@router.get(
    "/vendor-email-contact",
    response_model=VendorContactResponse,
    summary="Get vendor email contact details",
    description="Retrieve the vendor email contact, language, and name using Business Central and easyPDFAddress data.",
)
async def get_vendor_email_contact(
    vendor_no: str = Query(..., min_length=1, description="Vendor number (No) to look up."),
    contact_service: VendorContactService = Depends(get_vendor_contact_service),
) -> VendorContactResponse:
    """Return vendor email contact using the easyPDFAddress endpoint."""
    try:
        contact = await contact_service.get_vendor_contact(vendor_no)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "INVALID_VENDOR",
                    "message": str(exc),
                }
            },
        ) from exc
    except httpx.HTTPStatusError as exc:
        status_code = exc.response.status_code if exc.response else status.HTTP_502_BAD_GATEWAY
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "error": {
                    "code": "BC_VENDOR_CONTACT_ERROR",
                    "message": "Business Central vendor contact lookup failed",
                    "upstream_status": status_code,
                }
            },
        ) from exc
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "error": {
                    "code": "BC_VENDOR_CONTACT_UNAVAILABLE",
                    "message": "Business Central vendor contact service unreachable",
                }
            },
        ) from exc

    return VendorContactResponse(**contact.to_dict())


@router.get(
    "/items",
    response_model=List[Dict[str, Any]],
    summary="List items",
    description="Retrieve items with optional filtering by item number.",
)
async def list_items(
    no: Optional[str] = Query(
        default=None,
        description="Filter by item number (No).",
    ),
    top: Optional[int] = Query(
        default=None,
        ge=1,
        le=500,
        description="Limit the number of records returned.",
    ),
    service: BusinessCentralODataService = Depends(get_odata_service),
) -> List[Dict[str, Any]]:
    """Return item master records."""
    with logfire.span("bc_api.list_items", no=no, top=top):
        records = await _fetch_with_handling(
            resource="Items",
            filter_field="No",
            filter_value=no,
            top=top,
            service=service,
        )
    return records


@router.get(
    "/purchase-order-headers",
    response_model=List[Dict[str, Any]],
    summary="List purchase order headers",
    description="Retrieve purchase order headers with optional filtering by order number.",
)
async def list_purchase_order_headers(
    no: Optional[str] = Query(
        default=None,
        description="Filter by purchase order number (No).",
    ),
    top: Optional[int] = Query(
        default=None,
        ge=1,
        le=500,
        description="Limit the number of records returned.",
    ),
    service: BusinessCentralODataService = Depends(get_odata_service),
) -> List[Dict[str, Any]]:
    """Return purchase order headers."""
    with logfire.span("bc_api.list_purchase_order_headers", no=no, top=top):
        records = await _fetch_with_handling(
            resource="PurchaseOrderHeaders",
            filter_field="No",
            filter_value=no,
            top=top,
            service=service,
        )
    return records


@router.get(
    "/sales-order-headers",
    response_model=List[Dict[str, Any]],
    summary="List sales order headers",
    description="Retrieve sales order headers with optional filtering by order number.",
)
async def list_sales_order_headers(
    no: Optional[str] = Query(
        default=None,
        description="Filter by sales order number (No).",
    ),
    top: Optional[int] = Query(
        default=None,
        ge=1,
        le=500,
        description="Limit the number of records returned.",
    ),
    service: BusinessCentralODataService = Depends(get_odata_service),
) -> List[Dict[str, Any]]:
    """Return sales order headers."""
    with logfire.span("bc_api.list_sales_order_headers", no=no, top=top):
        records = await _fetch_with_handling(
            resource="SalesOrderHeaders",
            filter_field="No",
            filter_value=no,
            top=top,
            service=service,
        )
    return records


@router.get(
    "/sales-order-lines",
    response_model=List[Dict[str, Any]],
    summary="List sales order lines",
    description="Retrieve Gilbert sales order lines with optional filtering by document number.",
)
async def list_sales_order_lines(
    document_no: Optional[str] = Query(
        default=None,
        description="Filter by sales order number (Document_No).",
    ),
    top: Optional[int] = Query(
        default=None,
        ge=1,
        le=500,
        description="Limit the number of records returned.",
    ),
    service: BusinessCentralODataService = Depends(get_odata_service),
) -> List[Dict[str, Any]]:
    """Return sales order lines from the Gilbert-specific view."""
    with logfire.span("bc_api.list_sales_order_lines", document_no=document_no, top=top):
        records = await _fetch_with_handling(
            resource="Gilbert_SalesOrderLines",
            filter_field="DocumentNo",
            filter_value=document_no,
            top=top,
            service=service,
        )
    return records


@router.get(
    "/sales-quote-headers",
    response_model=List[Dict[str, Any]],
    summary="List sales quote headers",
    description="Retrieve sales order quote headers with optional filtering by quote number.",
)
async def list_sales_quote_headers(
    no: Optional[str] = Query(
        default=None,
        description="Filter by sales quote number (No).",
    ),
    top: Optional[int] = Query(
        default=None,
        ge=1,
        le=500,
        description="Limit the number of records returned.",
    ),
    service: BusinessCentralODataService = Depends(get_odata_service),
) -> List[Dict[str, Any]]:
    """Return sales quote header records."""
    with logfire.span("bc_api.list_sales_quote_headers", no=no, top=top):
        records = await _fetch_with_handling(
            resource="SalesOrderQuotesH",
            filter_field="No",
            filter_value=no,
            top=top,
            service=service,
        )
    return records


@router.get(
    "/sales-quote-lines",
    response_model=List[Dict[str, Any]],
    summary="List sales quote lines",
    description="Retrieve sales quote lines with optional filtering by quote document number.",
)
async def list_sales_quote_lines(
    document_no: Optional[str] = Query(
        default=None,
        description="Filter by quote document number (Document_No).",
    ),
    top: Optional[int] = Query(
        default=None,
        ge=1,
        le=500,
        description="Limit the number of records returned.",
    ),
    service: BusinessCentralODataService = Depends(get_odata_service),
) -> List[Dict[str, Any]]:
    """Return sales quote lines."""
    with logfire.span("bc_api.list_sales_quote_lines", document_no=document_no, top=top):
        records = await _fetch_with_handling(
            resource="SalesQuoteLines",
            filter_field="Document_No",
            filter_value=document_no,
            top=top,
            service=service,
        )
    return records


@router.get(
    "/customer-sales-stats",
    response_model=CustomerSalesStatsResponse,
    summary="Get sales statistics for a customer",
    description="Retrieve aggregated sales quote and sales order statistics for a specific customer, including totals and quote-to-order relationships.",
)
async def get_customer_sales_stats(
    customer_id: str = Query(..., min_length=1, description="Customer ID to get sales statistics for."),
    service: BusinessCentralODataService = Depends(get_odata_service),
) -> CustomerSalesStatsResponse:
    """Return sales statistics for a specific customer."""
    with logfire.span("bc_api.get_customer_sales_stats", customer_id=customer_id):
        from decimal import Decimal
        from app.domain.erp.models import CustomerSalesQuoteStats, CustomerSalesOrderStats

        def _coerce_decimal(value: Any) -> Optional[Decimal]:
            if value is None:
                return None
            try:
                return Decimal(str(value))
            except (ValueError, TypeError):
                return None

        def _first_decimal(line: Dict[str, Any], fields: List[str]) -> Optional[Decimal]:
            for field in fields:
                if field in line and line[field] is not None:
                    amount = _coerce_decimal(line[field])
                    if amount is not None:
                        return amount
            return None

        def _extract_item_no(line: Dict[str, Any]) -> Optional[str]:
            for field in ["No", "ItemNo", "Item_No", "No_", "Item_No_", "ItemNumber", "Item_Number"]:
                value = line.get(field)
                if value:
                    return str(value)
            return None

        # Fetch sales quote headers for the customer
        quote_headers = await _fetch_with_handling(
            resource="SalesOrderQuotesH",
            filter_field="Sell_to_Customer_No",
            filter_value=customer_id,
            top=None,
            service=service,
        )

        # Fetch sales order headers for the customer
        order_headers = await _fetch_with_handling(
            resource="SalesOrderHeaders",
            filter_field="Sell_to_Customer_No",
            filter_value=customer_id,
            top=None,
            service=service,
        )

        # Aggregate quote statistics from lines (sum amounts from all quote lines)
        total_quote_amount = Decimal("0")
        total_quote_amount_incl_tax = Decimal("0")
        total_quote_quantity = Decimal("0")
        quote_distinct_items: set[str] = set()
        quote_numbers = [quote.get("No") for quote in quote_headers if quote.get("No")]

        for quote in quote_headers:
            quote_no = quote.get("No")
            if not quote_no:
                continue
            quote_lines = await _fetch_with_handling(
                resource="SalesQuoteLines",
                filter_field="Document_No",
                filter_value=quote_no,
                top=None,
                service=service,
            )
            quote_line_quantity = Decimal("0")
            quote_line_amount = Decimal("0")
            quote_line_amount_incl_tax = Decimal("0")
            quote_line_items: set[str] = set()
            for line in quote_lines:
                # Sum line amounts (try different possible field names)
                line_amount = _first_decimal(line, ["Line_Amount", "LineAmount", "Amount"])
                if line_amount is not None:
                    quote_line_amount += line_amount
                    total_quote_amount += line_amount

                line_amount_incl_tax = _first_decimal(
                    line,
                    [
                        "Amount_Including_VAT",
                        "AmountIncludingVAT",
                        "Line_Amount_Including_VAT",
                        "LineAmountIncludingVAT",
                    ],
                )
                if line_amount_incl_tax is not None:
                    quote_line_amount_incl_tax += line_amount_incl_tax
                    total_quote_amount_incl_tax += line_amount_incl_tax

                # Sum quantities
                if "Quantity" in line and line["Quantity"] is not None:
                    quantity = _coerce_decimal(line["Quantity"])
                    if quantity is not None:
                        quote_line_quantity += quantity
                        total_quote_quantity += quantity

                item_no = _extract_item_no(line)
                if item_no:
                    quote_line_items.add(item_no)
                    quote_distinct_items.add(item_no)

            quote["total_amount"] = quote_line_amount
            quote["total_amount_including_tax"] = quote_line_amount_incl_tax
            quote["total_quantity"] = quote_line_quantity
            quote["distinct_product_count"] = len(quote_line_items)

        # Aggregate order statistics
        total_order_amount = Decimal("0")
        total_order_amount_incl_tax = Decimal("0")
        total_order_quantity = Decimal("0")
        order_distinct_items: set[str] = set()
        orders_based_on_quotes = 0
        order_numbers = [order.get("No") for order in order_headers if order.get("No")]

        for order in order_headers:
            # Check if order is based on a quote
            if order.get("Quote_No"):
                orders_based_on_quotes += 1

        # Aggregate amounts and quantities from order lines
        for order in order_headers:
            order_no = order.get("No")
            if not order_no:
                continue
            order_lines = await _fetch_with_handling(
                resource="Gilbert_SalesOrderLines",
                filter_field="DocumentNo",
                filter_value=order_no,
                top=None,
                service=service,
            )
            order_line_quantity = Decimal("0")
            order_line_amount = Decimal("0")
            order_line_amount_incl_tax = Decimal("0")
            order_line_items: set[str] = set()
            for line in order_lines:
                # Sum line amounts (try different possible field names)
                line_amount = _first_decimal(line, ["LineAmount", "Line_Amount", "Amount"])
                if line_amount is not None:
                    order_line_amount += line_amount
                    total_order_amount += line_amount

                line_amount_incl_tax = _first_decimal(
                    line,
                    [
                        "Amount_Including_VAT",
                        "AmountIncludingVAT",
                        "Line_Amount_Including_VAT",
                        "LineAmountIncludingVAT",
                    ],
                )
                if line_amount_incl_tax is not None:
                    order_line_amount_incl_tax += line_amount_incl_tax
                    total_order_amount_incl_tax += line_amount_incl_tax

                # Sum quantities
                if "Quantity" in line and line["Quantity"] is not None:
                    quantity = _coerce_decimal(line["Quantity"])
                    if quantity is not None:
                        order_line_quantity += quantity
                        total_order_quantity += quantity

                item_no = _extract_item_no(line)
                if item_no:
                    order_line_items.add(item_no)
                    order_distinct_items.add(item_no)

            order["total_amount"] = order_line_amount
            order["total_amount_including_tax"] = order_line_amount_incl_tax
            order["total_quantity"] = order_line_quantity
            order["distinct_product_count"] = len(order_line_items)

        return CustomerSalesStatsResponse(
            customer_id=customer_id,
            quotes=CustomerSalesQuoteStats(
                total_quotes=len(quote_headers),
                total_amount=total_quote_amount,
                total_amount_including_tax=total_quote_amount_incl_tax,
                total_quantity=total_quote_quantity,
                total_distinct_products=len(quote_distinct_items),
                quotes=quote_headers,
            ),
            orders=CustomerSalesOrderStats(
                total_orders=len(order_headers),
                total_amount=total_order_amount,
                total_amount_including_tax=total_order_amount_incl_tax,
                total_quantity=total_order_quantity,
                total_distinct_products=len(order_distinct_items),
                orders_based_on_quotes=orders_based_on_quotes,
                orders=order_headers,
            ),
        )

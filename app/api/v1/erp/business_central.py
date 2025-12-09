"""Business Central data retrieval endpoints."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import httpx
import logfire
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.domain.erp.business_central_data_service import BusinessCentralODataService
from app.domain.erp.models import VendorContactResponse
from app.domain.erp.vendor_contact_service import VendorContactService

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

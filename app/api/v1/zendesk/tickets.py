"""Zendesk tickets endpoints."""

from __future__ import annotations

import logging
from typing import Optional

import logfire
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.v1.models import CollectionResponse, ErrorResponse, SingleResponse
from app.deps import get_db
from app.domain.zendesk.service import ZendeskService
from app.domain.zendesk.models import ZendeskTicketResponse, ZendeskTicketsResponse
from app.errors import BaseAPIException

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tickets", tags=["Zendesk - Tickets"])

zendesk_service = ZendeskService()


@router.get(
    "/customer/{customer_id}",
    response_model=CollectionResponse[ZendeskTicketResponse],
    responses={
        200: {"description": "Tickets retrieved successfully"},
        400: {"description": "Invalid request parameters", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
    summary="List tickets for a specific customer",
    description="""
    Retrieve all tickets (open or closed) for a specific customer.

    - If `include_closed` is false, only open tickets will be returned
    - Supports pagination with `page` and `per_page` parameters
    - Customer ID can be an email address or organization ID
    """,
)
async def list_tickets_for_customer(
    customer_id: str,
    include_closed: bool = Query(
        True,
        description="Whether to include closed/solved tickets",
        example=True
    ),
    page: Optional[int] = Query(
        None,
        description="Page number for pagination (optional)",
        ge=1,
        example=1
    ),
    per_page: Optional[int] = Query(
        None,
        description="Number of tickets per page (optional, max 100)",
        ge=1,
        le=100,
        example=25
    ),
    db: Session = Depends(get_db),
) -> CollectionResponse[ZendeskTicketResponse]:
    """List tickets for a specific customer with optional filtering."""
    try:
        with logfire.span(
            "list_tickets_for_customer",
            customer_id=customer_id,
            include_closed=include_closed,
            page=page,
            per_page=per_page
        ):
            result = await zendesk_service.get_tickets_for_customer(
                customer_id=customer_id,
                include_closed=include_closed,
                page=page,
                per_page=per_page
            )

        return CollectionResponse(data=[ZendeskTicketResponse(ticket=ticket) for ticket in result.tickets])
    except HTTPException:
        raise
    except BaseAPIException:
        raise
    except Exception as exc:
        logger.error("Error retrieving tickets for customer %s: %s", customer_id, exc)
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "Failed to retrieve Zendesk tickets",
                    "trace_id": getattr(db, "trace_id", "unknown"),
                }
            },
        )


@router.get(
    "/open",
    response_model=CollectionResponse[ZendeskTicketResponse],
    responses={
        200: {"description": "Open tickets retrieved successfully"},
        400: {"description": "Invalid request parameters", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
    summary="List all currently open tickets",
    description="""
    Retrieve all currently open tickets from Zendesk.

    - Supports pagination with `page` and `per_page` parameters
    - Only returns tickets with status "open"
    """,
)
async def list_open_tickets(
    page: Optional[int] = Query(
        None,
        description="Page number for pagination (optional)",
        ge=1,
        example=1
    ),
    per_page: Optional[int] = Query(
        None,
        description="Number of tickets per page (optional, max 100)",
        ge=1,
        le=100,
        example=25
    ),
    db: Session = Depends(get_db),
) -> CollectionResponse[ZendeskTicketResponse]:
    """List all currently open tickets."""
    try:
        with logfire.span("list_open_tickets", page=page, per_page=per_page):
            result = await zendesk_service.get_open_tickets(
                page=page,
                per_page=per_page
            )

        return CollectionResponse(data=[ZendeskTicketResponse(ticket=ticket) for ticket in result.tickets])
    except HTTPException:
        raise
    except BaseAPIException:
        raise
    except Exception as exc:
        logger.error("Error retrieving open tickets: %s", exc)
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "Failed to retrieve open Zendesk tickets",
                    "trace_id": getattr(db, "trace_id", "unknown"),
                }
            },
        )


@router.get(
    "/past-year",
    response_model=CollectionResponse[ZendeskTicketResponse],
    responses={
        200: {"description": "Past year tickets retrieved successfully"},
        400: {"description": "Invalid request parameters", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
    summary="List all tickets from the past year",
    description="""
    Retrieve all tickets created in the past year from Zendesk.

    - Supports pagination with `page` and `per_page` parameters
    - Includes both open and closed tickets
    """,
)
async def list_past_year_tickets(
    page: Optional[int] = Query(
        None,
        description="Page number for pagination (optional)",
        ge=1,
        example=1
    ),
    per_page: Optional[int] = Query(
        None,
        description="Number of tickets per page (optional, max 100)",
        ge=1,
        le=100,
        example=25
    ),
    db: Session = Depends(get_db),
) -> CollectionResponse[ZendeskTicketResponse]:
    """List all tickets from the past year."""
    try:
        with logfire.span("list_past_year_tickets", page=page, per_page=per_page):
            result = await zendesk_service.get_past_year_tickets(
                page=page,
                per_page=per_page
            )

        return CollectionResponse(data=[ZendeskTicketResponse(ticket=ticket) for ticket in result.tickets])
    except HTTPException:
        raise
    except BaseAPIException:
        raise
    except Exception as exc:
        logger.error("Error retrieving past year tickets: %s", exc)
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "Failed to retrieve past year Zendesk tickets",
                    "trace_id": getattr(db, "trace_id", "unknown"),
                }
            },
        )


@router.get(
    "/{ticket_id}",
    response_model=SingleResponse[ZendeskTicketResponse],
    responses={
        200: {"description": "Ticket retrieved successfully"},
        404: {"description": "Ticket not found", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
    summary="Get ticket by ID",
    description="Retrieve a specific ticket from Zendesk by its ID.",
)
async def get_ticket_by_id(
    ticket_id: int,
    db: Session = Depends(get_db),
) -> SingleResponse[ZendeskTicketResponse]:
    """Get a specific Zendesk ticket by ID."""
    try:
        with logfire.span("get_ticket_by_id", ticket_id=ticket_id):
            ticket = await zendesk_service.get_ticket_by_id(ticket_id)

        if not ticket:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": {
                        "code": "TICKET_NOT_FOUND",
                        "message": f"Ticket '{ticket_id}' not found",
                        "trace_id": getattr(db, "trace_id", "unknown"),
                    }
                },
            )

        return SingleResponse(data=ZendeskTicketResponse(ticket=ticket))
    except HTTPException:
        raise
    except BaseAPIException:
        raise
    except Exception as exc:
        logger.error("Error retrieving ticket %s: %s", ticket_id, exc)
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "Failed to retrieve Zendesk ticket",
                    "trace_id": getattr(db, "trace_id", "unknown"),
                }
            },
        )


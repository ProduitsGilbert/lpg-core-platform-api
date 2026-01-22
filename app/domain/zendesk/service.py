"""Zendesk service for ticket management."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Type

import logfire

from app.adapters.zendesk_client import ZendeskClient
from app.domain.zendesk.models import (
    ZendeskExportSearchResponse,
    ZendeskSearchResponse,
    ZendeskTicket,
    ZendeskTicketResponse,
    ZendeskTicketsResponse,
)
from app.errors import BaseAPIException, ExternalServiceException
from app.ports import ZendeskClientProtocol

logger = logging.getLogger(__name__)


class ZendeskService:
    """Service for Zendesk operations."""

    def __init__(self, zendesk_client_class: Type[ZendeskClientProtocol] = ZendeskClient):
        self._zendesk_client_class = zendesk_client_class

    def _client(self) -> ZendeskClientProtocol:
        return self._zendesk_client_class()  # type: ignore[return-value]

    async def get_tickets_for_customer(
        self,
        customer_id: str,
        include_closed: bool = True,
        page: Optional[int] = None,
        per_page: Optional[int] = None
    ) -> ZendeskTicketsResponse:
        """Get all tickets (open or closed) for a specific customer."""
        try:
            with logfire.span(
                "get_tickets_for_customer",
                customer_id=customer_id,
                include_closed=include_closed,
                page=page,
                per_page=per_page
            ):
                # Build search query for tickets by customer
                # Zendesk search uses 'requester:<email>' or 'organization:<id>' format
                # We'll assume customer_id could be email or organization ID
                if "@" in customer_id:
                    # It's an email address
                    query = f"type:ticket requester:{customer_id}"
                else:
                    # Assume it's an organization ID
                    query = f"type:ticket organization:{customer_id}"

                if not include_closed:
                    query += " status<solved"

                async with self._client() as client:
                    response = await client.search_tickets(
                        query=query,
                        page=page,
                        per_page=per_page
                    )

                # Convert raw response to our domain models
                tickets = []
                for result in response.get("results", []):
                    if result.get("result_type") == "ticket":
                        ticket_data = result.get("ticket", result)
                        tickets.append(ticket_data)

                return ZendeskTicketsResponse(
                    tickets=tickets,
                    count=response.get("count", len(tickets)),
                    next_page=response.get("next_page"),
                    previous_page=response.get("previous_page")
                )
        except Exception as exc:
            logger.error("Error retrieving tickets for customer %s: %s", customer_id, exc)
            raise ExternalServiceException(
                f"Failed to retrieve tickets for customer {customer_id}",
                service="zendesk"
            ) from exc

    async def get_open_tickets(
        self,
        page: Optional[int] = None,
        per_page: Optional[int] = None
    ) -> ZendeskTicketsResponse:
        """Get all currently open tickets."""
        try:
            with logfire.span("get_open_tickets", page=page, per_page=per_page):
                # Use search API to filter active tickets (anything not solved/closed)
                query = "type:ticket status<solved"

                async with self._client() as client:
                    response = await client.search_tickets(
                        query=query,
                        page=page,
                        per_page=per_page
                    )

                # Convert raw response to our domain models
                tickets = []
                for result in response.get("results", []):
                    if result.get("result_type") == "ticket":
                        ticket_data = result.get("ticket", result)
                        tickets.append(ticket_data)

                return ZendeskTicketsResponse(
                    tickets=tickets,
                    count=response.get("count", len(tickets)),
                    next_page=response.get("next_page"),
                    previous_page=response.get("previous_page")
                )
        except Exception as exc:
            logger.error("Error retrieving open tickets: %s", exc)
            raise ExternalServiceException("Failed to retrieve open tickets", service="zendesk") from exc

    async def get_past_year_tickets(
        self,
        page: Optional[int] = None,
        per_page: Optional[int] = None
    ) -> ZendeskTicketsResponse:
        """Get all tickets from the past year."""
        try:
            with logfire.span("get_past_year_tickets", page=page, per_page=per_page):
                # Calculate date one year ago
                one_year_ago = datetime.now() - timedelta(days=365)
                date_str = one_year_ago.strftime("%Y-%m-%d")

                # Use export search to fetch ALL tickets from past year, no paging exposed
                query = f"type:ticket created>{date_str}"
                tickets: List[dict] = []
                after_cursor: Optional[str] = None

                async with self._client() as client:
                    while True:
                        response = await client.export_search_results(
                            query=query,
                            page_size=1000,
                            after_cursor=after_cursor
                        )

                        tickets.extend(response.get("results", []))

                        meta = response.get("meta", {}) or {}
                        has_more = meta.get("has_more")
                        after_cursor = meta.get("after_cursor")

                        if not has_more or not after_cursor:
                            break

                return ZendeskTicketsResponse(
                    tickets=tickets,
                    count=len(tickets),
                    next_page=None,
                    previous_page=None
                )
        except Exception as exc:
            logger.error("Error retrieving past year tickets: %s", exc)
            raise ExternalServiceException("Failed to retrieve past year tickets", service="zendesk") from exc

    async def get_ticket_by_id(self, ticket_id: int) -> Optional[ZendeskTicket]:
        """Get a specific ticket by ID."""
        try:
            with logfire.span("get_ticket_by_id", ticket_id=ticket_id):
                async with self._client() as client:
                    response = await client.get_ticket(ticket_id)

                ticket_data = response.get("ticket", response)
                if ticket_data:
                    return ticket_data
                return None
        except Exception as exc:
            logger.error("Error retrieving ticket %s: %s", ticket_id, exc)
            raise ExternalServiceException(f"Failed to retrieve ticket {ticket_id}", service="zendesk") from exc


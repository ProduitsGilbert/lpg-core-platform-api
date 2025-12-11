"""Zendesk domain models."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ZendeskCustomField(BaseModel):
    """Custom field for a Zendesk ticket."""

    id: int = Field(description="The id of the custom field")
    value: Optional[str] = Field(default=None, description="The value of the custom field")


class ZendeskTicket(BaseModel):
    """Zendesk ticket object."""

    id: Optional[int] = Field(default=None, description="Automatically assigned when the ticket is created")
    url: Optional[str] = Field(default=None, description="The API url of this ticket")
    external_id: Optional[str] = Field(default=None, description="An id you can use to link Zendesk Support tickets to local records")

    # Status and priority
    status: str = Field(description="The state of the ticket")
    priority: Optional[str] = Field(default=None, description="The urgency with which the ticket should be addressed")

    # Subject and description
    subject: str = Field(description="The value of the subject field for this ticket")
    description: Optional[str] = Field(default=None, description="Read-only first comment on the ticket")

    # Requester and assignee
    requester_id: int = Field(description="The user who requested this ticket")
    assignee_id: Optional[int] = Field(default=None, description="The agent currently assigned to the ticket")
    organization_id: Optional[int] = Field(default=None, description="The organization of the requester")

    # Groups and collaborators
    group_id: Optional[int] = Field(default=None, description="The group this ticket is assigned to")
    collaborator_ids: List[int] = Field(default_factory=list, description="The ids of users currently CC'ed on the ticket")
    email_cc_ids: List[int] = Field(default_factory=list, description="The ids of agents or end users currently CC'ed on the ticket")
    follower_ids: List[int] = Field(default_factory=list, description="The ids of agents currently following the ticket")

    # Dates
    created_at: datetime = Field(description="When this record was created")
    updated_at: Optional[datetime] = Field(default=None, description="When this record last got updated")
    due_at: Optional[datetime] = Field(default=None, description="If this is a ticket of type 'task' it has a due date")

    # Other properties
    ticket_type: Optional[str] = Field(default=None, description="The type of this ticket")
    tags: List[str] = Field(default_factory=list, description="The array of tags applied to this ticket")
    custom_fields: List[ZendeskCustomField] = Field(default_factory=list, description="Custom fields for the ticket")
    brand_id: Optional[int] = Field(default=None, description="The id of the brand this ticket is associated with")

    # Problem/incident linking
    problem_id: Optional[int] = Field(default=None, description="For tickets of type 'incident', the ID of the problem the incident is linked to")
    has_incidents: bool = Field(default=False, description="Is true if a ticket is a problem type and has one or more incidents linked to it")

    # Additional metadata
    via: Optional[Dict[str, Any]] = Field(default=None, description="How the ticket was created")
    satisfaction_rating: Optional[Dict[str, Any]] = Field(default=None, description="The satisfaction rating of the ticket")


class ZendeskTicketResponse(BaseModel):
    """Response containing a single Zendesk ticket."""

    ticket: ZendeskTicket


class ZendeskTicketsResponse(BaseModel):
    """Response containing multiple Zendesk tickets."""

    tickets: List[ZendeskTicket]
    count: Optional[int] = Field(default=None, description="The number of resources returned")
    next_page: Optional[str] = Field(default=None, description="URL to the next page of results")
    previous_page: Optional[str] = Field(default=None, description="URL to the previous page of results")


class ZendeskSearchResponse(BaseModel):
    """Response from Zendesk search API."""

    results: List[Dict[str, Any]] = Field(description="Search results (may contain tickets, users, groups, or organizations)")
    count: int = Field(description="The number of resources returned by the query")
    next_page: Optional[str] = Field(default=None, description="URL to the next page of results")
    previous_page: Optional[str] = Field(default=None, description="URL to the previous page of results")
    facets: Optional[str] = Field(default=None, description="The facets corresponding to the search query")


class ZendeskExportSearchResponse(BaseModel):
    """Response from Zendesk export search API."""

    results: List[Dict[str, Any]] = Field(description="Export search results")
    meta: Dict[str, Any] = Field(description="Metadata about the response")
    links: Optional[Dict[str, str]] = Field(default=None, description="Pagination links")


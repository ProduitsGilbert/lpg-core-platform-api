"""ERP webhook endpoints for Business Central integrations."""
from __future__ import annotations

from datetime import datetime
import logging
from typing import Any, List

from fastapi import APIRouter, Response, status
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)

try:
    import logfire
except ImportError:  # pragma: no cover - logfire is optional in tests
    logfire = None


router = APIRouter(prefix="/webhooks", tags=["ERP - Webhooks"])


class BusinessCentralNotification(BaseModel):
    """Notification payload received from Business Central webhooks."""

    subscription_id: str = Field(..., alias="subscriptionId", description="Subscription identifier")
    client_state: str | None = Field(None, alias="clientState", description="Client state token if provided")
    change_type: str | None = Field(None, alias="changeType", description="Type of change")
    resource: str | None = Field(None, alias="resource", description="Resource identifier affected by the change")
    resource_id: str | None = Field(None, alias="resourceId", description="Resource instance identifier")
    sequence_number: int | None = Field(None, alias="sequenceNumber", description="Sequence number for ordering notifications")
    expiration_datetime: datetime | None = Field(None, alias="expirationDateTime", description="Subscription expiration timestamp")

    model_config = ConfigDict(
        populate_by_name=True,
        extra="allow",  # Business Central may send additional fields depending on the resource
        frozen=False,
    )


@router.get(
    "/items",
    response_class=PlainTextResponse,
    summary="Business Central validation handshake",
    description="Responds to the initial validation request issued by Business Central when registering an items webhook."
)
async def validate_items_webhook(validationtoken: str | None = None) -> Response:
    """Respond to Business Central's validation request by echoing the provided token."""
    if validationtoken is not None:
        if logfire:
            logfire.info(
                "Business Central webhook validation received",
                endpoint="items",
                validationtoken_present=True,
            )
        else:
            logger.info("Business Central items webhook validation received")

        return PlainTextResponse(content=validationtoken)

    if logfire:
        logfire.info(
            "Business Central webhook validation received without token",
            endpoint="items",
            validationtoken_present=False,
        )
    else:
        logger.info("Business Central items webhook validation received without token")

    return Response(status_code=status.HTTP_200_OK)


@router.post(
    "/items",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Receive Business Central item notifications",
    description=(
        "Endpoint that Business Central calls with item change notifications. "
        "Notifications are accepted and should be handed off to downstream processors."
    ),
)
async def receive_items_notifications(payload: List[BusinessCentralNotification]) -> Response:
    """Accept item notifications from Business Central and acknowledge receipt."""
    if not payload:
        if logfire:
            logfire.info(
                "Business Central webhook notification received with empty payload",
                endpoint="items",
            )
        else:
            logger.info("Business Central items webhook notification received with empty payload")

        return Response(status_code=status.HTTP_202_ACCEPTED)

    for notification in payload:
        details: dict[str, Any] = {
            "endpoint": "items",
            "subscription_id": notification.subscription_id,
            "change_type": notification.change_type,
            "resource": notification.resource,
            "sequence_number": notification.sequence_number,
        }
        if logfire:
            logfire.info("Business Central webhook notification received", **details)
        else:
            logger.info("Business Central items webhook notification received", extra=details)

    return Response(status_code=status.HTTP_202_ACCEPTED)

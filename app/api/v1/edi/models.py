"""Pydantic models for EDI API endpoints."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class PurchaseOrder850Request(BaseModel):
    """Request payload to trigger an EDI 850 transmission."""

    po_number: str = Field(..., min_length=1, max_length=50, description="Purchase order number")


class PurchaseOrder850Response(BaseModel):
    """Response payload describing the outcome of an EDI 850 transmission."""

    po_number: str
    file_name: str
    sent: bool
    generated_at: datetime
    remote_path: Optional[str] = None
    message: Optional[str] = None

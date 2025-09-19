"""
Data Transfer Objects (DTOs) for the purchasing domain.

This module defines Pydantic v2 models for request/response validation
and serialization. All models use strict typing and forbid extra fields.
"""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator


class POStatus(str, Enum):
    """Purchase Order status enumeration."""
    DRAFT = "draft"
    OPEN = "open"
    RELEASED = "released"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    PARTIALLY_RECEIVED = "partially_received"
    RECEIVED = "received"
    INVOICED = "invoiced"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class POLineStatus(str, Enum):
    """Purchase Order Line status enumeration."""
    OPEN = "open"
    RELEASED = "released"
    PARTIALLY_RECEIVED = "partially_received"
    RECEIVED = "received"
    INVOICED = "invoiced"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class ReceiptStatus(str, Enum):
    """Receipt status enumeration."""
    DRAFT = "draft"
    POSTED = "posted"
    CANCELLED = "cancelled"


class BaseDTO(BaseModel):
    """Base model for all DTOs with common configuration."""
    
    model_config = ConfigDict(
        extra="forbid",  # Reject unknown fields
        str_strip_whitespace=True,  # Strip whitespace from strings
        use_enum_values=True,  # Use enum values instead of enum instances
        json_encoders={
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat(),
            Decimal: lambda v: str(v)
        }
    )


# Request DTOs

class UpdatePOLineDateBody(BaseDTO):
    """Request body for updating PO line promise date."""
    
    new_date: date = Field(
        ...,
        description="New promise date for the PO line"
    )
    reason: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Business reason for the date change"
    )
    idempotency_key: Optional[str] = Field(
        None,
        max_length=128,
        description="Idempotency key for request deduplication"
    )
    
    @field_validator("new_date")
    @classmethod
    def validate_future_date(cls, v: date) -> date:
        """Ensure the new date is not in the past."""
        if v < date.today():
            raise ValueError("Promise date cannot be in the past")
        return v


class UpdatePOLinePriceBody(BaseDTO):
    """Request body for updating PO line unit price."""
    
    new_price: Decimal = Field(
        ...,
        gt=0,
        decimal_places=2,
        description="New unit price for the PO line"
    )
    reason: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Business reason for the price change"
    )
    idempotency_key: Optional[str] = Field(
        None,
        max_length=128,
        description="Idempotency key for request deduplication"
    )


class UpdatePOLineQuantityBody(BaseDTO):
    """Request body for updating PO line quantity."""
    
    new_quantity: Decimal = Field(
        ...,
        gt=0,
        description="New quantity for the PO line"
    )
    reason: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Business reason for the quantity change"
    )
    idempotency_key: Optional[str] = Field(
        None,
        max_length=128,
        description="Idempotency key for request deduplication"
    )


class CreateReceiptBody(BaseDTO):
    """Request body for creating a new receipt."""
    
    po_id: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Purchase Order ID"
    )
    vendor_shipment_no: Optional[str] = Field(
        None,
        max_length=50,
        description="Vendor shipment reference number"
    )
    lines: List["ReceiptLineInput"] = Field(
        ...,
        min_length=1,
        description="Receipt lines to create"
    )
    receipt_date: Optional[date] = Field(
        None,
        description="Receipt date (defaults to today)"
    )
    notes: Optional[str] = Field(
        None,
        max_length=500,
        description="Optional receipt notes"
    )
    job_check_delay_seconds: int = Field(
        default=5,
        ge=0,
        le=60,
        description="Seconds to wait before checking posting status"
    )
    idempotency_key: Optional[str] = Field(
        None,
        max_length=128,
        description="Idempotency key for request deduplication"
    )


class ReceiptLineInput(BaseDTO):
    """Input for a single receipt line."""
    
    line_no: int = Field(
        ...,
        ge=1,
        description="PO line number"
    )
    quantity: Decimal = Field(
        ...,
        gt=0,
        description="Quantity to receive"
    )
    location_code: Optional[str] = Field(
        None,
        max_length=20,
        description="Warehouse location code"
    )
    vendor_shipment_no: Optional[str] = Field(
        None,
        max_length=50,
        description="Optional line-level vendor shipment reference override"
    )


class CreateReturnBody(BaseDTO):
    """Request body for creating a return."""
    
    receipt_id: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Original receipt ID"
    )
    lines: List["ReturnLineInput"] = Field(
        ...,
        min_length=1,
        description="Return lines to create"
    )
    reason: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Reason for return"
    )
    return_date: Optional[date] = Field(
        None,
        description="Return date (defaults to today)"
    )
    idempotency_key: Optional[str] = Field(
        None,
        max_length=128,
        description="Idempotency key for request deduplication"
    )


class ReturnLineInput(BaseDTO):
    """Input for a single return line."""
    
    line_no: int = Field(
        ...,
        ge=1,
        description="Receipt line number"
    )
    quantity: Decimal = Field(
        ...,
        gt=0,
        description="Quantity to return"
    )


# Response DTOs

class VendorDTO(BaseDTO):
    """Vendor information DTO."""
    
    vendor_id: str = Field(..., description="Vendor ID")
    name: str = Field(..., description="Vendor name")
    address: Optional[str] = Field(None, description="Vendor address")
    city: Optional[str] = Field(None, description="City")
    state: Optional[str] = Field(None, description="State/Province")
    postal_code: Optional[str] = Field(None, description="Postal code")
    country: Optional[str] = Field(None, description="Country")
    contact_name: Optional[str] = Field(None, description="Primary contact name")
    contact_email: Optional[str] = Field(None, description="Contact email")
    contact_phone: Optional[str] = Field(None, description="Contact phone")
    payment_terms: Optional[str] = Field(None, description="Payment terms code")
    currency_code: Optional[str] = Field(None, description="Default currency")
    is_active: bool = Field(True, description="Vendor active status")


class ItemDTO(BaseDTO):
    """Item/Product information DTO."""
    
    item_no: str = Field(..., description="Item number")
    description: str = Field(..., description="Item description")
    unit_of_measure: str = Field(..., description="Base unit of measure")
    unit_cost: Optional[Decimal] = Field(None, description="Standard unit cost")
    vendor_item_no: Optional[str] = Field(None, description="Vendor's item number")
    category_code: Optional[str] = Field(None, description="Item category")
    is_active: bool = Field(True, description="Item active status")


class POLineDTO(BaseDTO):
    """Purchase Order Line DTO."""
    
    po_id: str = Field(..., description="Purchase Order ID")
    line_no: int = Field(..., description="Line number")
    item_no: str = Field(..., description="Item number")
    description: str = Field(..., description="Line description")
    quantity: Decimal = Field(..., description="Ordered quantity")
    unit_of_measure: str = Field(..., description="Unit of measure")
    unit_price: Decimal = Field(..., description="Unit price")
    line_amount: Decimal = Field(..., description="Total line amount")
    promise_date: date = Field(..., description="Promise delivery date")
    requested_date: Optional[date] = Field(None, description="Requested delivery date")
    quantity_received: Decimal = Field(0, description="Quantity received")
    quantity_invoiced: Decimal = Field(0, description="Quantity invoiced")
    quantity_to_receive: Decimal = Field(..., description="Outstanding quantity")
    status: POLineStatus = Field(..., description="Line status")
    location_code: Optional[str] = Field(None, description="Delivery location")
    
    @model_validator(mode="after")
    def calculate_outstanding(self):
        """Calculate outstanding quantity."""
        self.quantity_to_receive = self.quantity - self.quantity_received
        return self


class PurchaseOrderDTO(BaseDTO):
    """Purchase Order DTO."""
    
    po_id: str = Field(..., description="Purchase Order ID")
    vendor_id: str = Field(..., description="Vendor ID")
    vendor_name: str = Field(..., description="Vendor name")
    order_date: date = Field(..., description="Order date")
    document_date: date = Field(..., description="Document date")
    expected_receipt_date: Optional[date] = Field(None, description="Expected receipt date")
    status: POStatus = Field(..., description="PO status")
    currency_code: str = Field(..., description="Currency code")
    total_amount: Decimal = Field(..., description="Total PO amount")
    lines: List[POLineDTO] = Field(default_factory=list, description="PO lines")
    created_by: Optional[str] = Field(None, description="Created by user")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    modified_by: Optional[str] = Field(None, description="Last modified by")
    modified_at: Optional[datetime] = Field(None, description="Last modification timestamp")


class ReceiptLineDTO(BaseDTO):
    """Receipt Line DTO."""
    
    receipt_id: str = Field(..., description="Receipt ID")
    line_no: int = Field(..., description="Receipt line number")
    po_id: str = Field(..., description="Purchase Order ID")
    po_line_no: int = Field(..., description="PO line number")
    item_no: str = Field(..., description="Item number")
    description: str = Field(..., description="Item description")
    quantity_received: Decimal = Field(..., description="Quantity received")
    unit_of_measure: str = Field(..., description="Unit of measure")
    location_code: Optional[str] = Field(None, description="Receipt location")
    receipt_date: date = Field(..., description="Receipt date")


class ReceiptDTO(BaseDTO):
    """Receipt DTO."""
    
    receipt_id: str = Field(..., description="Receipt ID")
    po_id: str = Field(..., description="Purchase Order ID")
    vendor_id: str = Field(..., description="Vendor ID")
    vendor_name: str = Field(..., description="Vendor name")
    receipt_date: date = Field(..., description="Receipt date")
    posting_date: Optional[date] = Field(None, description="Posting date")
    status: ReceiptStatus = Field(..., description="Receipt status")
    lines: List[ReceiptLineDTO] = Field(default_factory=list, description="Receipt lines")
    notes: Optional[str] = Field(None, description="Receipt notes")
    created_by: Optional[str] = Field(None, description="Created by user")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")


class ReturnDTO(BaseDTO):
    """Return DTO."""
    
    return_id: str = Field(..., description="Return ID")
    receipt_id: str = Field(..., description="Original receipt ID")
    po_id: str = Field(..., description="Purchase Order ID")
    vendor_id: str = Field(..., description="Vendor ID")
    vendor_name: str = Field(..., description="Vendor name")
    return_date: date = Field(..., description="Return date")
    reason: str = Field(..., description="Return reason")
    status: str = Field(..., description="Return status")
    lines: List["ReturnLineDTO"] = Field(default_factory=list, description="Return lines")
    created_by: Optional[str] = Field(None, description="Created by user")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")


class ReturnLineDTO(BaseDTO):
    """Return Line DTO."""
    
    return_id: str = Field(..., description="Return ID")
    line_no: int = Field(..., description="Return line number")
    receipt_line_no: int = Field(..., description="Original receipt line number")
    item_no: str = Field(..., description="Item number")
    description: str = Field(..., description="Item description")
    quantity_returned: Decimal = Field(..., description="Quantity returned")
    unit_of_measure: str = Field(..., description="Unit of measure")


class QuoteDTO(BaseDTO):
    """Purchase Quote DTO."""
    
    quote_id: str = Field(..., description="Quote ID")
    vendor_id: str = Field(..., description="Vendor ID")
    vendor_name: str = Field(..., description="Vendor name")
    quote_date: date = Field(..., description="Quote date")
    valid_until: Optional[date] = Field(None, description="Quote validity date")
    status: str = Field(..., description="Quote status")
    currency_code: str = Field(..., description="Currency code")
    total_amount: Decimal = Field(..., description="Total quote amount")
    lines: List["QuoteLineDTO"] = Field(default_factory=list, description="Quote lines")


class QuoteLineDTO(BaseDTO):
    """Quote Line DTO."""
    
    quote_id: str = Field(..., description="Quote ID")
    line_no: int = Field(..., description="Line number")
    item_no: str = Field(..., description="Item number")
    description: str = Field(..., description="Item description")
    quantity: Decimal = Field(..., description="Quoted quantity")
    unit_of_measure: str = Field(..., description="Unit of measure")
    unit_price: Decimal = Field(..., description="Unit price")
    line_amount: Decimal = Field(..., description="Total line amount")
    delivery_date: Optional[date] = Field(None, description="Promised delivery date")


# Aggregate/Command DTOs

class PurchaseCommand(BaseDTO):
    """Base command for purchasing operations."""
    
    actor: str = Field(..., description="User or system performing the action")
    trace_id: Optional[str] = Field(None, description="Request trace ID")
    idempotency_key: Optional[str] = Field(None, max_length=128)


class UpdatePOLineDateCommand(PurchaseCommand):
    """Command to update PO line promise date."""
    
    po_id: str
    line_no: int
    new_date: date
    reason: str


class UpdatePOLinePriceCommand(PurchaseCommand):
    """Command to update PO line unit price."""
    
    po_id: str
    line_no: int
    new_price: Decimal
    reason: str


class UpdatePOLineQuantityCommand(PurchaseCommand):
    """Command to update PO line quantity."""
    
    po_id: str
    line_no: int
    new_quantity: Decimal
    reason: str


class CreateReceiptCommand(PurchaseCommand):
    """Command to create a receipt."""
    
    po_id: str
    lines: List[ReceiptLineInput]
    receipt_date: date
    notes: Optional[str] = None
    vendor_shipment_no: Optional[str] = None
    job_check_delay_seconds: int = 5


class CreateReturnCommand(PurchaseCommand):
    """Command to create a return."""
    
    receipt_id: str
    lines: List[ReturnLineInput]
    reason: str
    return_date: date


# Forward reference updates for nested models
CreateReceiptBody.model_rebuild()
CreateReturnBody.model_rebuild()
PurchaseOrderDTO.model_rebuild()
ReceiptDTO.model_rebuild()
ReturnDTO.model_rebuild()
QuoteDTO.model_rebuild()

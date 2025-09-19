"""
Domain models for ERP entities
"""
from typing import Optional, List, Any
from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, Field

# Item models
class ItemResponse(BaseModel):
    """Item data from Business Central"""
    id: str = Field(..., description="Item number/ID")
    type: str = "item"
    description: str = Field(..., description="Item description")
    unit_of_measure: str = Field(..., description="Base unit of measure")
    unit_cost: Decimal = Field(default=Decimal("0"), description="Unit cost")
    unit_price: Decimal = Field(default=Decimal("0"), description="Unit price")
    inventory: Decimal = Field(default=Decimal("0"), description="Current inventory level")
    item_category_code: Optional[str] = Field(None, description="Item category")
    blocked: bool = Field(default=False, description="Item blocked status")
    last_modified: Optional[datetime] = Field(None, description="Last modification timestamp")
    vendor_id: Optional[str] = Field(None, description="Primary vendor ID")
    vendor_name: Optional[str] = Field(None, description="Primary vendor name")
    vendor_item_no: Optional[str] = Field(None, description="Vendor's item number")
    qty_on_purchase_order: Decimal = Field(default=Decimal("0"), description="Quantity on purchase orders")
    qty_on_sales_order: Decimal = Field(default=Decimal("0"), description="Quantity on sales orders")
    lead_time_calculation: Optional[str] = Field(None, description="Lead time calculation")
    replenishment_system: Optional[str] = Field(None, description="Replenishment system")
    gross_weight: Optional[Decimal] = Field(None, description="Gross weight")
    net_weight: Optional[Decimal] = Field(None, description="Net weight")
    country_region_of_origin: Optional[str] = Field(None, description="Country/Region of origin")
    safety_stock_quantity: Optional[Decimal] = Field(None, description="Safety stock quantity")

    class Config:
        json_encoders = {
            Decimal: lambda v: float(v),
            datetime: lambda v: v.isoformat() if v else None
        }


class ItemValueChange(BaseModel):
    """Single field update requested for an item."""

    field: str = Field(..., min_length=1, description="Business Central field name to update")
    current_value: Optional[Any] = Field(
        None,
        description="Expected current value; used for optimistic concurrency"
    )
    new_value: Any = Field(..., description="New value to persist in Business Central")


class ItemUpdateRequest(BaseModel):
    """Request body for updating one or more item fields."""

    updates: List[ItemValueChange] = Field(
        ..., min_length=1, description="One or more field updates to apply"
    )


class CreateItemRequest(BaseModel):
    """Request body for creating a new item from a template."""

    item_no: str = Field(..., min_length=1, description="Destination item number")

# Purchase Order models
class PurchaseOrderResponse(BaseModel):
    """Purchase Order header from Business Central"""
    id: str = Field(..., description="Purchase order number")
    type: str = "purchase-order"
    vendor_id: str = Field(..., description="Vendor ID")
    vendor_name: str = Field(..., description="Vendor name")
    order_date: date = Field(..., description="Order date")
    expected_receipt_date: Optional[date] = Field(None, description="Expected receipt date")
    status: str = Field(..., description="Order status")
    total_amount: Decimal = Field(default=Decimal("0"), description="Total order amount")
    currency_code: str = Field(default="USD", description="Currency code")
    buyer_id: Optional[str] = Field(None, description="Buyer/Purchaser ID")
    location_code: Optional[str] = Field(None, description="Location code")
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v),
            date: lambda v: v.isoformat() if v else None
        }

class PurchaseOrderLineResponse(BaseModel):
    """Purchase Order line from Business Central with Gilbert custom fields"""
    id: str = Field(..., description="Line ID")
    type: str = "purchase-order-line"
    line_no: int = Field(..., description="Line number")
    item_no: str = Field(..., description="Item number")
    description: str = Field(..., description="Item description")
    quantity: Decimal = Field(..., description="Ordered quantity")
    quantity_received: Decimal = Field(default=Decimal("0"), description="Received quantity")
    quantity_invoiced: Decimal = Field(default=Decimal("0"), description="Invoiced quantity")
    outstanding_qty: Optional[Decimal] = Field(None, description="Outstanding quantity")
    unit_of_measure: str = Field(..., description="Unit of measure")
    unit_cost: Decimal = Field(..., description="Unit cost")
    line_amount: Decimal = Field(..., description="Line amount")
    promised_receipt_date: Optional[date] = Field(None, description="Promised receipt date from vendor")
    expected_receipt_date: Optional[date] = Field(None, description="Expected receipt date")
    mrp_date_requise: Optional[date] = Field(None, description="MRP required date")
    location_code: Optional[str] = Field(None, description="Location code")
    vendor_item_no: Optional[str] = Field(None, description="Vendor item number")
    suivi_status: Optional[str] = Field(None, description="Tracking status")
    no_suivi: Optional[str] = Field(None, description="Tracking number")
    no_job_ref: Optional[str] = Field(None, description="Job reference number")
    job_no: Optional[str] = Field(None, description="Job number")
    job_task_no: Optional[str] = Field(None, description="Job task number")
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v),
            date: lambda v: v.isoformat() if v else None
        }

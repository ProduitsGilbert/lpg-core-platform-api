"""
Domain models for ERP entities
"""
from typing import Optional, List, Any, Dict
from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict

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


class ItemPricesResponse(BaseModel):
    """Aggregated item pricing across supported currencies."""

    item_id: str
    cad_price: Decimal = Field(..., description="Unit sales price in CAD")
    usd_price: Decimal = Field(..., description="Unit sales price in USD")
    eur_price: Decimal = Field(..., description="Unit sales price converted to EUR")

    class Config:
        json_encoders = {
            Decimal: lambda v: float(v),
        }


class ItemAvailabilityTimelineEntry(BaseModel):
    """Projected inventory snapshot for a calendar month."""

    period_start: date = Field(..., description="Month start date (YYYY-MM-01)")
    incoming_qty: Decimal = Field(default=Decimal("0"), description="Quantity expected to arrive during the month")
    outgoing_qty: Decimal = Field(default=Decimal("0"), description="Quantity required during the month")
    projected_available: Decimal = Field(
        default=Decimal("0"),
        description="Projected ending available quantity after this month",
    )
    incoming_jobs: List[str] = Field(default_factory=list, description="Jobs contributing to inbound supply")
    outgoing_jobs: List[str] = Field(default_factory=list, description="Jobs consuming inventory")

    class Config:
        json_encoders = {
            Decimal: lambda v: float(v),
            date: lambda v: v.isoformat() if v else None,
        }


class ItemAvailabilityResponse(BaseModel):
    """Summary of on-hand and projected availability."""

    item_id: str
    as_of_date: date = Field(..., description="Date when availability was calculated")
    current_inventory: Decimal = Field(..., description="On-hand quantity in fixed bins at GIL")
    total_incoming: Decimal = Field(..., description="Sum of open inbound supply from MRP In endpoint")
    total_outgoing: Decimal = Field(..., description="Sum of demand from MRP Out endpoint")
    projected_available: Decimal = Field(..., description="Net availability after planned supply and demand")
    details_included: bool = Field(
        default=False,
        description="Indicates whether the monthly timeline data is populated",
    )
    timeline: Optional[List[ItemAvailabilityTimelineEntry]] = Field(
        default=None,
        description="Monthly breakdown when details are requested",
    )

    class Config:
        json_encoders = {
            Decimal: lambda v: float(v),
            date: lambda v: v.isoformat() if v else None,
        }


class ItemAttributeValueEntry(BaseModel):
    """Single attribute and value assigned to an item."""

    attribute_id: int = Field(..., description="Business Central item attribute ID")
    attribute_name: str = Field(..., description="Item attribute name")
    attribute_type: str = Field(..., description="Attribute data type (Option, Decimal, Text)")
    value_id: int = Field(..., description="Business Central attribute value ID")
    value: str = Field(..., description="Value assigned to the item attribute")


class ItemAttributesResponse(BaseModel):
    """Collection of attribute values for a specific item."""

    item_id: str = Field(..., description="Item number/ID")
    attributes: List[ItemAttributeValueEntry] = Field(
        default_factory=list,
        description="Attributes assigned to the item",
    )


class VendorContactResponse(BaseModel):
    """Vendor email contact details."""

    vendor_id: str = Field(..., description="Vendor number (No)")
    email: str = Field(..., description="Primary contact email address")
    language: str = Field(..., description="Preferred communication language")
    language_code: Optional[str] = Field(None, description="Business Central language code")
    name: str = Field("", description="Vendor name")
    communication_language: str = Field(..., description="Alias mirroring language field for compatibility")


class TariffMaterialResponse(BaseModel):
    """Single BOM component output from the tariff calculator."""

    item_no: str
    description: str
    material_type: str
    quantity: float
    scrap_percent: float
    dimensions: Dict[str, float] = Field(default_factory=dict)
    weight_per_piece_lbs: float
    weight_per_piece_kg: float
    total_weight_lbs: float
    total_weight_kg: float
    total_with_scrap_lbs: float
    total_with_scrap_kg: float
    standard_cost_cad: float
    total_cost_cad: float
    total_cost_usd: float
    vendor_no: Optional[str] = None
    vendor_item_no: Optional[str] = None
    country_of_melt_and_pour: Optional[str] = None
    country_of_manufacture: Optional[str] = None
    note: Optional[str] = None


class TariffSummaryResponse(BaseModel):
    """Aggregated totals for a tariff calculation."""

    total_materials: int
    calculated_materials: int
    total_weight_kg: float
    total_weight_with_scrap_kg: float
    total_cost_cad: float
    total_cost_usd: float
    exchange_rate: float


class TariffCalculationResponse(BaseModel):
    """Full tariff calculation payload for an item."""

    item_id: str
    production_bom_no: str
    summary: TariffSummaryResponse
    materials: Optional[List[TariffMaterialResponse]] = None
    parent_country_of_melt_and_pour: Optional[str] = None
    parent_country_of_manufacture: Optional[str] = None
    report: Optional[str] = None


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


class PurchaseOrderReopenRequest(BaseModel):
    """Request payload to reopen a released purchase order."""

    header_no: str = Field(
        ...,
        alias="headerNo",
        min_length=1,
        description="Purchase order number to reopen"
    )

    model_config = ConfigDict(
        populate_by_name=True,
        extra="forbid",
        str_strip_whitespace=True,
    )


class PurchaseOrderReopenResponse(BaseModel):
    """Response returned after reopening a purchase order."""

    id: str = Field(..., description="Purchase order number")
    type: str = Field(default="purchase-order-status", description="Resource type identifier")
    status: str = Field(default="Open", description="Purchase order status after the reopen action")
    details: Dict[str, Any] = Field(default_factory=dict, description="Raw ERP response payload")

    model_config = ConfigDict(extra="ignore")

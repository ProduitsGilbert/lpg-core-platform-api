"""Pydantic schemas for ElekNet EDI-category endpoints."""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ElekNetPriceAvailabilityItemRequest(BaseModel):
    """Single product line for xPA lookup."""

    productCode: str = Field(..., min_length=1)
    qty: int = Field(..., gt=0)

    @field_validator("productCode")
    @classmethod
    def _validate_product_code(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("productCode must not be empty")
        return normalized


class ElekNetPriceAvailabilityRequest(BaseModel):
    """Request payload for ElekNet xPA endpoint."""

    items: list[ElekNetPriceAvailabilityItemRequest] = Field(..., min_length=1, max_length=200)
    productInfo: bool = Field(default=False)


class ElekNetShippingAddress(BaseModel):
    """Optional shipping address block for order submissions."""

    name: str | None = None
    address1: str | None = None
    address2: str | None = None
    city: str | None = None
    state: str | None = None
    postalCode: str | None = None
    country: str | None = None
    phone: str | None = None
    email: str | None = None

    model_config = ConfigDict(extra="allow")


class ElekNetOrderHeader(BaseModel):
    """Order header contract for ElekNet order submission."""

    partner: Literal["Lumen"] = "Lumen"
    type: Literal["Order"] = "Order"
    custno: str = Field(..., min_length=1)
    shipTo: str = Field(..., min_length=1)
    whse: str = Field(..., min_length=1)
    po: str = Field(..., min_length=1)
    delivery: Literal["Y", "N"]
    shipComplete: Literal["Y", "N"]
    shippingDate: date | None = None
    shippingAddress: ElekNetShippingAddress | None = None
    buyer: str | None = None
    contactName: str | None = None
    phone: str | None = None
    email: str | None = None
    comments: str | None = None

    model_config = ConfigDict(extra="allow")


class ElekNetOrderLine(BaseModel):
    """Order line contract for ElekNet order submission."""

    productCode: str = Field(..., min_length=1)
    qty: int = Field(..., gt=0)
    description: str | None = None
    price: float | None = None
    comments: str | None = None
    uom: str | None = None

    model_config = ConfigDict(extra="allow")

    @field_validator("productCode")
    @classmethod
    def _validate_product_code(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("productCode must not be empty")
        return normalized


class ElekNetOrderRequest(BaseModel):
    """Request payload for ElekNet order endpoint."""

    orderHeader: ElekNetOrderHeader
    orderLines: list[ElekNetOrderLine] = Field(..., min_length=1, max_length=500)


class ElekNetStockDetail(BaseModel):
    """Normalized warehouse stock detail."""

    whse: str | None = None
    whseName: str | None = None
    qtyStock: float | None = None


class ElekNetPriceAvailabilityItem(BaseModel):
    """Normalized price/availability item response."""

    status: str | None = None
    productCode: str | None = None
    qty: float | None = None
    unitPrice: float | None = None
    listPrice: float | None = None
    netPrice: float | None = None
    extPrice: float | None = None
    uom: str | None = None
    description: str | None = None
    returnMessage: str | None = None
    stock: list[ElekNetStockDetail] = Field(default_factory=list)
    additionalFields: dict[str, str] = Field(default_factory=dict)


class ElekNetPriceAvailabilityResponse(BaseModel):
    """Normalized xPA response payload."""

    returnCode: str | None = None
    returnMessage: str | None = None
    items: list[ElekNetPriceAvailabilityItem] = Field(default_factory=list)


class ElekNetOrderResponse(BaseModel):
    """Normalized order response payload."""

    returnCode: str | None = None
    po: str | None = None
    orderNumber: str | None = None
    returnMessage: str | None = None

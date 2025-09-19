"""
Pydantic models for OCR document extraction.

These models define the structure of extracted data from various document types.
"""

from typing import List, Optional
from datetime import date
from decimal import Decimal
from pydantic import BaseModel, Field


class PurchaseOrderLine(BaseModel):
    """Model for a purchase order line item."""
    line_number: int = Field(..., description="Line item number")
    item_code: Optional[str] = Field(None, description="Item/SKU code")
    description: str = Field(..., description="Item description")
    quantity: Decimal = Field(..., description="Ordered quantity")
    unit: Optional[str] = Field(None, description="Unit of measure (e.g., EA, KG, M)")
    unit_price: Decimal = Field(..., description="Price per unit")
    line_total: Decimal = Field(..., description="Total amount for this line")
    requested_date: Optional[date] = Field(None, description="Requested delivery date")
    promise_date: Optional[date] = Field(None, description="Promised delivery date")
    notes: Optional[str] = Field(None, description="Additional line notes")


class PurchaseOrderExtraction(BaseModel):
    """Model for extracted purchase order data."""
    po_number: str = Field(..., description="Purchase order number")
    po_date: date = Field(..., description="Purchase order date")
    vendor_name: str = Field(..., description="Vendor/supplier name")
    vendor_id: Optional[str] = Field(None, description="Vendor ID/code")
    vendor_address: Optional[str] = Field(None, description="Vendor address")
    
    buyer_name: Optional[str] = Field(None, description="Buyer company name")
    buyer_contact: Optional[str] = Field(None, description="Buyer contact person")
    buyer_address: Optional[str] = Field(None, description="Buyer/ship-to address")
    
    currency: str = Field(default="USD", description="Currency code")
    subtotal: Decimal = Field(..., description="Subtotal before tax")
    tax_amount: Optional[Decimal] = Field(None, description="Tax amount")
    shipping_cost: Optional[Decimal] = Field(None, description="Shipping/freight cost")
    total_amount: Decimal = Field(..., description="Total PO amount")
    
    payment_terms: Optional[str] = Field(None, description="Payment terms (e.g., Net 30)")
    shipping_terms: Optional[str] = Field(None, description="Shipping terms (e.g., FOB)")
    delivery_instructions: Optional[str] = Field(None, description="Special delivery instructions")
    
    lines: List[PurchaseOrderLine] = Field(..., description="Purchase order line items")
    
    notes: Optional[str] = Field(None, description="Additional PO notes/comments")


class InvoiceLine(BaseModel):
    """Model for an invoice line item."""
    line_number: int = Field(..., description="Line item number")
    item_code: Optional[str] = Field(None, description="Item/SKU code")
    description: str = Field(..., description="Item/service description")
    quantity: Decimal = Field(..., description="Invoiced quantity")
    unit: Optional[str] = Field(None, description="Unit of measure")
    unit_price: Decimal = Field(..., description="Price per unit")
    discount_percent: Optional[Decimal] = Field(None, description="Line discount percentage")
    discount_amount: Optional[Decimal] = Field(None, description="Line discount amount")
    line_total: Decimal = Field(..., description="Total amount for this line")
    tax_code: Optional[str] = Field(None, description="Tax code for this line")
    po_reference: Optional[str] = Field(None, description="Related PO number/line")


class InvoiceExtraction(BaseModel):
    """Model for extracted invoice data."""
    invoice_number: str = Field(..., description="Invoice number")
    invoice_date: date = Field(..., description="Invoice date")
    due_date: Optional[date] = Field(None, description="Payment due date")
    
    vendor_name: str = Field(..., description="Vendor/supplier name")
    vendor_id: Optional[str] = Field(None, description="Vendor ID/code")
    vendor_address: Optional[str] = Field(None, description="Vendor address")
    vendor_tax_id: Optional[str] = Field(None, description="Vendor tax/VAT ID")
    
    customer_name: str = Field(..., description="Customer/bill-to name")
    customer_id: Optional[str] = Field(None, description="Customer ID/account number")
    customer_address: Optional[str] = Field(None, description="Customer billing address")
    customer_tax_id: Optional[str] = Field(None, description="Customer tax/VAT ID")
    
    po_number: Optional[str] = Field(None, description="Related purchase order number")
    
    currency: str = Field(default="USD", description="Currency code")
    subtotal: Decimal = Field(..., description="Subtotal before tax")
    discount_amount: Optional[Decimal] = Field(None, description="Total discount amount")
    tax_rate: Optional[Decimal] = Field(None, description="Tax rate percentage")
    tax_amount: Optional[Decimal] = Field(None, description="Tax amount")
    shipping_cost: Optional[Decimal] = Field(None, description="Shipping/freight cost")
    total_amount: Decimal = Field(..., description="Total invoice amount")
    amount_paid: Optional[Decimal] = Field(None, description="Amount already paid")
    amount_due: Optional[Decimal] = Field(None, description="Outstanding amount")
    
    payment_terms: Optional[str] = Field(None, description="Payment terms")
    payment_method: Optional[str] = Field(None, description="Accepted payment methods")
    bank_details: Optional[str] = Field(None, description="Bank account details for payment")
    
    lines: List[InvoiceLine] = Field(..., description="Invoice line items")
    
    notes: Optional[str] = Field(None, description="Additional invoice notes")


class OCRExtractionRequest(BaseModel):
    """Request model for OCR extraction."""
    document_type: str = Field(..., description="Type of document (purchase_order, invoice, custom)")
    custom_model_name: Optional[str] = Field(None, description="Name of custom model for extraction")
    additional_instructions: Optional[str] = Field(None, description="Additional extraction instructions")


class OCRExtractionResponse(BaseModel):
    """Response model for OCR extraction."""
    success: bool = Field(..., description="Whether extraction was successful")
    document_type: str = Field(..., description="Type of document extracted")
    extracted_data: dict = Field(default_factory=dict, description="Extracted structured data")
    confidence_score: Optional[float] = Field(default=None, description="Extraction confidence score")
    processing_time_ms: Optional[int] = Field(default=None, description="Processing time in milliseconds")
    error_message: Optional[str] = Field(default=None, description="Error message if extraction failed")
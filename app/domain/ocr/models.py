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


class AccountStatementTransaction(BaseModel):
    """Common transaction structure for account statements."""
    transaction_date: date = Field(..., description="Transaction posting date")
    description: str = Field(..., description="Transaction description or memo")
    reference: Optional[str] = Field(None, description="Reference or document number")
    debit: Optional[Decimal] = Field(None, description="Debit amount applied to the account")
    credit: Optional[Decimal] = Field(None, description="Credit amount applied to the account")
    balance: Decimal = Field(..., description="Running balance after the transaction")
    currency: Optional[str] = Field(None, description="Currency code for the transaction")


class SupplierAccountStatementExtraction(BaseModel):
    """Model for supplier account statement data."""
    supplier_name: str = Field(..., description="Supplier or vendor name")
    supplier_id: Optional[str] = Field(None, description="Internal supplier identifier")
    account_number: Optional[str] = Field(None, description="Supplier account number")
    statement_number: Optional[str] = Field(None, description="Statement identifier or reference")
    statement_period_start: date = Field(..., description="Statement period start date")
    statement_period_end: date = Field(..., description="Statement period end date")
    currency: str = Field(default="USD", description="Currency used for the statement")
    opening_balance: Decimal = Field(..., description="Balance at the start of the period")
    total_debits: Decimal = Field(..., description="Total debits during the period")
    total_credits: Decimal = Field(..., description="Total credits during the period")
    closing_balance: Decimal = Field(..., description="Balance at the end of the period")
    statement_date: Optional[date] = Field(None, description="Date the statement was issued")
    contact_information: Optional[str] = Field(None, description="Supplier contact details")
    transactions: List[AccountStatementTransaction] = Field(
        ..., description="List of transactions appearing on the statement"
    )
    notes: Optional[str] = Field(None, description="Additional remarks or footnotes from the supplier")


class CustomerAccountStatementExtraction(BaseModel):
    """Model for customer account statement data."""
    customer_name: str = Field(..., description="Customer or account holder name")
    customer_id: Optional[str] = Field(None, description="Internal customer identifier")
    account_number: Optional[str] = Field(None, description="Customer account number")
    statement_number: Optional[str] = Field(None, description="Statement identifier or reference")
    statement_period_start: date = Field(..., description="Statement period start date")
    statement_period_end: date = Field(..., description="Statement period end date")
    currency: str = Field(default="USD", description="Currency used for the statement")
    opening_balance: Decimal = Field(..., description="Balance at the beginning of the period")
    total_charges: Decimal = Field(..., description="Total charges or invoices during the period")
    total_payments: Decimal = Field(..., description="Total payments or credits during the period")
    closing_balance: Decimal = Field(..., description="Balance outstanding at the end of the period")
    statement_date: Optional[date] = Field(None, description="Date the statement was issued")
    credit_limit: Optional[Decimal] = Field(None, description="Customer credit limit if applicable")
    transactions: List[AccountStatementTransaction] = Field(
        ..., description="List of transactions affecting the account balance"
    )
    notes: Optional[str] = Field(None, description="Additional remarks or payment instructions")


class SupplierInvoiceExtraction(InvoiceExtraction):
    """Model for supplier invoice data with AP specific fields."""
    receipt_reference: Optional[str] = Field(None, description="Goods receipt or delivery note reference")
    supplier_contact: Optional[str] = Field(None, description="Primary supplier contact details")
    payment_reference: Optional[str] = Field(None, description="Supplier payment reference or remittance info")
    approval_status: Optional[str] = Field(None, description="Internal approval status or workflow state")


class ShippingBillItem(BaseModel):
    """Individual line item from a shipping bill."""
    line_number: int = Field(..., description="Sequential line number")
    description: str = Field(..., description="Goods description")
    hs_code: Optional[str] = Field(None, description="Harmonized system code")
    quantity: Decimal = Field(..., description="Quantity shipped")
    unit_of_measure: Optional[str] = Field(None, description="Unit of measure for quantity")
    gross_weight: Optional[Decimal] = Field(None, description="Gross weight for the line")
    net_weight: Optional[Decimal] = Field(None, description="Net weight for the line")
    customs_value: Decimal = Field(..., description="Customs value for the line")
    currency: str = Field(default="USD", description="Currency code for the customs value")
    country_of_origin: Optional[str] = Field(None, description="Country where the goods originated")


class ShippingBillExtraction(BaseModel):
    """Model for shipping bill (bill of entry/export) data."""
    bill_number: str = Field(..., description="Shipping bill number")
    bill_date: date = Field(..., description="Date of the shipping bill")
    exporter_name: str = Field(..., description="Exporter or consignor name")
    exporter_tax_id: Optional[str] = Field(None, description="Exporter tax/VAT identification number")
    consignee_name: str = Field(..., description="Consignee or importer name")
    consignee_address: Optional[str] = Field(None, description="Consignee address")
    port_of_loading: Optional[str] = Field(None, description="Port where goods were loaded")
    port_of_discharge: Optional[str] = Field(None, description="Destination port")
    vessel_name: Optional[str] = Field(None, description="Vessel or flight name/number")
    voyage_number: Optional[str] = Field(None, description="Voyage or flight number")
    incoterm: Optional[str] = Field(None, description="Applicable Incoterm")
    currency: str = Field(default="USD", description="Currency used in declaration")
    total_customs_value: Decimal = Field(..., description="Total customs value of goods")
    total_packages: Optional[int] = Field(None, description="Number of packages")
    total_gross_weight: Optional[Decimal] = Field(None, description="Total gross weight")
    total_net_weight: Optional[Decimal] = Field(None, description="Total net weight")
    line_items: List[ShippingBillItem] = Field(..., description="Declared shipping bill line items")
    remarks: Optional[str] = Field(None, description="Additional remarks or declarations")


class CommercialInvoiceItem(BaseModel):
    """Line item extracted from a commercial invoice."""
    line_number: int = Field(..., description="Sequential line number")
    description: str = Field(..., description="Description of goods/services")
    hs_code: Optional[str] = Field(None, description="Harmonized system or tariff code")
    quantity: Decimal = Field(..., description="Quantity shipped or invoiced")
    unit_of_measure: Optional[str] = Field(None, description="Unit of measure for quantity")
    unit_price: Decimal = Field(..., description="Unit price")
    total_price: Decimal = Field(..., description="Extended price (quantity x unit price)")
    origin_country: Optional[str] = Field(None, description="Country of origin")
    destination_country: Optional[str] = Field(None, description="Destination country")


class CommercialInvoiceExtraction(BaseModel):
    """Model for commercial invoice (export) data."""
    invoice_number: str = Field(..., description="Commercial invoice number")
    invoice_date: date = Field(..., description="Commercial invoice date")
    exporter_name: str = Field(..., description="Exporter or seller name")
    exporter_address: Optional[str] = Field(None, description="Exporter address")
    exporter_tax_id: Optional[str] = Field(None, description="Exporter tax or registration ID")
    importer_name: str = Field(..., description="Importer or buyer name")
    importer_address: Optional[str] = Field(None, description="Importer address")
    importer_tax_id: Optional[str] = Field(None, description="Importer tax or registration ID")
    consignee_name: Optional[str] = Field(None, description="Consignee name if different from importer")
    incoterm: Optional[str] = Field(None, description="Incoterm governing the sale")
    payment_terms: Optional[str] = Field(None, description="Payment terms")
    currency: str = Field(default="USD", description="Currency of the invoice")
    total_invoice_value: Decimal = Field(..., description="Total invoice value")
    freight_cost: Optional[Decimal] = Field(None, description="Freight or shipping cost")
    insurance_cost: Optional[Decimal] = Field(None, description="Insurance cost")
    port_of_loading: Optional[str] = Field(None, description="Port or location of loading")
    port_of_discharge: Optional[str] = Field(None, description="Port or location of discharge")
    country_of_origin: Optional[str] = Field(None, description="Country where goods originated")
    country_of_destination: Optional[str] = Field(None, description="Final destination country")
    line_items: List[CommercialInvoiceItem] = Field(..., description="Line items included in the commercial invoice")
    additional_documents: Optional[str] = Field(None, description="References to packing lists, certificates, etc.")
    remarks: Optional[str] = Field(None, description="Additional notes or regulatory statements")


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

"""
OCR Document Type Definitions
Comprehensive document type definitions with specific field mappings for OCR processing
"""

from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class DocumentCategory(str, Enum):
    """High-level document categories"""
    INVOICE = "invoice"
    SHIPPING = "shipping"
    CUSTOMS = "customs"
    QUALITY = "quality"
    FINANCIAL = "financial"
    LEGAL = "legal"


class InvoiceType(str, Enum):
    """Specific invoice document types"""
    SALES_ORDER_INVOICE = "sales_order_invoice"
    SUPPLIER_INVOICE = "supplier_invoice"
    SHIPPING_INVOICE = "shipping_invoice"
    COMMERCIAL_INVOICE = "commercial_invoice"
    PROFORMA_INVOICE = "proforma_invoice"
    CREDIT_NOTE = "credit_note"
    DEBIT_NOTE = "debit_note"


class ShippingDocumentType(str, Enum):
    """Shipping-related document types"""
    PACKING_SLIP = "packing_slip"
    BILL_OF_LADING = "bill_of_lading"
    AIR_WAYBILL = "air_waybill"
    DELIVERY_NOTE = "delivery_note"
    SHIPPING_MANIFEST = "shipping_manifest"


class CustomsDocumentType(str, Enum):
    """Customs and border-related document types"""
    BORDER_DECLARATION = "border_declaration"
    CUSTOMS_DECLARATION = "customs_declaration"
    CERTIFICATE_OF_ORIGIN = "certificate_of_origin"
    IMPORT_PERMIT = "import_permit"
    EXPORT_PERMIT = "export_permit"


class FieldDefinition(BaseModel):
    """Definition of a field to extract from document"""
    name: str
    description: str
    data_type: str  # string, number, date, boolean, array
    required: bool = False
    validation_pattern: Optional[str] = None
    aliases: List[str] = Field(default_factory=list)
    extraction_hints: List[str] = Field(default_factory=list)


class DocumentTypeDefinition(BaseModel):
    """Complete definition of a document type"""
    type_id: str
    category: DocumentCategory
    name: str
    description: str
    identifying_keywords: List[str]
    required_fields: List[FieldDefinition]
    optional_fields: List[FieldDefinition]
    validation_rules: Dict[str, Any] = Field(default_factory=dict)
    extraction_confidence_threshold: float = 0.85


# Sales Order Invoice Definition
SALES_ORDER_INVOICE = DocumentTypeDefinition(
    type_id="sales_order_invoice",
    category=DocumentCategory.INVOICE,
    name="Sales Order Invoice",
    description="Invoice issued to customer for goods/services sold",
    identifying_keywords=[
        "sales invoice", "customer invoice", "tax invoice", 
        "invoice to", "bill to", "sold to"
    ],
    required_fields=[
        FieldDefinition(
            name="invoice_number",
            description="Unique invoice identifier",
            data_type="string",
            required=True,
            aliases=["invoice no", "invoice #", "inv no", "document number"],
            extraction_hints=["Usually alphanumeric", "Top right of document"]
        ),
        FieldDefinition(
            name="invoice_date",
            description="Date invoice was issued",
            data_type="date",
            required=True,
            aliases=["date", "invoice dt", "document date"],
            validation_pattern=r"\d{2,4}[-/]\d{1,2}[-/]\d{2,4}"
        ),
        FieldDefinition(
            name="customer_name",
            description="Customer or buyer name",
            data_type="string",
            required=True,
            aliases=["bill to", "sold to", "customer", "buyer"],
            extraction_hints=["Usually in top left or center"]
        ),
        FieldDefinition(
            name="total_amount",
            description="Total invoice amount including tax",
            data_type="number",
            required=True,
            aliases=["grand total", "amount due", "total", "balance due"],
            extraction_hints=["Bottom of invoice", "Largest amount on document"]
        ),
        FieldDefinition(
            name="line_items",
            description="Individual items/services on invoice",
            data_type="array",
            required=True,
            extraction_hints=["Table format in middle of document"]
        )
    ],
    optional_fields=[
        FieldDefinition(
            name="po_number",
            description="Customer's purchase order reference",
            data_type="string",
            aliases=["po no", "po #", "purchase order", "customer po"]
        ),
        FieldDefinition(
            name="sales_order_number",
            description="Internal sales order reference",
            data_type="string",
            aliases=["so no", "so #", "order number", "order ref"]
        ),
        FieldDefinition(
            name="customer_id",
            description="Customer account number",
            data_type="string",
            aliases=["account no", "customer code", "customer ref"]
        ),
        FieldDefinition(
            name="payment_terms",
            description="Payment terms and conditions",
            data_type="string",
            aliases=["terms", "payment due", "net terms"]
        ),
        FieldDefinition(
            name="tax_amount",
            description="Total tax amount",
            data_type="number",
            aliases=["gst", "vat", "sales tax", "tax"]
        ),
        FieldDefinition(
            name="shipping_address",
            description="Delivery address",
            data_type="string",
            aliases=["ship to", "deliver to", "delivery address"]
        )
    ],
    validation_rules={
        "total_validation": "sum(line_items.amount) + tax_amount == total_amount",
        "date_validation": "invoice_date <= current_date"
    }
)

# Supplier Invoice Definition
SUPPLIER_INVOICE = DocumentTypeDefinition(
    type_id="supplier_invoice",
    category=DocumentCategory.INVOICE,
    name="Supplier Invoice",
    description="Invoice received from supplier/vendor for purchases",
    identifying_keywords=[
        "vendor invoice", "supplier invoice", "purchase invoice",
        "from vendor", "accounts payable", "remit to"
    ],
    required_fields=[
        FieldDefinition(
            name="vendor_invoice_number",
            description="Vendor's invoice number",
            data_type="string",
            required=True,
            aliases=["invoice no", "vendor inv #", "supplier invoice no"]
        ),
        FieldDefinition(
            name="vendor_name",
            description="Supplier/vendor company name",
            data_type="string",
            required=True,
            aliases=["from", "vendor", "supplier", "seller", "remit to"]
        ),
        FieldDefinition(
            name="invoice_date",
            description="Date of vendor invoice",
            data_type="date",
            required=True,
            aliases=["date", "invoice date", "document date"]
        ),
        FieldDefinition(
            name="total_amount",
            description="Total amount to be paid",
            data_type="number",
            required=True,
            aliases=["amount due", "total", "balance", "invoice total"]
        ),
        FieldDefinition(
            name="our_po_number",
            description="Our purchase order reference",
            data_type="string",
            required=True,
            aliases=["po number", "purchase order", "your po", "customer po"]
        )
    ],
    optional_fields=[
        FieldDefinition(
            name="vendor_id",
            description="Vendor account or ID number",
            data_type="string",
            aliases=["vendor no", "supplier code", "vendor ref"]
        ),
        FieldDefinition(
            name="payment_due_date",
            description="Date payment is due",
            data_type="date",
            aliases=["due date", "payment due", "pay by"]
        ),
        FieldDefinition(
            name="bank_details",
            description="Banking information for payment",
            data_type="string",
            aliases=["bank account", "remittance info", "wire instructions"]
        ),
        FieldDefinition(
            name="tax_id",
            description="Vendor tax identification",
            data_type="string",
            aliases=["tax no", "ein", "vat no", "gst no"]
        )
    ]
)

# Shipping Invoice Definition
SHIPPING_INVOICE = DocumentTypeDefinition(
    type_id="shipping_invoice",
    category=DocumentCategory.INVOICE,
    name="Shipping Invoice",
    description="Invoice for shipping/freight charges",
    identifying_keywords=[
        "freight invoice", "shipping invoice", "carrier invoice",
        "transport charges", "freight charges", "shipping charges"
    ],
    required_fields=[
        FieldDefinition(
            name="carrier_name",
            description="Shipping company name",
            data_type="string",
            required=True,
            aliases=["carrier", "shipper", "transport company"]
        ),
        FieldDefinition(
            name="tracking_number",
            description="Shipment tracking number",
            data_type="string",
            required=True,
            aliases=["tracking no", "waybill no", "pro number", "reference no"]
        ),
        FieldDefinition(
            name="shipment_date",
            description="Date of shipment",
            data_type="date",
            required=True,
            aliases=["ship date", "pickup date", "dispatch date"]
        ),
        FieldDefinition(
            name="freight_charges",
            description="Total shipping charges",
            data_type="number",
            required=True,
            aliases=["shipping cost", "freight cost", "transport charges"]
        ),
        FieldDefinition(
            name="origin",
            description="Shipment origin location",
            data_type="string",
            required=True,
            aliases=["from", "pickup location", "ship from"]
        ),
        FieldDefinition(
            name="destination",
            description="Shipment destination",
            data_type="string",
            required=True,
            aliases=["to", "deliver to", "ship to", "delivery location"]
        )
    ],
    optional_fields=[
        FieldDefinition(
            name="weight",
            description="Shipment weight",
            data_type="string",
            aliases=["gross weight", "total weight", "weight"]
        ),
        FieldDefinition(
            name="service_type",
            description="Type of shipping service",
            data_type="string",
            aliases=["service", "shipping method", "delivery type"]
        ),
        FieldDefinition(
            name="fuel_surcharge",
            description="Fuel surcharge amount",
            data_type="number",
            aliases=["fuel charge", "fuel adjustment"]
        ),
        FieldDefinition(
            name="accessorial_charges",
            description="Additional service charges",
            data_type="number",
            aliases=["additional charges", "extra charges", "special services"]
        )
    ]
)

# Commercial Invoice Definition
COMMERCIAL_INVOICE = DocumentTypeDefinition(
    type_id="commercial_invoice",
    category=DocumentCategory.INVOICE,
    name="Commercial Invoice",
    description="Invoice for international trade/customs purposes",
    identifying_keywords=[
        "commercial invoice", "export invoice", "customs invoice",
        "international invoice", "trade invoice"
    ],
    required_fields=[
        FieldDefinition(
            name="invoice_number",
            description="Commercial invoice number",
            data_type="string",
            required=True,
            aliases=["invoice no", "document no", "reference no"]
        ),
        FieldDefinition(
            name="exporter_name",
            description="Exporter/seller company name",
            data_type="string",
            required=True,
            aliases=["seller", "vendor", "shipper", "exporter"]
        ),
        FieldDefinition(
            name="importer_name",
            description="Importer/buyer company name",
            data_type="string",
            required=True,
            aliases=["buyer", "consignee", "importer", "bill to"]
        ),
        FieldDefinition(
            name="country_of_origin",
            description="Country where goods originated",
            data_type="string",
            required=True,
            aliases=["origin", "made in", "country of manufacture"]
        ),
        FieldDefinition(
            name="country_of_destination",
            description="Final destination country",
            data_type="string",
            required=True,
            aliases=["destination", "ship to country", "final destination"]
        ),
        FieldDefinition(
            name="incoterms",
            description="International commercial terms",
            data_type="string",
            required=True,
            aliases=["terms of sale", "delivery terms", "trade terms"]
        ),
        FieldDefinition(
            name="total_value",
            description="Total commercial value",
            data_type="number",
            required=True,
            aliases=["invoice total", "total amount", "commercial value"]
        ),
        FieldDefinition(
            name="currency",
            description="Currency of transaction",
            data_type="string",
            required=True,
            aliases=["currency code", "ccy"]
        )
    ],
    optional_fields=[
        FieldDefinition(
            name="hs_codes",
            description="Harmonized system codes",
            data_type="array",
            aliases=["tariff codes", "commodity codes", "hs classification"]
        ),
        FieldDefinition(
            name="export_license",
            description="Export license number",
            data_type="string",
            aliases=["license no", "export permit", "authorization no"]
        ),
        FieldDefinition(
            name="terms_of_payment",
            description="Payment terms",
            data_type="string",
            aliases=["payment terms", "payment method"]
        )
    ]
)

# Packing Slip Definition
PACKING_SLIP = DocumentTypeDefinition(
    type_id="packing_slip",
    category=DocumentCategory.SHIPPING,
    name="Packing Slip",
    description="Document listing items included in shipment",
    identifying_keywords=[
        "packing slip", "packing list", "shipping list",
        "delivery note", "pick ticket", "contents list"
    ],
    required_fields=[
        FieldDefinition(
            name="packing_slip_number",
            description="Unique packing slip identifier",
            data_type="string",
            required=True,
            aliases=["slip no", "document no", "reference no"]
        ),
        FieldDefinition(
            name="ship_date",
            description="Date of shipment",
            data_type="date",
            required=True,
            aliases=["date shipped", "dispatch date", "date"]
        ),
        FieldDefinition(
            name="ship_to_name",
            description="Recipient name",
            data_type="string",
            required=True,
            aliases=["deliver to", "consignee", "recipient"]
        ),
        FieldDefinition(
            name="ship_to_address",
            description="Delivery address",
            data_type="string",
            required=True,
            aliases=["delivery address", "shipping address", "destination"]
        ),
        FieldDefinition(
            name="items",
            description="List of items in shipment",
            data_type="array",
            required=True,
            extraction_hints=["Table with item numbers, descriptions, quantities"]
        )
    ],
    optional_fields=[
        FieldDefinition(
            name="order_number",
            description="Related order number",
            data_type="string",
            aliases=["po number", "sales order", "reference"]
        ),
        FieldDefinition(
            name="tracking_number",
            description="Shipment tracking number",
            data_type="string",
            aliases=["tracking no", "waybill", "pro number"]
        ),
        FieldDefinition(
            name="carrier",
            description="Shipping carrier name",
            data_type="string",
            aliases=["shipped via", "carrier", "transport company"]
        ),
        FieldDefinition(
            name="number_of_boxes",
            description="Total number of packages",
            data_type="number",
            aliases=["packages", "cartons", "boxes", "pieces"]
        ),
        FieldDefinition(
            name="total_weight",
            description="Total shipment weight",
            data_type="string",
            aliases=["gross weight", "weight", "total wt"]
        ),
        FieldDefinition(
            name="special_instructions",
            description="Special handling instructions",
            data_type="string",
            aliases=["notes", "instructions", "comments"]
        )
    ]
)

# Border Declaration Definition
BORDER_DECLARATION = DocumentTypeDefinition(
    type_id="border_declaration",
    category=DocumentCategory.CUSTOMS,
    name="Border Declaration",
    description="Customs declaration for cross-border shipments",
    identifying_keywords=[
        "border declaration", "customs declaration", "import declaration",
        "export declaration", "entry summary", "customs entry"
    ],
    required_fields=[
        FieldDefinition(
            name="declaration_number",
            description="Unique declaration identifier",
            data_type="string",
            required=True,
            aliases=["entry no", "declaration no", "reference no", "b3 number"]
        ),
        FieldDefinition(
            name="declaration_date",
            description="Date of declaration",
            data_type="date",
            required=True,
            aliases=["date", "entry date", "filing date"]
        ),
        FieldDefinition(
            name="importer_name",
            description="Importer of record",
            data_type="string",
            required=True,
            aliases=["importer", "consignee", "buyer", "importer of record"]
        ),
        FieldDefinition(
            name="exporter_name",
            description="Exporter/shipper name",
            data_type="string",
            required=True,
            aliases=["exporter", "shipper", "seller", "vendor"]
        ),
        FieldDefinition(
            name="country_of_origin",
            description="Country where goods originated",
            data_type="string",
            required=True,
            aliases=["origin", "country of manufacture", "made in"]
        ),
        FieldDefinition(
            name="port_of_entry",
            description="Port where goods enter country",
            data_type="string",
            required=True,
            aliases=["port", "entry port", "port of arrival", "port code"]
        ),
        FieldDefinition(
            name="total_value",
            description="Total declared value",
            data_type="number",
            required=True,
            aliases=["customs value", "declared value", "invoice value"]
        ),
        FieldDefinition(
            name="hs_codes",
            description="Harmonized system classification codes",
            data_type="array",
            required=True,
            aliases=["tariff codes", "commodity codes", "classification"]
        )
    ],
    optional_fields=[
        FieldDefinition(
            name="duties",
            description="Customs duties amount",
            data_type="number",
            aliases=["duty", "customs duty", "import duty"]
        ),
        FieldDefinition(
            name="taxes",
            description="Import taxes amount",
            data_type="number",
            aliases=["import tax", "vat", "gst", "sales tax"]
        ),
        FieldDefinition(
            name="broker_name",
            description="Customs broker name",
            data_type="string",
            aliases=["broker", "agent", "customs broker"]
        ),
        FieldDefinition(
            name="transport_document",
            description="Bill of lading or air waybill number",
            data_type="string",
            aliases=["bol", "awb", "transport doc", "shipping document"]
        ),
        FieldDefinition(
            name="container_numbers",
            description="Container identification numbers",
            data_type="array",
            aliases=["containers", "container no", "equipment no"]
        ),
        FieldDefinition(
            name="commercial_invoice_ref",
            description="Related commercial invoice number",
            data_type="string",
            aliases=["invoice no", "commercial invoice", "invoice ref"]
        )
    ],
    validation_rules={
        "value_validation": "total_value >= sum(line_items.value)",
        "duty_calculation": "duties == sum(line_items.duty_amount)"
    }
)

# Document Type Registry
DOCUMENT_TYPES: Dict[str, DocumentTypeDefinition] = {
    "sales_order_invoice": SALES_ORDER_INVOICE,
    "supplier_invoice": SUPPLIER_INVOICE,
    "shipping_invoice": SHIPPING_INVOICE,
    "commercial_invoice": COMMERCIAL_INVOICE,
    "packing_slip": PACKING_SLIP,
    "border_declaration": BORDER_DECLARATION
}


class DocumentClassifier:
    """Classify documents based on content analysis"""
    
    @staticmethod
    def identify_document_type(text: str, confidence_threshold: float = 0.7) -> Optional[str]:
        """
        Identify document type from extracted text
        
        Args:
            text: Extracted text from document
            confidence_threshold: Minimum confidence score required
            
        Returns:
            Document type ID if identified with sufficient confidence
        """
        text_lower = text.lower()
        scores = {}
        
        for type_id, definition in DOCUMENT_TYPES.items():
            score = 0
            keyword_matches = 0
            
            # Check for identifying keywords
            for keyword in definition.identifying_keywords:
                if keyword.lower() in text_lower:
                    keyword_matches += 1
            
            if keyword_matches > 0:
                score = keyword_matches / len(definition.identifying_keywords)
                scores[type_id] = score
        
        if scores:
            best_match = max(scores, key=scores.get)
            if scores[best_match] >= confidence_threshold:
                return best_match
        
        return None
    
    @staticmethod
    def get_extraction_template(document_type: str) -> Dict[str, List[str]]:
        """
        Get field extraction template for a document type
        
        Args:
            document_type: Document type ID
            
        Returns:
            Dictionary of field names to extract with their aliases
        """
        if document_type not in DOCUMENT_TYPES:
            return {}
        
        definition = DOCUMENT_TYPES[document_type]
        template = {}
        
        for field in definition.required_fields + definition.optional_fields:
            template[field.name] = [field.name] + field.aliases
        
        return template
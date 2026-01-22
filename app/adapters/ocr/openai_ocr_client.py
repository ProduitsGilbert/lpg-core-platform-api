"""
OpenAI-based OCR client for document extraction.

This adapter uses OpenAI's GPT models with structured output to extract
data from PDF and image documents.
"""

import io
from typing import Dict, Any, Type, Optional
import time
import logfire
from openai import OpenAI
from pydantic import BaseModel

from app.ports import OCRClientProtocol
from app.domain.ocr.models import (
    PurchaseOrderExtraction,
    InvoiceExtraction,
    SupplierAccountStatementExtraction,
    CustomerAccountStatementExtraction,
    SupplierInvoiceExtraction,
    ShippingBillExtraction,
    CommercialInvoiceExtraction,
    ComplexDocumentExtraction
)


class OpenAIOCRClient(OCRClientProtocol):
    """
    OpenAI implementation of OCR client.
    
    Uses OpenAI's GPT models with structured output parsing
    to extract data from corporate documents.
    """
    
    def __init__(self, api_key: str, model: str = "gpt-4.1-mini"):
        """
        Initialize OpenAI OCR client.
        
        Args:
            api_key: OpenAI API key
            model: Model to use for extraction (default: gpt-4.1-mini)
        """
        self.client = OpenAI(api_key=api_key) if api_key else None
        self.model = model
        self._enabled = bool(api_key)
        logfire.info(f"OpenAI OCR client initialized with model: {model}")
    
    @property
    def enabled(self) -> bool:
        """Whether the OCR client is enabled and available."""
        return self._enabled

    def _upload_document(self, file_content: bytes, filename: str):
        """Upload a document for vision processing."""
        file_buffer = io.BytesIO(file_content)
        file_buffer.name = filename
        return self.client.files.create(
            file=file_buffer,
            purpose="assistants"
        )

    def _cleanup_document(self, file_id: str) -> None:
        """Attempt to delete an uploaded document; log failures only."""
        try:
            self.client.files.delete(file_id)
        except Exception as exc:  # pragma: no cover - cleanup is best effort
            logfire.warn(f'Failed to delete uploaded file {file_id}: {exc}')

    def _extract_with_vision(
        self,
        file_content: bytes,
        filename: str,
        document_category: str,
        system_prompt: str,
        user_prompt: str,
        response_model: Type[BaseModel]
    ) -> BaseModel:
        """Shared helper that sends the document to a vision-capable model."""
        if not self.enabled:
            raise ValueError("OpenAI client is not enabled")

        logfire.info(f'Uploading {document_category} file {filename} for vision OCR')
        uploaded_file = self._upload_document(file_content, filename)

        try:
            logfire.info(f'File uploaded with ID: {uploaded_file.id}')
            is_pdf = file_content[:4] == b"%PDF" or filename.lower().endswith(".pdf")

            if is_pdf:
                file_input = {
                    "type": "input_file",
                    "file_id": uploaded_file.id,
                }
            else:
                file_input = {
                    "type": "input_image",
                    "image": {
                        "file_id": uploaded_file.id,
                        "detail": "high",
                    },
                }

            response = self.client.responses.parse(
                model=self.model,
                input=[
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "input_text",
                                "text": user_prompt
                            },
                            file_input
                        ]
                    }
                ],
                text_format=response_model
            )

            return response.output_parsed

        finally:
            self._cleanup_document(uploaded_file.id)

    def _extract_with_text(
        self,
        document_category: str,
        system_prompt: str,
        user_prompt: str,
        response_model: Type[BaseModel],
    ) -> BaseModel:
        """Shared helper that parses extracted document text (no vision/file upload)."""
        if not self.enabled:
            raise ValueError("OpenAI client is not enabled")

        response = self.client.responses.parse(
            model=self.model,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            text_format=response_model,
        )
        return response.output_parsed

    def extract_purchase_order(
        self,
        file_content: bytes,
        filename: str
    ) -> Dict[str, Any]:
        """
        Extract structured data from a Purchase Order document.
        
        Args:
            file_content: Binary content of the PDF/image file
            filename: Name of the file
            
        Returns:
            Structured PO data including header and lines
        """
        with logfire.span('openai_extract_purchase_order'):
            start_time = time.time()
            
            try:
                po_data = self._extract_with_vision(
                    file_content=file_content,
                    filename=filename,
                    document_category="purchase_order",
                    system_prompt="""You are an expert at extracting structured data from Purchase Order documents.
                    Extract ALL information from the document including:
                    - PO header information (number, date, vendor details, buyer details)
                    - All line items with complete details (quantities, prices, dates)
                    - Payment and shipping terms
                    - Any special instructions or notes
                    Ensure all monetary amounts and quantities are accurately extracted as numbers.
                    For dates, use ISO format (YYYY-MM-DD).""",
                    user_prompt="Extract all purchase order information from this document. Include every line item with all details.",
                    response_model=PurchaseOrderExtraction
                )

                processing_time = int((time.time() - start_time) * 1000)
                logfire.info(f'Successfully extracted PO data in {processing_time}ms')
                
                # Convert to dict and add metadata
                result = po_data.model_dump()
                result["document_category"] = "purchase_order"
                result["confidence_score"] = 0.95  # OpenAI typically has high confidence
                result["processing_time_ms"] = processing_time
                
                return result
                
            except Exception as e:
                logfire.error(f'Failed to extract PO from {filename}: {str(e)}')
                raise
    
    def extract_invoice(
        self,
        file_content: bytes,
        filename: str
    ) -> Dict[str, Any]:
        """
        Extract structured data from an Invoice document.
        
        Args:
            file_content: Binary content of the PDF/image file
            filename: Name of the file
            
        Returns:
            Structured invoice data including header and lines
        """
        with logfire.span('openai_extract_invoice'):
            start_time = time.time()
            
            try:
                invoice_data = self._extract_with_vision(
                    file_content=file_content,
                    filename=filename,
                    document_category="invoice",
                    system_prompt="""You are an expert at extracting structured data from Invoice documents.
                    Extract ALL information from the document including:
                    - Invoice header (number, date, due date)
                    - Vendor/supplier information (name, address, tax ID)
                    - Customer/bill-to information
                    - All line items with complete details (descriptions, quantities, prices, discounts)
                    - Tax calculations and totals
                    - Payment terms and bank details
                    - Any reference to related Purchase Orders
                    Ensure all monetary amounts are accurately extracted as numbers.
                    For dates, use ISO format (YYYY-MM-DD).""",
                    user_prompt="Extract all invoice information from this document. Include every line item with all details, tax information, and payment terms.",
                    response_model=InvoiceExtraction
                )

                processing_time = int((time.time() - start_time) * 1000)
                logfire.info(f'Successfully extracted invoice data in {processing_time}ms')
                
                # Convert to dict and add metadata
                result = invoice_data.model_dump()
                result["document_category"] = "invoice"
                result["confidence_score"] = 0.95  # OpenAI typically has high confidence
                result["processing_time_ms"] = processing_time
                
                return result
                
            except Exception as e:
                logfire.error(f'Failed to extract invoice from {filename}: {str(e)}')
                raise
    
    def extract_generic_document(
        self,
        file_content: bytes,
        filename: str,
        document_type: str,
        output_model: Type[BaseModel]
    ) -> BaseModel:
        """
        Extract structured data from any document type using a custom model.
        
        Args:
            file_content: Binary content of the PDF/image file
            filename: Name of the file
            document_type: Type of document for prompt customization
            output_model: Pydantic model class defining expected output structure
            
        Returns:
            Extracted data in the specified model format
        """
        with logfire.span('openai_extract_generic_document'):
            start_time = time.time()
            
            try:
                field_descriptions = []
                for field_name, field_info in output_model.model_fields.items():
                    desc = field_info.description or field_name.replace("_", " ").title()
                    field_descriptions.append(f"- {desc}")

                fields_prompt = "\n".join(field_descriptions)

                extracted_data = self._extract_with_vision(
                    file_content=file_content,
                    filename=filename,
                    document_category=document_type,
                    system_prompt=f"""You are an expert at extracting structured data from {document_type} documents.
                    Extract ALL information from the document that matches these fields:
                    {fields_prompt}

                    Ensure all data is accurately extracted and properly formatted.
                    For dates, use ISO format (YYYY-MM-DD).
                    For monetary amounts, extract as decimal numbers without currency symbols.""",
                    user_prompt=f"Extract all relevant information from this {document_type} document according to the specified structure.",
                    response_model=output_model
                )

                processing_time = int((time.time() - start_time) * 1000)
                logfire.info(f'Successfully extracted {document_type} data in {processing_time}ms')
                
                # Add metadata if model supports it
                if hasattr(extracted_data, "confidence_score"):
                    extracted_data.confidence_score = 0.95
                if hasattr(extracted_data, "processing_time_ms"):
                    extracted_data.processing_time_ms = processing_time
                if hasattr(extracted_data, "document_category"):
                    extracted_data.document_category = document_type
                return extracted_data
                
            except Exception as e:
                logfire.error(f'Failed to extract {document_type} from {filename}: {str(e)}')
                raise

    def extract_generic_text(
        self,
        document_text: str,
        document_type: str,
        output_model: Type[BaseModel]
    ) -> BaseModel:
        """
        Extract structured data from plain text using a custom model.

        This is used as a fallback for large PDFs where uploading the whole document
        for vision processing would be inefficient or exceed provider limits.
        """
        with logfire.span('openai_extract_generic_text'):
            start_time = time.time()

            if not document_text or not document_text.strip():
                raise ValueError("document_text is empty")

            try:
                field_descriptions = []
                for field_name, field_info in output_model.model_fields.items():
                    desc = field_info.description or field_name.replace("_", " ").title()
                    field_descriptions.append(f"- {desc}")

                fields_prompt = "\n".join(field_descriptions)

                extracted_data = self._extract_with_text(
                    document_category=document_type,
                    system_prompt=f"""You are an expert at extracting structured data from {document_type} documents.
Extract ALL information from the provided text that matches these fields:
{fields_prompt}

Guidelines:
- Only use information that is present in the text.
- Preserve the exact meaning of payment terms and timing.
- For monetary amounts, extract decimal numbers without currency symbols.
- For percent values, use numbers from 0 to 100.
- If currency is present, return ISO 4217 codes (e.g., USD, CAD, EUR).""",
                    user_prompt=f"""Extract the required structured data from this document text:

--- BEGIN DOCUMENT TEXT ---
{document_text}
--- END DOCUMENT TEXT ---""",
                    response_model=output_model
                )

                processing_time = int((time.time() - start_time) * 1000)
                logfire.info(f'Successfully extracted {document_type} data from text in {processing_time}ms')

                # Add metadata if model supports it
                if hasattr(extracted_data, "confidence_score"):
                    extracted_data.confidence_score = 0.9
                if hasattr(extracted_data, "processing_time_ms"):
                    extracted_data.processing_time_ms = processing_time
                if hasattr(extracted_data, "document_category"):
                    extracted_data.document_category = document_type

                return extracted_data

            except Exception as e:
                logfire.error(f'Failed to extract {document_type} from text: {str(e)}')
                raise

    def extract_supplier_account_statement(
        self,
        file_content: bytes,
        filename: str,
        additional_instructions: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Extract structured data from a supplier account statement document."""
        with logfire.span('openai_extract_supplier_account_statement'):
            start_time = time.time()

            try:
                extra = ""
                if additional_instructions and additional_instructions.strip():
                    extra = f"\n\nAdditional instructions:\n{additional_instructions.strip()}"
                statement_data = self._extract_with_vision(
                    file_content=file_content,
                    filename=filename,
                    document_category="supplier_account_statement",
                    system_prompt="""You are an expert at extracting structured data from supplier account statements.
                    Capture the supplier identifiers, statement period, opening/closing balances, totals, and every transaction line.
                    Ensure debits, credits, and balances are returned as decimal numbers.
                    Dates must be formatted as ISO YYYY-MM-DD.""",
                    user_prompt=(
                        "Extract all supplier account statement details including summary balances and the full list of transactions."
                        f"{extra}"
                    ),
                    response_model=SupplierAccountStatementExtraction
                )

                processing_time = int((time.time() - start_time) * 1000)
                result = statement_data.model_dump()
                result["document_category"] = "supplier_account_statement"
                result["confidence_score"] = 0.9
                result["processing_time_ms"] = processing_time
                return result

            except Exception as exc:
                logfire.error(f'Failed to extract supplier account statement from {filename}: {exc}')
                raise

    def extract_customer_account_statement(
        self,
        file_content: bytes,
        filename: str
    ) -> Dict[str, Any]:
        """Extract structured data from a customer account statement document."""
        with logfire.span('openai_extract_customer_account_statement'):
            start_time = time.time()

            try:
                statement_data = self._extract_with_vision(
                    file_content=file_content,
                    filename=filename,
                    document_category="customer_account_statement",
                    system_prompt="""You are an expert at extracting structured data from customer account statements.
                    Capture the customer identifiers, statement dates, balances, credit limits, and every transaction line.
                    Debits, credits, and balances must be decimal numbers.
                    Dates must be returned using ISO YYYY-MM-DD format.""",
                    user_prompt="Extract all customer account statement information including balances and detailed transactions.",
                    response_model=CustomerAccountStatementExtraction
                )

                processing_time = int((time.time() - start_time) * 1000)
                result = statement_data.model_dump()
                result["document_category"] = "customer_account_statement"
                result["confidence_score"] = 0.9
                result["processing_time_ms"] = processing_time
                return result

            except Exception as exc:
                logfire.error(f'Failed to extract customer account statement from {filename}: {exc}')
                raise

    def extract_supplier_invoice(
        self,
        file_content: bytes,
        filename: str
    ) -> Dict[str, Any]:
        """Extract structured data from a supplier invoice document."""
        with logfire.span('openai_extract_supplier_invoice'):
            start_time = time.time()

            try:
                invoice_data = self._extract_with_vision(
                    file_content=file_content,
                    filename=filename,
                    document_category="supplier_invoice",
                    system_prompt="""You are an expert at extracting structured data from supplier invoices for accounts payable processing.
                    Capture vendor and buyer information, invoice identifiers, dates, totals, taxes, payment instructions, references, and detailed line items.
                    Return all numeric values as decimal numbers without currency symbols.
                    Dates must use ISO YYYY-MM-DD format.""",
                    user_prompt="Extract all supplier invoice information including summary amounts, payment info, and detailed line items.",
                    response_model=SupplierInvoiceExtraction
                )

                processing_time = int((time.time() - start_time) * 1000)
                result = invoice_data.model_dump()
                result["document_category"] = "supplier_invoice"
                result["confidence_score"] = 0.92
                result["processing_time_ms"] = processing_time
                return result

            except Exception as exc:
                logfire.error(f'Failed to extract supplier invoice from {filename}: {exc}')
                raise

    def extract_shipping_bill(
        self,
        file_content: bytes,
        filename: str
    ) -> Dict[str, Any]:
        """Extract structured data from a shipping bill document."""
        with logfire.span('openai_extract_shipping_bill'):
            start_time = time.time()

            try:
                shipping_data = self._extract_with_vision(
                    file_content=file_content,
                    filename=filename,
                    document_category="shipping_bill",
                    system_prompt="""You are an expert at extracting structured data from shipping bills or bills of entry/export.
                    Capture exporter and consignee information, ports, transport details, incoterms, totals, and every declared line item with HS codes and customs values.
                    Return numeric amounts as decimals and dates using ISO YYYY-MM-DD format.""",
                    user_prompt="Extract all shipping bill declaration details including header information and each declared line item.",
                    response_model=ShippingBillExtraction
                )

                processing_time = int((time.time() - start_time) * 1000)
                result = shipping_data.model_dump()
                result["document_category"] = "shipping_bill"
                result["confidence_score"] = 0.88
                result["processing_time_ms"] = processing_time
                return result

            except Exception as exc:
                logfire.error(f'Failed to extract shipping bill from {filename}: {exc}')
                raise

    def extract_commercial_invoice(
        self,
        file_content: bytes,
        filename: str
    ) -> Dict[str, Any]:
        """Extract structured data from a commercial invoice document."""
        with logfire.span('openai_extract_commercial_invoice'):
            start_time = time.time()

            try:
                commercial_data = self._extract_with_vision(
                    file_content=file_content,
                    filename=filename,
                    document_category="commercial_invoice",
                    system_prompt="""You are an expert at extracting structured data from commercial export invoices.
                    Capture exporter and importer details, invoice identifiers, incoterms, payment terms, logistics information, totals, and each line item with HS codes and countries of origin/destination.
                    All monetary values must be decimals and dates in ISO YYYY-MM-DD format.""",
                    user_prompt="Extract all commercial invoice details including parties, totals, logistics information, and the detailed line item list.",
                    response_model=CommercialInvoiceExtraction
                )

                processing_time = int((time.time() - start_time) * 1000)
                result = commercial_data.model_dump()
                result["document_category"] = "commercial_invoice"
                result["confidence_score"] = 0.9
                result["processing_time_ms"] = processing_time
                return result

            except Exception as exc:
                logfire.error(f'Failed to extract commercial invoice from {filename}: {exc}')
                raise

    def extract_complex_document(
        self,
        file_content: bytes,
        filename: str,
        additional_instructions: Optional[str] = None,
    ) -> BaseModel:
        """Extract layout-aware content (text, tables, figures) from complex documents."""
        with logfire.span('openai_extract_complex_document'):
            start_time = time.time()

            try:
                extra = ""
                if additional_instructions and additional_instructions.strip():
                    extra = f"\n\nAdditional instructions:\n{additional_instructions.strip()}"

                complex_data = self._extract_with_vision(
                    file_content=file_content,
                    filename=filename,
                    document_category="complex_document",
                    system_prompt=(
                        "You are an expert at layout-aware OCR for complex documents. "
                        "Extract the document layout into ordered blocks and capture tables and figures. "
                        "Rules:\n"
                        "- Preserve reading order.\n"
                        "- For text blocks, return the verbatim text.\n"
                        "- For tables, return headers and rows exactly as shown.\n"
                        "- For figures/graphs, provide a short description and list only values explicitly shown. "
                        "Do not infer missing values.\n"
                        "- Use normalized bounding boxes (0-1) only when confident; otherwise omit.\n"
                        "- Keep summary_markdown concise and factual.\n"
                    ),
                    user_prompt=(
                        "Extract layout blocks, tables, figures, and a concise markdown summary "
                        "from this document. Include any numeric values shown in graphs or diagrams."
                        f"{extra}"
                    ),
                    response_model=ComplexDocumentExtraction,
                )

                processing_time = int((time.time() - start_time) * 1000)

                # Fill top-level tables/figures from blocks if not provided.
                if getattr(complex_data, "tables", None) in (None, []):
                    complex_data.tables = [
                        block.table for block in complex_data.blocks if block.table is not None
                    ]
                if getattr(complex_data, "figures", None) in (None, []):
                    complex_data.figures = [
                        block.figure for block in complex_data.blocks if block.figure is not None
                    ]

                if hasattr(complex_data, "confidence_score"):
                    complex_data.confidence_score = 0.88
                if hasattr(complex_data, "processing_time_ms"):
                    complex_data.processing_time_ms = processing_time
                if hasattr(complex_data, "document_category"):
                    complex_data.document_category = "complex_document"

                return complex_data

            except Exception as exc:
                logfire.error(f'Failed to extract complex document from {filename}: {exc}')
                raise

"""
OCR document processing service.

This service handles the business logic for extracting structured data
from documents using AI/LLM models.
"""

from typing import Dict, Any, Optional
import io
import time
import logfire
from pydantic import BaseModel

from app.ports import OCRClientProtocol
from app.domain.ocr.models import (
    OCRExtractionResponse,
    ContractPaymentTermsExtraction,
    SupplierAccountStatementExtraction,
)

from pypdf import PdfReader, PdfWriter


class OCRService:
    """
    Service for OCR document processing and extraction.
    
    This service orchestrates document extraction using AI/LLM models
    to convert unstructured documents into structured data.
    """
    
    def __init__(self, ocr_client: OCRClientProtocol):
        """
        Initialize OCR service.
        
        Args:
            ocr_client: OCR client adapter implementing the protocol
        """
        self.ocr_client = ocr_client
        logfire.info(f"OCR service initialized with client enabled: {ocr_client.enabled}")
    
    def extract_purchase_order(
        self,
        file_content: bytes,
        filename: str
    ) -> OCRExtractionResponse:
        """
        Extract structured data from a purchase order document.
        
        Args:
            file_content: Binary content of the PDF/image file
            filename: Name of the file
            
        Returns:
            OCRExtractionResponse with extracted PO data
        """
        with logfire.span('extract_purchase_order'):
            try:
                logfire.info(f'Processing PO document: {filename}')
                
                if not self.ocr_client.enabled:
                    return OCRExtractionResponse(
                        success=False,
                        document_type="purchase_order",
                        extracted_data={},
                        error_message="OCR client is not enabled"
                    )
                
                # Extract data using OCR client
                extracted_data = self.ocr_client.extract_purchase_order(
                    file_content=file_content,
                    filename=filename
                )
                
                logfire.info(f'Successfully extracted PO data from {filename}')
                
                return OCRExtractionResponse(
                    success=True,
                    document_type="purchase_order",
                    extracted_data=extracted_data,
                    confidence_score=extracted_data.get("confidence_score")
                )
                
            except Exception as e:
                logfire.error(f'Failed to extract PO from {filename}: {str(e)}')
                return OCRExtractionResponse(
                    success=False,
                    document_type="purchase_order",
                    extracted_data={},
                    error_message=str(e)
                )
    
    def extract_invoice(
        self,
        file_content: bytes,
        filename: str
    ) -> OCRExtractionResponse:
        """
        Extract structured data from an invoice document.
        
        Args:
            file_content: Binary content of the PDF/image file
            filename: Name of the file
            
        Returns:
            OCRExtractionResponse with extracted invoice data
        """
        with logfire.span('extract_invoice'):
            try:
                logfire.info(f'Processing invoice document: {filename}')
                
                if not self.ocr_client.enabled:
                    return OCRExtractionResponse(
                        success=False,
                        document_type="invoice",
                        extracted_data={},
                        error_message="OCR client is not enabled"
                    )
                
                # Extract data using OCR client
                extracted_data = self.ocr_client.extract_invoice(
                    file_content=file_content,
                    filename=filename
                )
                
                logfire.info(f'Successfully extracted invoice data from {filename}')
                
                return OCRExtractionResponse(
                    success=True,
                    document_type="invoice",
                    extracted_data=extracted_data,
                    confidence_score=extracted_data.get("confidence_score")
                )
                
            except Exception as e:
                logfire.error(f'Failed to extract invoice from {filename}: {str(e)}')
                return OCRExtractionResponse(
                    success=False,
                    document_type="invoice",
                    extracted_data={},
                    error_message=str(e)
                )
    
    def extract_supplier_account_statement(
        self,
        file_content: bytes,
        filename: str,
        additional_instructions: Optional[str] = None,
    ) -> OCRExtractionResponse:
        """Extract data from supplier account statements."""
        with logfire.span('extract_supplier_account_statement'):
            try:
                logfire.info(f'Processing supplier account statement: {filename}')

                if not self.ocr_client.enabled:
                    return OCRExtractionResponse(
                        success=False,
                        document_type="supplier_account_statement",
                        extracted_data={},
                        error_message="OCR client is not enabled"
                    )

                extracted_data = self.ocr_client.extract_supplier_account_statement(
                    file_content=file_content,
                    filename=filename,
                    additional_instructions=additional_instructions,
                )

                return OCRExtractionResponse(
                    success=True,
                    document_type="supplier_account_statement",
                    extracted_data=extracted_data,
                    confidence_score=extracted_data.get("confidence_score")
                )

            except Exception as e:
                logfire.error(f'Failed to extract supplier account statement from {filename}: {str(e)}')
                return OCRExtractionResponse(
                    success=False,
                    document_type="supplier_account_statement",
                    extracted_data={},
                    error_message=str(e)
                )

    def extract_customer_account_statement(
        self,
        file_content: bytes,
        filename: str
    ) -> OCRExtractionResponse:
        """Extract data from customer account statements."""
        with logfire.span('extract_customer_account_statement'):
            try:
                logfire.info(f'Processing customer account statement: {filename}')

                if not self.ocr_client.enabled:
                    return OCRExtractionResponse(
                        success=False,
                        document_type="customer_account_statement",
                        extracted_data={},
                        error_message="OCR client is not enabled"
                    )

                extracted_data = self.ocr_client.extract_customer_account_statement(
                    file_content=file_content,
                    filename=filename
                )

                return OCRExtractionResponse(
                    success=True,
                    document_type="customer_account_statement",
                    extracted_data=extracted_data,
                    confidence_score=extracted_data.get("confidence_score")
                )

            except Exception as e:
                logfire.error(f'Failed to extract customer account statement from {filename}: {str(e)}')
                return OCRExtractionResponse(
                    success=False,
                    document_type="customer_account_statement",
                    extracted_data={},
                    error_message=str(e)
                )

    def extract_supplier_invoice(
        self,
        file_content: bytes,
        filename: str
    ) -> OCRExtractionResponse:
        """Extract data from supplier invoices."""
        with logfire.span('extract_supplier_invoice'):
            try:
                logfire.info(f'Processing supplier invoice: {filename}')

                if not self.ocr_client.enabled:
                    return OCRExtractionResponse(
                        success=False,
                        document_type="supplier_invoice",
                        extracted_data={},
                        error_message="OCR client is not enabled"
                    )

                extracted_data = self.ocr_client.extract_supplier_invoice(
                    file_content=file_content,
                    filename=filename
                )

                return OCRExtractionResponse(
                    success=True,
                    document_type="supplier_invoice",
                    extracted_data=extracted_data,
                    confidence_score=extracted_data.get("confidence_score")
                )

            except Exception as e:
                logfire.error(f'Failed to extract supplier invoice from {filename}: {str(e)}')
                return OCRExtractionResponse(
                    success=False,
                    document_type="supplier_invoice",
                    extracted_data={},
                    error_message=str(e)
                )

    def extract_vendor_quote(
        self,
        file_content: bytes,
        filename: str,
        additional_instructions: Optional[str] = None,
    ) -> OCRExtractionResponse:
        """Extract data from vendor quotes."""
        with logfire.span('extract_vendor_quote'):
            try:
                logfire.info(f'Processing vendor quote: {filename}')

                if not self.ocr_client.enabled:
                    return OCRExtractionResponse(
                        success=False,
                        document_type="vendor_quote",
                        extracted_data={},
                        error_message="OCR client is not enabled"
                    )

                extracted_data = self.ocr_client.extract_vendor_quote(
                    file_content=file_content,
                    filename=filename,
                    additional_instructions=additional_instructions,
                )

                return OCRExtractionResponse(
                    success=True,
                    document_type="vendor_quote",
                    extracted_data=extracted_data,
                    confidence_score=extracted_data.get("confidence_score")
                )

            except Exception as e:
                logfire.error(f'Failed to extract vendor quote from {filename}: {str(e)}')
                return OCRExtractionResponse(
                    success=False,
                    document_type="vendor_quote",
                    extracted_data={},
                    error_message=str(e)
                )

    def extract_order_confirmation(
        self,
        file_content: bytes,
        filename: str,
        additional_instructions: Optional[str] = None,
    ) -> OCRExtractionResponse:
        """Extract data from order confirmations."""
        with logfire.span('extract_order_confirmation'):
            try:
                logfire.info(f'Processing order confirmation: {filename}')

                if not self.ocr_client.enabled:
                    return OCRExtractionResponse(
                        success=False,
                        document_type="order_confirmation",
                        extracted_data={},
                        error_message="OCR client is not enabled"
                    )

                extracted_data = self.ocr_client.extract_order_confirmation(
                    file_content=file_content,
                    filename=filename,
                    additional_instructions=additional_instructions,
                )

                return OCRExtractionResponse(
                    success=True,
                    document_type="order_confirmation",
                    extracted_data=extracted_data,
                    confidence_score=extracted_data.get("confidence_score")
                )

            except Exception as e:
                logfire.error(f'Failed to extract order confirmation from {filename}: {str(e)}')
                return OCRExtractionResponse(
                    success=False,
                    document_type="order_confirmation",
                    extracted_data={},
                    error_message=str(e)
                )

    def extract_shipping_bill(
        self,
        file_content: bytes,
        filename: str
    ) -> OCRExtractionResponse:
        """Extract data from shipping bills."""
        with logfire.span('extract_shipping_bill'):
            try:
                logfire.info(f'Processing shipping bill: {filename}')

                if not self.ocr_client.enabled:
                    return OCRExtractionResponse(
                        success=False,
                        document_type="shipping_bill",
                        extracted_data={},
                        error_message="OCR client is not enabled"
                    )

                extracted_data = self.ocr_client.extract_shipping_bill(
                    file_content=file_content,
                    filename=filename
                )

                return OCRExtractionResponse(
                    success=True,
                    document_type="shipping_bill",
                    extracted_data=extracted_data,
                    confidence_score=extracted_data.get("confidence_score")
                )

            except Exception as e:
                logfire.error(f'Failed to extract shipping bill from {filename}: {str(e)}')
                return OCRExtractionResponse(
                    success=False,
                    document_type="shipping_bill",
                    extracted_data={},
                    error_message=str(e)
                )

    def extract_commercial_invoice(
        self,
        file_content: bytes,
        filename: str
    ) -> OCRExtractionResponse:
        """Extract data from commercial invoices."""
        with logfire.span('extract_commercial_invoice'):
            try:
                logfire.info(f'Processing commercial invoice: {filename}')

                if not self.ocr_client.enabled:
                    return OCRExtractionResponse(
                        success=False,
                        document_type="commercial_invoice",
                        extracted_data={},
                        error_message="OCR client is not enabled"
                    )

                extracted_data = self.ocr_client.extract_commercial_invoice(
                    file_content=file_content,
                    filename=filename
                )

                return OCRExtractionResponse(
                    success=True,
                    document_type="commercial_invoice",
                    extracted_data=extracted_data,
                    confidence_score=extracted_data.get("confidence_score")
                )

            except Exception as e:
                logfire.error(f'Failed to extract commercial invoice from {filename}: {str(e)}')
                return OCRExtractionResponse(
                    success=False,
                    document_type="commercial_invoice",
                    extracted_data={},
                    error_message=str(e)
                )

    def extract_complex_document(
        self,
        file_content: bytes,
        filename: str,
        additional_instructions: Optional[str] = None,
    ) -> OCRExtractionResponse:
        """Extract layout-aware content from complex documents."""
        document_type = "complex_document"
        with logfire.span('extract_complex_document'):
            try:
                logfire.info(f'Processing complex document: {filename}')

                if not self.ocr_client.enabled:
                    return OCRExtractionResponse(
                        success=False,
                        document_type=document_type,
                        extracted_data={},
                        error_message="OCR client is not enabled"
                    )

                extracted_model = self.ocr_client.extract_complex_document(
                    file_content=file_content,
                    filename=filename,
                    additional_instructions=additional_instructions,
                )

                return OCRExtractionResponse(
                    success=True,
                    document_type=document_type,
                    extracted_data=extracted_model.model_dump(),
                    confidence_score=getattr(extracted_model, "confidence_score", None),
                    processing_time_ms=getattr(extracted_model, "processing_time_ms", None),
                )

            except Exception as e:
                logfire.error(f'Failed to extract complex document from {filename}: {str(e)}')
                return OCRExtractionResponse(
                    success=False,
                    document_type=document_type,
                    extracted_data={},
                    error_message=str(e)
                )
    
    def extract_custom_document(
        self,
        file_content: bytes,
        filename: str,
        document_type: str,
        output_model: BaseModel,
        additional_instructions: Optional[str] = None,
    ) -> OCRExtractionResponse:
        """
        Extract structured data from a custom document type.
        
        Args:
            file_content: Binary content of the PDF/image file
            filename: Name of the file
            document_type: Type of document for prompt customization
            output_model: Pydantic model defining expected output structure
            
        Returns:
            OCRExtractionResponse with extracted data
        """
        with logfire.span('extract_custom_document'):
            try:
                logfire.info(f'Processing {document_type} document: {filename}')
                
                if not self.ocr_client.enabled:
                    return OCRExtractionResponse(
                        success=False,
                        document_type=document_type,
                        extracted_data={},
                        error_message="OCR client is not enabled"
                    )
                
                # Extract data using OCR client with custom model
                extracted_model = self.ocr_client.extract_generic_document(
                    file_content=file_content,
                    filename=filename,
                    document_type=document_type,
                    output_model=output_model,
                    additional_instructions=additional_instructions,
                )

                logfire.info(f'Successfully extracted {document_type} data from {filename}')

                return OCRExtractionResponse(
                    success=True,
                    document_type=document_type,
                    extracted_data=extracted_model.model_dump(),
                    confidence_score=getattr(extracted_model, "confidence_score", None)
                )

            except Exception as e:
                logfire.error(f'Failed to extract {document_type} from {filename}: {str(e)}')
                return OCRExtractionResponse(
                    success=False,
                    document_type=document_type,
                    extracted_data={},
                    error_message=str(e)
                )

    def extract_customer_payment_terms_contract(
        self,
        file_content: bytes,
        filename: str,
        additional_instructions: Optional[str] = None,
        *,
        max_text_pages: int = 60,
        max_vision_pages_fallback: int = 12,
    ) -> OCRExtractionResponse:
        """
        Extract customer contract payment terms + total amount.

        Strategy:
        - For smaller PDFs/images: use vision extraction directly.
        - For large PDFs: extract text with pypdf, build a focused snippet, and parse via text-only extraction.
        - If text extraction is empty (scanned PDF): fall back to vision on the first N pages.
        """
        document_type = "customer_payment_terms_contract"

        with logfire.span('extract_customer_payment_terms_contract'):
            start_time = time.time()

            try:
                logfire.info(f'Processing {document_type} document: {filename}')

                if not self.ocr_client.enabled:
                    return OCRExtractionResponse(
                        success=False,
                        document_type=document_type,
                        extracted_data={},
                        error_message="OCR client is not enabled",
                    )

                is_pdf = file_content[:4] == b"%PDF"

                # Prefer text extraction for PDFs (fast, reliable for typed contracts, avoids vision upload limits).
                if is_pdf:
                    extracted_text = self._extract_pdf_text(file_content, max_pages=max_text_pages)
                    snippet = self._build_payment_terms_snippet(extracted_text)

                    if snippet.strip():
                        extra = ""
                        if additional_instructions and additional_instructions.strip():
                            extra = f"\n\nAdditional instructions:\n{additional_instructions.strip()}"

                        extracted_model = self.ocr_client.extract_generic_text(
                            document_text=f"{snippet}{extra}",
                            document_type=document_type,
                            output_model=ContractPaymentTermsExtraction,
                        )
                        # Post-process: if the model omitted currency but the document clearly indicates it, fill it in.
                        if getattr(extracted_model, "currency", None) in (None, "", "UNKNOWN", "unknown"):
                            normalized = snippet.replace(" ", "").upper()
                            if "($USD)" in normalized or "USD" in normalized:
                                extracted_model.currency = "USD"
                    else:
                        # Scanned PDF (no text) → vision fallback on first pages only.
                        truncated_pdf = self._truncate_pdf(file_content, max_pages=max_vision_pages_fallback)
                        extracted_model = self.ocr_client.extract_generic_document(
                            file_content=truncated_pdf,
                            filename=filename,
                            document_type=document_type,
                            output_model=ContractPaymentTermsExtraction,
                        )
                else:
                    # Non-PDF inputs (images): use vision directly.
                    extracted_model = self.ocr_client.extract_generic_document(
                        file_content=file_content,
                        filename=filename,
                        document_type=document_type,
                        output_model=ContractPaymentTermsExtraction,
                    )

                processing_time = int((time.time() - start_time) * 1000)
                if hasattr(extracted_model, "processing_time_ms") and getattr(extracted_model, "processing_time_ms") is None:
                    extracted_model.processing_time_ms = processing_time

                return OCRExtractionResponse(
                    success=True,
                    document_type=document_type,
                    extracted_data=extracted_model.model_dump(),
                    confidence_score=getattr(extracted_model, "confidence_score", None),
                    processing_time_ms=getattr(extracted_model, "processing_time_ms", None),
                )

            except Exception as e:
                logfire.error(f'Failed to extract {document_type} from {filename}: {str(e)}')
                return OCRExtractionResponse(
                    success=False,
                    document_type=document_type,
                    extracted_data={},
                    error_message=str(e),
                )

    @staticmethod
    def _extract_pdf_text(file_content: bytes, *, max_pages: int = 60) -> str:
        """Extract text from the first N pages of a PDF using pypdf."""
        reader = PdfReader(io.BytesIO(file_content))
        pages_text: list[str] = []
        for i, page in enumerate(reader.pages):
            if i >= max_pages:
                break
            extracted = page.extract_text() or ""
            if extracted.strip():
                pages_text.append(f"[Page {i + 1}]\n{extracted.strip()}")
        return "\n\n".join(pages_text)

    @staticmethod
    def _truncate_pdf(file_content: bytes, *, max_pages: int = 12) -> bytes:
        """Create a smaller PDF containing only the first N pages."""
        reader = PdfReader(io.BytesIO(file_content))
        writer = PdfWriter()
        for i, page in enumerate(reader.pages):
            if i >= max_pages:
                break
            writer.add_page(page)

        out = io.BytesIO()
        writer.write(out)
        return out.getvalue()

    @staticmethod
    def _build_payment_terms_snippet(extracted_text: str) -> str:
        """
        Build a focused snippet for payment terms + total amount to keep prompt size manageable.
        """
        if not extracted_text or not extracted_text.strip():
            return ""

        keywords = [
            "payment terms",
            "terms of payment",
            "payment schedule",
            "schedule of payments",
            "milestone",
            "deposit",
            "down payment",
            "progress payment",
            "net",
            "total",
            "grand total",
            "total amount",
            "contract value",
            "total contract value",
            "contract price",
            "total price",
        ]

        text = extracted_text
        lower = text.lower()
        ranges: list[tuple[int, int]] = []

        window = 900  # characters around matches
        for kw in keywords:
            start = 0
            while True:
                idx = lower.find(kw, start)
                if idx == -1:
                    break
                a = max(0, idx - window)
                b = min(len(text), idx + len(kw) + window)
                ranges.append((a, b))
                start = idx + len(kw)

        # If nothing matched, fall back to the beginning of the doc (often summary pages)
        if not ranges:
            return text[:15000]

        # Merge overlapping ranges
        ranges.sort()
        merged: list[tuple[int, int]] = []
        for a, b in ranges:
            if not merged or a > merged[-1][1]:
                merged.append((a, b))
            else:
                merged[-1] = (merged[-1][0], max(merged[-1][1], b))

        parts: list[str] = []
        for a, b in merged:
            parts.append(text[a:b].strip())

        snippet = "\n\n---\n\n".join(part for part in parts if part)

        # Hard cap to avoid enormous prompts
        return snippet[:30000]
    
    def validate_extraction(
        self,
        extracted_data: Dict[str, Any],
        document_type: str
    ) -> tuple[bool, Optional[str]]:
        """
        Validate extracted data meets minimum requirements.
        
        Args:
            extracted_data: Extracted data to validate
            document_type: Type of document
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        with logfire.span('validate_extraction'):
            try:
                if document_type == "purchase_order":
                    required_fields = ["po_number", "po_date", "vendor_name", "lines", "total_amount"]
                    for field in required_fields:
                        if field not in extracted_data or not extracted_data[field]:
                            return False, f"Missing required field: {field}"
                    
                    if not extracted_data.get("lines"):
                        return False, "Purchase order must have at least one line item"
                    
                elif document_type == "invoice":
                    required_fields = ["invoice_number", "invoice_date", "vendor_name", "lines", "total_amount"]
                    for field in required_fields:
                        if field not in extracted_data or not extracted_data[field]:
                            return False, f"Missing required field: {field}"
                    
                    if not extracted_data.get("lines"):
                        return False, "Invoice must have at least one line item"
                
                elif document_type == "supplier_account_statement":
                    required_fields = [
                        "supplier_name",
                        "transactions",
                    ]
                    for field in required_fields:
                        if field not in extracted_data or extracted_data[field] in (None, "", []):
                            return False, f"Missing required field: {field}"
                    if not extracted_data["transactions"]:
                        return False, "Account statement must include at least one transaction"
                
                elif document_type == "customer_account_statement":
                    required_fields = [
                        "customer_name",
                        "statement_period_start",
                        "statement_period_end",
                        "opening_balance",
                        "closing_balance",
                        "transactions"
                    ]
                    for field in required_fields:
                        if field not in extracted_data or extracted_data[field] in (None, "", []):
                            return False, f"Missing required field: {field}"
                    if not extracted_data["transactions"]:
                        return False, "Account statement must include at least one transaction"
                
                elif document_type == "supplier_invoice":
                    required_fields = ["invoice_number", "invoice_date", "vendor_name", "lines", "total_amount"]
                    for field in required_fields:
                        if field not in extracted_data or not extracted_data[field]:
                            return False, f"Missing required field: {field}"
                    if not extracted_data.get("lines"):
                        return False, "Supplier invoice must have at least one line item"

                elif document_type == "vendor_quote":
                    required_fields = ["quote_number", "quote_date", "supplier_name", "lines"]
                    for field in required_fields:
                        if field not in extracted_data or extracted_data[field] in (None, "", []):
                            return False, f"Missing required field: {field}"
                    if not extracted_data.get("lines"):
                        return False, "Vendor quote must have at least one line item"

                elif document_type == "order_confirmation":
                    required_fields = [
                        "order_confirmation_number",
                        "order_confirmation_date",
                        "supplier_name",
                        "po_reference_number",
                        "lines",
                    ]
                    for field in required_fields:
                        if field not in extracted_data or extracted_data[field] in (None, "", []):
                            return False, f"Missing required field: {field}"
                    if not extracted_data.get("lines"):
                        return False, "Order confirmation must have at least one line item"
                
                elif document_type == "shipping_bill":
                    required_fields = ["bill_number", "bill_date", "exporter_name", "consignee_name", "line_items"]
                    for field in required_fields:
                        if field not in extracted_data or extracted_data[field] in (None, "", []):
                            return False, f"Missing required field: {field}"
                    if not extracted_data["line_items"]:
                        return False, "Shipping bill must include at least one line item"
                
                elif document_type == "commercial_invoice":
                    required_fields = ["invoice_number", "invoice_date", "exporter_name", "importer_name", "line_items"]
                    for field in required_fields:
                        if field not in extracted_data or extracted_data[field] in (None, "", []):
                            return False, f"Missing required field: {field}"
                    if not extracted_data["line_items"]:
                        return False, "Commercial invoice must include at least one line item"
                
                logfire.info(f'Validation passed for {document_type}')
                return True, None
                
            except Exception as e:
                logfire.error(f'Validation error for {document_type}: {str(e)}')
                return False, str(e)

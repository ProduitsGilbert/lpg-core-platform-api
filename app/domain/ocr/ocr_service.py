"""
OCR document processing service.

This service handles the business logic for extracting structured data
from documents using AI/LLM models.
"""

from typing import Dict, Any, Optional
from decimal import Decimal, ROUND_HALF_UP
import io
import time
import re
import logfire
from pydantic import BaseModel

from app.ports import OCRClientProtocol
from app.domain.ocr.models import (
    OCRExtractionResponse,
    CarrierAccountStatementExtraction,
    ContractPaymentTermsExtraction,
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
                logfire.error(
                    "Failed to extract purchase order",
                    filename=filename,
                    error=str(e),
                )
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
                logfire.error(
                    "Failed to extract invoice",
                    filename=filename,
                    error=str(e),
                )
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
                logfire.error(
                    "Failed to extract supplier account statement",
                    filename=filename,
                    error=str(e),
                )
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
                logfire.error(
                    "Failed to extract customer account statement",
                    filename=filename,
                    error=str(e),
                )
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
                logfire.error(
                    "Failed to extract supplier invoice",
                    filename=filename,
                    error=str(e),
                )
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
                logfire.error(
                    "Failed to extract vendor quote",
                    filename=filename,
                    error=str(e),
                )
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
                logfire.error(
                    "Failed to extract order confirmation",
                    filename=filename,
                    error=str(e),
                )
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
                logfire.error(
                    "Failed to extract shipping bill",
                    filename=filename,
                    error=str(e),
                )
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
                logfire.error(
                    "Failed to extract commercial invoice",
                    filename=filename,
                    error=str(e),
                )
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
                logfire.error(
                    "Failed to extract complex document",
                    filename=filename,
                    error=str(e),
                )
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
                logfire.error(
                    "Failed to extract document",
                    document_type=document_type,
                    filename=filename,
                    error=str(e),
                )
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
                            detected_currency = self._detect_currency_code(snippet)
                            if detected_currency:
                                extracted_model.currency = detected_currency
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

                extracted_data = extracted_model.model_dump()
                payment_terms_table, payment_terms_table_markdown = self._build_payment_terms_table(extracted_model)
                if payment_terms_table:
                    extracted_data["payment_terms_table"] = payment_terms_table
                    extracted_data["payment_terms_table_markdown"] = payment_terms_table_markdown

                return OCRExtractionResponse(
                    success=True,
                    document_type=document_type,
                    extracted_data=extracted_data,
                    confidence_score=getattr(extracted_model, "confidence_score", None),
                    processing_time_ms=getattr(extracted_model, "processing_time_ms", None),
                )

            except Exception as e:
                logfire.error(
                    "Failed to extract document",
                    document_type=document_type,
                    filename=filename,
                    error=str(e),
                )
                return OCRExtractionResponse(
                    success=False,
                    document_type=document_type,
                    extracted_data={},
                    error_message=str(e),
                )

    def extract_carrier_account_statement(
        self,
        file_content: bytes,
        filename: str,
        carrier: str,
        additional_instructions: Optional[str] = None,
        *,
        max_pages: Optional[int] = None,
    ) -> OCRExtractionResponse:
        """
        Extract shipment-level charges from a carrier account statement.

        For PDF inputs, the full statement is processed by default. When `max_pages`
        is provided, only the first N pages are processed.
        """
        document_type = "carrier_account_statement"
        normalized_carrier = (carrier or "").strip().lower()

        with logfire.span('extract_carrier_account_statement'):
            start_time = time.time()

            try:
                logfire.info(
                    "Processing carrier account statement",
                    filename=filename,
                    carrier=normalized_carrier,
                    max_pages=max_pages,
                )

                if not self.ocr_client.enabled:
                    return OCRExtractionResponse(
                        success=False,
                        document_type=document_type,
                        extracted_data={},
                        error_message="OCR client is not enabled",
                    )

                if normalized_carrier != "purolator":
                    return OCRExtractionResponse(
                        success=False,
                        document_type=document_type,
                        extracted_data={},
                        error_message=f"Unsupported carrier: {normalized_carrier}",
                    )

                carrier_guidance = self._build_carrier_statement_instructions(
                    carrier=normalized_carrier,
                    max_pages=max_pages,
                    additional_instructions=additional_instructions,
                )

                is_pdf = file_content[:4] == b"%PDF"
                extraction_content = file_content
                extraction_filename = filename
                processed_pages = 1

                if is_pdf:
                    processed_pages = self._count_pdf_pages(file_content)
                    if max_pages is not None and max_pages > 0:
                        extraction_content = self._truncate_pdf(file_content, max_pages=max_pages)
                        extraction_filename = f"{filename.rsplit('.', 1)[0]}-first-{max_pages}.pdf"
                        processed_pages = min(processed_pages, max_pages)

                    page_ranges = self._build_pdf_page_ranges(processed_pages, chunk_pages=1)
                    chunk_results: list[CarrierAccountStatementExtraction] = []
                    total_chunks = len(page_ranges)
                    for chunk_index, (start_page, end_page) in enumerate(page_ranges, start=1):
                        chunk_instructions = self._build_carrier_statement_chunk_instructions(
                            base_instructions=carrier_guidance,
                            chunk_index=chunk_index,
                            total_chunks=total_chunks,
                            start_page=start_page,
                            end_page=end_page,
                        )
                        chunk_pdf = self._slice_pdf_pages(
                            extraction_content,
                            start_page=start_page,
                            end_page=end_page,
                        )
                        chunk_filename = (
                            f"{extraction_filename.rsplit('.', 1)[0]}-page-{start_page}.pdf"
                            if start_page == end_page
                            else f"{extraction_filename.rsplit('.', 1)[0]}-pages-{start_page}-{end_page}.pdf"
                        )

                        try:
                            chunk_model = self.ocr_client.extract_generic_document(
                                file_content=chunk_pdf,
                                filename=chunk_filename,
                                document_type=f"{normalized_carrier}_{document_type}",
                                output_model=CarrierAccountStatementExtraction,
                                additional_instructions=chunk_instructions,
                                prefer_vision=True,
                            )
                        except Exception as chunk_exc:
                            logfire.warn(
                                "Carrier statement vision chunk extraction failed; falling back to text chunk parsing.",
                                chunk_index=chunk_index,
                                start_page=start_page,
                                end_page=end_page,
                                error=str(chunk_exc),
                            )
                            chunk_text = self._extract_pdf_text(
                                chunk_pdf,
                                max_pages=(end_page - start_page + 1),
                            )
                            if not chunk_text.strip():
                                raise
                            chunk_model = self.ocr_client.extract_generic_text(
                                document_text=chunk_text,
                                document_type=f"{normalized_carrier}_{document_type}",
                                output_model=CarrierAccountStatementExtraction,
                                additional_instructions=chunk_instructions,
                            )

                        if start_page == end_page:
                            normalized_shipments = [
                                shipment
                                if shipment.source_page is not None
                                else shipment.model_copy(update={"source_page": start_page})
                                for shipment in chunk_model.shipments
                            ]
                            chunk_model = chunk_model.model_copy(update={"shipments": normalized_shipments})
                        chunk_results.append(chunk_model)

                    extracted_model = self._merge_carrier_statement_chunk_results(
                        carrier=normalized_carrier,
                        processed_pages=processed_pages,
                        chunk_results=chunk_results,
                    )
                else:
                    extracted_model = self.ocr_client.extract_generic_document(
                        file_content=extraction_content,
                        filename=extraction_filename,
                        document_type=f"{normalized_carrier}_{document_type}",
                        output_model=CarrierAccountStatementExtraction,
                        additional_instructions=carrier_guidance,
                        prefer_vision=True,
                    )

                processing_time = int((time.time() - start_time) * 1000)
                extracted_data = extracted_model.model_dump()
                extracted_data["carrier"] = normalized_carrier
                extracted_data["processed_pages"] = processed_pages if is_pdf else 1
                extracted_data["document_category"] = document_type
                extracted_data["confidence_score"] = 0.9
                extracted_data["processing_time_ms"] = processing_time

                return OCRExtractionResponse(
                    success=True,
                    document_type=document_type,
                    extracted_data=extracted_data,
                    confidence_score=0.9,
                    processing_time_ms=processing_time,
                )

            except Exception as e:
                logfire.error(
                    "Failed to extract carrier account statement",
                    carrier=normalized_carrier,
                    filename=filename,
                    error=str(e),
                )
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
    def _build_pdf_page_ranges(total_pages: int, *, chunk_pages: int = 1) -> list[tuple[int, int]]:
        """Build 1-based inclusive page ranges."""
        if total_pages <= 0:
            return []
        if chunk_pages <= 0:
            chunk_pages = 1

        ranges: list[tuple[int, int]] = []
        start_page = 1
        while start_page <= total_pages:
            end_page = min(total_pages, start_page + chunk_pages - 1)
            ranges.append((start_page, end_page))
            start_page = end_page + 1
        return ranges

    @staticmethod
    def _slice_pdf_pages(
        file_content: bytes,
        *,
        start_page: int,
        end_page: int,
    ) -> bytes:
        """Return a PDF containing only the requested 1-based inclusive page range."""
        if start_page <= 0 or end_page < start_page:
            raise ValueError("Invalid page range for PDF slicing")

        reader = PdfReader(io.BytesIO(file_content))
        writer = PdfWriter()
        page_count = len(reader.pages)
        if start_page > page_count:
            raise ValueError("Start page exceeds PDF page count")

        for page_index in range(start_page - 1, min(end_page, page_count)):
            writer.add_page(reader.pages[page_index])

        out = io.BytesIO()
        writer.write(out)
        return out.getvalue()

    @staticmethod
    def _extract_pdf_text_chunks(
        file_content: bytes,
        *,
        max_pages: int = 60,
        chunk_pages: int = 1,
    ) -> list[tuple[int, int, str]]:
        """Extract PDF text in small page chunks to avoid oversized JSON responses."""
        if chunk_pages <= 0:
            chunk_pages = 1

        reader = PdfReader(io.BytesIO(file_content))
        total_pages = min(len(reader.pages), max_pages)
        chunks: list[tuple[int, int, str]] = []
        current_parts: list[str] = []
        chunk_start_page = 1

        for page_index in range(total_pages):
            page_number = page_index + 1
            extracted = reader.pages[page_index].extract_text() or ""
            if extracted.strip():
                current_parts.append(f"[Page {page_number}]\n{extracted.strip()}")

            reached_chunk_size = (page_number - chunk_start_page + 1) >= chunk_pages
            reached_last_page = page_number == total_pages
            if reached_chunk_size or reached_last_page:
                if current_parts:
                    chunks.append((chunk_start_page, page_number, "\n\n".join(current_parts)))
                current_parts = []
                chunk_start_page = page_number + 1

        return chunks

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
    def _count_pdf_pages(file_content: bytes) -> int:
        """Count pages in a PDF payload."""
        reader = PdfReader(io.BytesIO(file_content))
        return len(reader.pages)

    @staticmethod
    def _merge_carrier_statement_chunk_results(
        *,
        carrier: str,
        processed_pages: int,
        chunk_results: list[CarrierAccountStatementExtraction],
    ) -> CarrierAccountStatementExtraction:
        """Merge chunk-level extraction results into a single carrier statement payload."""
        if not chunk_results:
            raise ValueError("No carrier statement chunk results to merge")

        account_number: Optional[str] = None
        invoice_number: Optional[str] = None
        invoice_date = None
        due_date = None
        currency = "CAD"
        amount_due = None

        note_seen: set[str] = set()
        merged_notes: list[str] = []
        merged_shipments = []
        seen_shipments: set[tuple[str, str, str, str, str, int]] = set()

        for chunk in chunk_results:
            if not account_number and chunk.account_number:
                account_number = chunk.account_number
            if not invoice_number and chunk.invoice_number:
                invoice_number = chunk.invoice_number
            if invoice_date is None and chunk.invoice_date is not None:
                invoice_date = chunk.invoice_date
            if due_date is None and chunk.due_date is not None:
                due_date = chunk.due_date
            if (not currency or currency == "CAD") and chunk.currency:
                currency = chunk.currency
            if amount_due is None and chunk.amount_due is not None:
                amount_due = chunk.amount_due

            if chunk.notes and chunk.notes.strip():
                normalized_note = chunk.notes.strip()
                if normalized_note not in note_seen:
                    note_seen.add(normalized_note)
                    merged_notes.append(normalized_note)

            for shipment in chunk.shipments:
                tracking_number = (shipment.tracking_number or "").strip()
                shipped_from = (shipment.shipped_from_address or "").strip()
                shipped_to = (shipment.shipped_to_address or "").strip()
                if not tracking_number or not shipped_from or not shipped_to:
                    continue

                dedupe_key = (
                    shipment.shipment_date.isoformat(),
                    tracking_number,
                    str(shipment.total_charges),
                    (shipment.ref_1 or "").strip(),
                    (shipment.ref_2 or "").strip(),
                    int(shipment.source_page or 0),
                )
                if dedupe_key in seen_shipments:
                    continue
                seen_shipments.add(dedupe_key)
                merged_shipments.append(shipment)

        if not merged_shipments:
            raise ValueError("Carrier statement extraction returned no shipment transactions")

        return CarrierAccountStatementExtraction(
            carrier=carrier,
            account_number=account_number,
            invoice_number=invoice_number,
            invoice_date=invoice_date,
            due_date=due_date,
            currency=currency or "CAD",
            amount_due=amount_due,
            processed_pages=processed_pages,
            shipments=merged_shipments,
            notes="\n\n".join(merged_notes) if merged_notes else None,
        )

    @staticmethod
    def _build_payment_terms_snippet(extracted_text: str) -> str:
        """
        Build a focused snippet for payment terms + total amount to keep prompt size manageable.
        """
        if not extracted_text or not extracted_text.strip():
            return ""

        terms_keywords = [
            "payment terms",
            "terms of payment",
            "payment schedule",
            "schedule of payments",
            "milestone",
            "deposit",
            "down payment",
            "progress payment",
            "net",
            "terms:",
        ]
        amount_keywords = [
            "total",
            "grand total",
            "total amount",
            "contract value",
            "total contract value",
            "contract price",
            "total price",
        ]
        keywords = terms_keywords + amount_keywords

        text = extracted_text
        lower = text.lower()
        ranges: list[tuple[int, int]] = []
        matched_terms = False

        window = 900  # characters around matches
        for kw in keywords:
            start = 0
            while True:
                idx = lower.find(kw, start)
                if idx == -1:
                    break
                if kw in terms_keywords:
                    matched_terms = True
                a = max(0, idx - window)
                b = min(len(text), idx + len(kw) + window)
                ranges.append((a, b))
                start = idx + len(kw)

        # If nothing matched, fall back to the beginning of the doc (often summary pages)
        if not ranges:
            return text[:15000]

        # If we only matched totals but missed the payment terms, include the tail pages (terms are often near the end).
        if not matched_terms:
            tail_len = 15000
            ranges.append((max(0, len(text) - tail_len), len(text)))

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

    @staticmethod
    def _detect_currency_code(text: str) -> Optional[str]:
        if not text:
            return None
        codes = [
            "USD",
            "CAD",
            "EUR",
            "GBP",
            "AUD",
            "NZD",
            "JPY",
            "CHF",
            "CNY",
            "MXN",
            "BRL",
            "INR",
            "SEK",
            "NOK",
            "DKK",
        ]
        upper = text.upper()
        pattern = r"\\(\\$?\\s*(" + "|".join(codes) + r")\\s*\\)"
        match = re.search(pattern, upper)
        if match:
            return match.group(1)
        match = re.search(r"\\b(" + "|".join(codes) + r")\\b", upper)
        if match:
            return match.group(1)
        return None

    @staticmethod
    def _format_decimal(value: Optional[Decimal], *, places: int = 2) -> Optional[str]:
        if value is None:
            return None
        quant = Decimal("1") if places <= 0 else Decimal("1").scaleb(-places)
        rounded = value.quantize(quant, rounding=ROUND_HALF_UP)
        return format(rounded, "f")

    def _build_payment_terms_table(
        self,
        extracted_model: ContractPaymentTermsExtraction,
    ) -> tuple[list[dict], str]:
        milestones = getattr(extracted_model, "milestones", None) or []
        if not milestones:
            return [], ""

        total_amount = getattr(extracted_model, "total_amount", None)
        try:
            total_amount = Decimal(str(total_amount)) if total_amount is not None else None
        except Exception:
            total_amount = None

        default_currency = (getattr(extracted_model, "currency", None) or "").upper() or None

        rows: list[dict] = []
        for milestone in milestones:
            percent = getattr(milestone, "percent", None)
            amount = getattr(milestone, "amount", None)
            currency = (getattr(milestone, "currency", None) or default_currency)

            if percent is not None:
                try:
                    percent = Decimal(str(percent))
                except Exception:
                    percent = None
            if amount is not None:
                try:
                    amount = Decimal(str(amount))
                except Exception:
                    amount = None

            calculated_amount = None
            if amount is not None:
                calculated_amount = amount
                if percent is None and total_amount:
                    percent = (amount / total_amount * Decimal("100")).quantize(
                        Decimal("0.01"), rounding=ROUND_HALF_UP
                    )
            elif percent is not None and total_amount:
                calculated_amount = (percent / Decimal("100")) * total_amount
                calculated_amount = calculated_amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            elif percent is None and amount is None and total_amount and len(milestones) == 1:
                percent = Decimal("100")
                calculated_amount = total_amount

            rows.append(
                {
                    "description": getattr(milestone, "timing_text", "") or "",
                    "percent": self._format_decimal(percent, places=2) if percent is not None else None,
                    "calculated_amount": self._format_decimal(calculated_amount, places=2)
                    if calculated_amount is not None
                    else None,
                    "currency": currency,
                }
            )

        if not rows:
            return [], ""

        headers = ["Description", "Percent", "Calculated Amount", "Currency"]
        md_lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
        for row in rows:
            md_lines.append(
                "| "
                + " | ".join(
                    [
                        (row.get("description") or "").replace("\n", " ").strip(),
                        row.get("percent") or "",
                        row.get("calculated_amount") or "",
                        row.get("currency") or "",
                    ]
                )
                + " |"
            )
        return rows, "\n".join(md_lines)

    @staticmethod
    def _build_carrier_statement_instructions(
        *,
        carrier: str,
        max_pages: Optional[int] = None,
        additional_instructions: Optional[str] = None,
    ) -> str:
        scope_line = (
            f"Extract transactions only from the first {max_pages} pages of the uploaded PDF."
            if max_pages is not None and max_pages > 0
            else "Extract transactions from all pages of the uploaded statement."
        )
        instructions = [
            scope_line,
            "Each shipment transaction starts with shipment date and tracking number and is separated by a full-width horizontal line.",
            "For each shipment, capture: shipment date, tracking number, shipped-from address block, shipped-to address block, piece count, billed weight, service description, full detailed charge lines, shipment total, Ref 1, Ref 2, manifest number, and billing notes.",
            "For Purolator French statements, map labels: 'Date d'expedition', 'No d'envoi', 'Expedie de', 'Expedie a', 'Nbre de pieces', 'Poids facture', 'Description du service', 'QTE/Tarif par unite', 'Total des frais', 'REF. 1', and 'REF. 2'.",
            "Preserve tracking numbers and references as strings exactly as shown (including leading zeros or mixed letters).",
            "Return addresses as complete multiline blocks merged into a single string with newline separators.",
            "Return monetary values as decimals without currency symbols.",
            "If a field is missing for a shipment, return null for that field rather than inventing data.",
        ]

        if carrier == "purolator":
            instructions.append(
                "Set carrier to 'purolator' and extract statement-level account number, invoice number/date, due date, and amount due when present."
            )

        if additional_instructions and additional_instructions.strip():
            instructions.append(f"Additional request: {additional_instructions.strip()}")

        return "\n".join(f"- {line}" for line in instructions)

    @staticmethod
    def _build_carrier_statement_chunk_instructions(
        *,
        base_instructions: str,
        chunk_index: int,
        total_chunks: int,
        start_page: int,
        end_page: int,
    ) -> str:
        page_scope = (
            f"This extraction call is chunk {chunk_index}/{total_chunks} and only covers page {start_page}."
            if start_page == end_page
            else (
                f"This extraction call is chunk {chunk_index}/{total_chunks} and only covers pages "
                f"{start_page}-{end_page}."
            )
        )
        chunk_rules = [
            page_scope,
            "Extract only shipment transactions visible in this chunk.",
            "Do not infer transactions from other pages.",
            "If statement-level fields are absent in this chunk, return null for those fields.",
        ]
        return "\n".join([base_instructions, *[f"- {rule}" for rule in chunk_rules]])
    
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

                elif document_type == "carrier_account_statement":
                    required_fields = ["carrier", "shipments"]
                    for field in required_fields:
                        if field not in extracted_data or extracted_data[field] in (None, "", []):
                            return False, f"Missing required field: {field}"
                    shipments = extracted_data.get("shipments", [])
                    if not shipments:
                        return False, "Carrier statement must include at least one shipment"
                    for index, shipment in enumerate(shipments, start=1):
                        if not shipment.get("tracking_number"):
                            return False, f"Shipment #{index} missing required field: tracking_number"
                        if shipment.get("total_charges") in (None, ""):
                            return False, f"Shipment #{index} missing required field: total_charges"
                        if shipment.get("shipped_from_address") in (None, ""):
                            return False, f"Shipment #{index} missing required field: shipped_from_address"
                        if shipment.get("shipped_to_address") in (None, ""):
                            return False, f"Shipment #{index} missing required field: shipped_to_address"
                
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
                logfire.error(
                    "Validation error",
                    document_type=document_type,
                    error=str(e),
                )
                return False, str(e)

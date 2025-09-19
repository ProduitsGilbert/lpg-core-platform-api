"""
OpenAI-based OCR client for document extraction.

This adapter uses OpenAI's GPT models with structured output to extract
data from PDF and image documents.
"""

import io
from typing import Dict, Any, Type
import time
import logfire
from openai import OpenAI
from pydantic import BaseModel

from app.ports import OCRClientProtocol
from app.domain.ocr.models import (
    PurchaseOrderExtraction,
    InvoiceExtraction
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
            purpose="vision"
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
                            {
                                "type": "input_image",
                                "image": {
                                    "file_id": uploaded_file.id,
                                    "detail": "high"
                                }
                            }
                        ]
                    }
                ],
                text_format=response_model
            )

            return response.output_parsed

        finally:
            self._cleanup_document(uploaded_file.id)

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

"""
OCR client adapter for document processing.

This module provides integration with OCR services (Tesseract/Azure)
for extracting text and data from scanned documents, invoices, and receipts.
"""

import base64
from typing import Dict, Any, List, Optional
from pathlib import Path
import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)
import logging

logger = logging.getLogger(__name__)

from app.settings import settings
from app.errors import ExternalServiceException


class OCRClient:
    """
    OCR service client for document text extraction.
    
    Supports both local Tesseract and cloud-based Azure OCR services.
    """
    
    def __init__(self, service_url: Optional[str] = None):
        """
        Initialize OCR client.
        
        Args:
            service_url: Override OCR service URL from settings
        """
        self.service_url = service_url or settings.ocr_service_url
        self._enabled = settings.enable_ocr and bool(self.service_url)
        
        if self._enabled:
            self.http_client = httpx.Client(
                base_url=self.service_url,
                timeout=settings.request_timeout,
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json"
                }
            )
        else:
            self.http_client = None
    
    def __del__(self):
        """Clean up HTTP client on deletion."""
        if hasattr(self, 'http_client') and self.http_client:
            self.http_client.close()
    
    @property
    def enabled(self) -> bool:
        """Check if OCR is enabled."""
        return self._enabled
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, max=30),
        retry=retry_if_exception_type(httpx.TimeoutException)
    )
    def extract_text(
        self,
        document: bytes,
        document_type: str = "generic",
        language: str = "en"
    ) -> Dict[str, Any]:
        """
        Extract text from a document using OCR.
        
        Args:
            document: Document bytes (PDF, image, etc.)
            document_type: Type of document (invoice, receipt, po, generic)
            language: Language hint for OCR (ISO 639-1 code)
        
        Returns:
            Dictionary with extracted text and metadata
        
        Raises:
            ExternalServiceException: If OCR service fails
        """
        if not self.enabled:
            raise ExternalServiceException(
                "OCR",
                "OCR service is not enabled or configured"
            )
        
        with logfire.span(
            "OCR extract_text",
            document_type=document_type,
            document_size=len(document),
            language=language
        ):
            try:
                # Encode document as base64 for transmission
                document_b64 = base64.b64encode(document).decode("utf-8")
                
                response = self.http_client.post(
                    "/extract",
                    json={
                        "document": document_b64,
                        "type": document_type,
                        "language": language
                    }
                )
                response.raise_for_status()
                
                result = response.json()
                logfire.info(
                    "OCR extraction successful",
                    pages=result.get("page_count", 1),
                    confidence=result.get("confidence")
                )
                
                return result
                
            except httpx.HTTPStatusError as e:
                logfire.error(f"OCR service HTTP error: {e.response.status_code}")
                raise ExternalServiceException(
                    "OCR",
                    f"HTTP {e.response.status_code}: {e.response.text}",
                    context={"status_code": e.response.status_code}
                )
            except httpx.TimeoutException:
                logfire.error("OCR service timeout")
                raise ExternalServiceException("OCR", "Service timeout")
            except Exception as e:
                logfire.error(f"OCR service error: {str(e)}")
                raise ExternalServiceException("OCR", str(e))
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, max=30),
        retry=retry_if_exception_type(httpx.TimeoutException)
    )
    def extract_invoice_data(
        self,
        document: bytes,
        hints: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Extract structured data from an invoice document.
        
        Args:
            document: Invoice document bytes
            hints: Optional hints for extraction (vendor name, PO number, etc.)
        
        Returns:
            Structured invoice data including:
            - vendor_info: Vendor details
            - invoice_number: Invoice identifier
            - invoice_date: Invoice date
            - po_number: Referenced PO if found
            - line_items: List of invoice lines
            - total_amount: Invoice total
        
        Raises:
            ExternalServiceException: If OCR service fails
        """
        if not self.enabled:
            # Return stub data for development
            return {
                "vendor_info": {
                    "name": "Sample Vendor",
                    "address": "123 Main St",
                    "tax_id": "XX-XXXXXXX"
                },
                "invoice_number": "INV-2024-001",
                "invoice_date": "2024-01-15",
                "po_number": hints.get("po_number") if hints else None,
                "line_items": [
                    {
                        "description": "Sample Item",
                        "quantity": 10,
                        "unit_price": 25.50,
                        "amount": 255.00
                    }
                ],
                "total_amount": 255.00,
                "confidence": 0.95
            }
        
        with logfire.span(
            "OCR extract_invoice_data",
            document_size=len(document),
            has_hints=bool(hints)
        ):
            try:
                document_b64 = base64.b64encode(document).decode("utf-8")
                
                response = self.http_client.post(
                    "/extract/invoice",
                    json={
                        "document": document_b64,
                        "hints": hints or {}
                    }
                )
                response.raise_for_status()
                
                result = response.json()
                logfire.info(
                    "Invoice extraction successful",
                    invoice_number=result.get("invoice_number"),
                    line_count=len(result.get("line_items", [])),
                    confidence=result.get("confidence")
                )
                
                return result
                
            except httpx.HTTPStatusError as e:
                logfire.error(f"Invoice extraction HTTP error: {e.response.status_code}")
                raise ExternalServiceException(
                    "OCR",
                    f"Invoice extraction failed: {e.response.status_code}",
                    context={"status_code": e.response.status_code}
                )
            except Exception as e:
                logfire.error(f"Invoice extraction error: {str(e)}")
                raise ExternalServiceException("OCR", f"Invoice extraction error: {str(e)}")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, max=30),
        retry=retry_if_exception_type(httpx.TimeoutException)
    )
    def extract_receipt_data(
        self,
        document: bytes,
        po_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extract structured data from a receipt/packing slip.
        
        Args:
            document: Receipt document bytes
            po_id: Optional PO ID to match against
        
        Returns:
            Structured receipt data including:
            - vendor_info: Vendor details
            - receipt_number: Receipt/packing slip number
            - receipt_date: Receipt date
            - po_number: Referenced PO
            - items: List of received items
        
        Raises:
            ExternalServiceException: If OCR service fails
        """
        if not self.enabled:
            # Return stub data for development
            return {
                "vendor_info": {
                    "name": "Sample Vendor"
                },
                "receipt_number": "REC-2024-001",
                "receipt_date": "2024-01-15",
                "po_number": po_id,
                "items": [
                    {
                        "item_number": "ITEM-001",
                        "description": "Sample Item",
                        "quantity": 10
                    }
                ],
                "confidence": 0.92
            }
        
        with logfire.span(
            "OCR extract_receipt_data",
            document_size=len(document),
            po_id=po_id
        ):
            try:
                document_b64 = base64.b64encode(document).decode("utf-8")
                
                response = self.http_client.post(
                    "/extract/receipt",
                    json={
                        "document": document_b64,
                        "po_id": po_id
                    }
                )
                response.raise_for_status()
                
                result = response.json()
                logfire.info(
                    "Receipt extraction successful",
                    receipt_number=result.get("receipt_number"),
                    item_count=len(result.get("items", [])),
                    confidence=result.get("confidence")
                )
                
                return result
                
            except httpx.HTTPStatusError as e:
                logfire.error(f"Receipt extraction HTTP error: {e.response.status_code}")
                raise ExternalServiceException(
                    "OCR",
                    f"Receipt extraction failed: {e.response.status_code}",
                    context={"status_code": e.response.status_code}
                )
            except Exception as e:
                logfire.error(f"Receipt extraction error: {str(e)}")
                raise ExternalServiceException("OCR", f"Receipt extraction error: {str(e)}")
    
    def validate_document(self, document: bytes) -> Dict[str, Any]:
        """
        Validate if a document is suitable for OCR processing.
        
        Args:
            document: Document bytes to validate
        
        Returns:
            Validation result with:
            - valid: Boolean indicating if document is valid
            - format: Detected document format
            - size: Document size in bytes
            - issues: List of any validation issues
        """
        issues = []
        
        # Check document size
        size = len(document)
        if size == 0:
            issues.append("Document is empty")
        elif size > 10 * 1024 * 1024:  # 10MB limit
            issues.append("Document exceeds 10MB size limit")
        
        # Detect format from magic bytes
        format_detected = "unknown"
        if document[:4] == b"%PDF":
            format_detected = "pdf"
        elif document[:2] in [b"\xff\xd8", b"\x89\x50"]:  # JPEG or PNG
            format_detected = "image"
        elif document[:4] == b"II\x2a\x00" or document[:4] == b"MM\x00\x2a":  # TIFF
            format_detected = "tiff"
        else:
            issues.append("Unsupported document format")
        
        return {
            "valid": len(issues) == 0,
            "format": format_detected,
            "size": size,
            "issues": issues
        }
    
    def health_check(self) -> bool:
        """
        Check if OCR service is healthy and reachable.
        
        Returns:
            True if service is healthy, False otherwise
        """
        if not self.enabled:
            return False
        
        try:
            response = self.http_client.get("/health", timeout=5)
            return response.status_code == 200
        except Exception as e:
            logfire.warning(f"OCR health check failed: {str(e)}")
            return False
"""
OCR document processing service.

This service handles the business logic for extracting structured data
from documents using AI/LLM models.
"""

from typing import Dict, Any, Optional
import logfire
from pydantic import BaseModel

from app.ports import OCRClientProtocol
from app.domain.ocr.models import OCRExtractionResponse


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
        filename: str
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
                    filename=filename
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
    
    def extract_custom_document(
        self,
        file_content: bytes,
        filename: str,
        document_type: str,
        output_model: BaseModel
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
                    output_model=output_model
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

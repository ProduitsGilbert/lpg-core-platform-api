"""
API endpoints for OCR document extraction.

These endpoints handle document uploads and extraction using AI/LLM models.
"""

from typing import Optional
from datetime import datetime
import json
import logfire
from fastapi import APIRouter, File, UploadFile, HTTPException, Depends, Form
from fastapi.responses import JSONResponse

from app.settings import settings
from app.adapters.ocr.openai_ocr_client import OpenAIOCRClient
from app.domain.ocr.ocr_service import OCRService
from app.domain.ocr.models import (
    OCRExtractionResponse,
    PurchaseOrderExtraction,
    InvoiceExtraction
)
from app.domain.ocr.schema_utils import build_pydantic_model_from_schema


router = APIRouter(
    prefix="/ocr/documents",
    tags=["OCR"]
)

ALLOWED_EXTENSIONS = ('.pdf', '.png', '.jpg', '.jpeg', '.tiff')
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024
MAX_CONTRACT_FILE_SIZE_BYTES = 50 * 1024 * 1024
DOCUMENT_HANDLER_MAP = {
    "purchase_order": "extract_purchase_order",
    "invoice": "extract_invoice",
    "supplier_account_statement": "extract_supplier_account_statement",
    "customer_account_statement": "extract_customer_account_statement",
    "supplier_invoice": "extract_supplier_invoice",
    "vendor_quote": "extract_vendor_quote",
    "order_confirmation": "extract_order_confirmation",
    "shipping_bill": "extract_shipping_bill",
    "commercial_invoice": "extract_commercial_invoice",
    "complex_document": "extract_complex_document",
}


async def _read_and_validate_upload(file: UploadFile) -> bytes:
    """Ensure uploaded file is supported and within size limits."""
    if not file.filename.lower().endswith(ALLOWED_EXTENSIONS):
        raise HTTPException(
            status_code=400,
            detail="File must be PDF or image format (PNG, JPG, JPEG, TIFF)"
        )

    file_content = await file.read()
    if len(file_content) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=400,
            detail="File size must not exceed 10MB"
        )
    return file_content


async def _read_and_validate_contract_pdf(file: UploadFile) -> bytes:
    """Validate a (potentially large) contract PDF upload."""
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="File must be PDF format (.pdf)",
        )

    file_content = await file.read()
    if len(file_content) > MAX_CONTRACT_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=400,
            detail="File size must not exceed 50MB for contract extraction",
        )
    return file_content


def get_ocr_service() -> OCRService:
    """
    Dependency to get OCR service instance.
    
    Returns:
        Configured OCR service
    """
    ocr_client = OpenAIOCRClient(
        api_key=settings.openai_api_key,
        model=settings.ocr_llm_model
    )
    return OCRService(ocr_client=ocr_client)


@router.post("/purchase-orders/extract", response_model=OCRExtractionResponse)
async def extract_purchase_order(
    file: UploadFile = File(..., description="PDF or image file containing the purchase order"),
    additional_instructions: Optional[str] = Form(None, description="Additional extraction instructions"),
    ocr_service: OCRService = Depends(get_ocr_service)
):
    """
    Extract structured data from a purchase order document.
    
    This endpoint processes PDF or image files containing purchase orders
    and extracts structured information including:
    - PO number, date, and vendor information
    - Line items with quantities and prices
    - Payment and shipping terms
    - Total amounts
    
    Args:
        file: Uploaded purchase order document
        additional_instructions: Optional additional extraction guidance
        
    Returns:
        OCRExtractionResponse with extracted purchase order data
    """
    with logfire.span('api_extract_purchase_order'):
        try:
            # Validate file type
            file_content = await _read_and_validate_upload(file)

            logfire.info(f'Processing PO extraction for file: {file.filename}')
            
            # Extract data
            result = ocr_service.extract_purchase_order(
                file_content=file_content,
                filename=file.filename
            )
            
            # Validate extraction if successful
            if result.success:
                is_valid, error_msg = ocr_service.validate_extraction(
                    result.extracted_data,
                    "purchase_order"
                )
                if not is_valid:
                    result.success = False
                    result.error_message = f"Validation failed: {error_msg}"
            
            return JSONResponse(
                status_code=200 if result.success else 422,
                content={
                    "data": result.model_dump(mode="json"),
                    "meta": {
                        "timestamp": datetime.utcnow().isoformat(),
                        "version": "1.0",
                        "document_type": "purchase_order",
                        "filename": file.filename
                    }
                }
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logfire.error(f'Failed to extract PO: {str(e)}')
            raise HTTPException(
                status_code=500,
                detail=f"Failed to extract purchase order: {str(e)}"
            )


@router.post("/invoices/extract", response_model=OCRExtractionResponse)
async def extract_invoice(
    file: UploadFile = File(..., description="PDF or image file containing the invoice"),
    additional_instructions: Optional[str] = Form(None, description="Additional extraction instructions"),
    ocr_service: OCRService = Depends(get_ocr_service)
):
    """
    Extract structured data from an invoice document.
    
    This endpoint processes PDF or image files containing invoices
    and extracts structured information including:
    - Invoice number, date, and vendor information
    - Line items with quantities and prices
    - Tax calculations
    - Payment terms and bank details
    - Total amounts
    
    Args:
        file: Uploaded invoice document
        additional_instructions: Optional additional extraction guidance
        
    Returns:
        OCRExtractionResponse with extracted invoice data
    """
    with logfire.span('api_extract_invoice'):
        try:
            # Validate file type
            file_content = await _read_and_validate_upload(file)

            logfire.info(f'Processing invoice extraction for file: {file.filename}')
            
            # Extract data
            result = ocr_service.extract_invoice(
                file_content=file_content,
                filename=file.filename
            )
            
            # Validate extraction if successful
            if result.success:
                is_valid, error_msg = ocr_service.validate_extraction(
                    result.extracted_data,
                    "invoice"
                )
                if not is_valid:
                    result.success = False
                    result.error_message = f"Validation failed: {error_msg}"
            
            return JSONResponse(
                status_code=200 if result.success else 422,
                content={
                    "data": result.model_dump(mode="json"),
                    "meta": {
                        "timestamp": datetime.utcnow().isoformat(),
                        "version": "1.0",
                        "document_type": "invoice",
                        "filename": file.filename
                    }
                }
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logfire.error(f'Failed to extract invoice: {str(e)}')
            raise HTTPException(
                status_code=500,
                detail=f"Failed to extract invoice: {str(e)}"
            )


@router.post("/customer-payment-terms/extract", response_model=OCRExtractionResponse)
async def extract_customer_payment_terms(
    file: UploadFile = File(..., description="PDF contract document containing customer payment terms"),
    additional_instructions: Optional[str] = Form(None, description="Additional extraction instructions"),
    ocr_service: OCRService = Depends(get_ocr_service),
):
    """
    Extract customer payment terms + total contract amount from a contract PDF.

    Returns:
    - payment_terms_text (verbatim)
    - milestones (percent/amount + timing)
    - total_amount (+ currency if present)
    """
    with logfire.span('api_extract_customer_payment_terms'):
        try:
            file_content = await _read_and_validate_contract_pdf(file)

            logfire.info(f'Processing customer payment terms extraction for file: {file.filename}')

            result = ocr_service.extract_customer_payment_terms_contract(
                file_content=file_content,
                filename=file.filename,
                additional_instructions=additional_instructions,
            )

            return JSONResponse(
                status_code=200 if result.success else 422,
                content={
                    "data": result.model_dump(mode="json"),
                    "meta": {
                        "timestamp": datetime.utcnow().isoformat(),
                        "version": "1.0",
                        "document_type": "customer_payment_terms_contract",
                        "filename": file.filename,
                    },
                },
            )

        except HTTPException:
            raise
        except Exception as e:
            logfire.error(f'Failed to extract customer payment terms: {str(e)}')
            raise HTTPException(
                status_code=500,
                detail=f"Failed to extract customer payment terms: {str(e)}",
            )


@router.post("/supplier-account-statements/extract", response_model=OCRExtractionResponse)
async def extract_supplier_account_statement(
    file: UploadFile = File(..., description="PDF or image file containing the supplier account statement"),
    additional_instructions: Optional[str] = Form(None, description="Additional extraction instructions"),
    ocr_service: OCRService = Depends(get_ocr_service)
):
    """Extract structured data from supplier account statements."""
    with logfire.span('api_extract_supplier_account_statement'):
        try:
            file_content = await _read_and_validate_upload(file)
            logfire.info(f'Processing supplier account statement for file: {file.filename}')

            result = ocr_service.extract_supplier_account_statement(
                file_content=file_content,
                filename=file.filename,
                additional_instructions=additional_instructions,
            )

            if result.success:
                is_valid, error_msg = ocr_service.validate_extraction(
                    result.extracted_data,
                    "supplier_account_statement"
                )
                if not is_valid:
                    result.success = False
                    result.error_message = f"Validation failed: {error_msg}"

            return JSONResponse(
                status_code=200 if result.success else 422,
                content={
                    "data": result.model_dump(mode="json"),
                    "meta": {
                        "timestamp": datetime.utcnow().isoformat(),
                        "version": "1.0",
                        "document_type": "supplier_account_statement",
                        "filename": file.filename
                    }
                }
            )

        except HTTPException:
            raise
        except Exception as e:
            logfire.error(f'Failed to extract supplier account statement: {str(e)}')
            raise HTTPException(
                status_code=500,
                detail=f"Failed to extract supplier account statement: {str(e)}"
            )


@router.post("/customer-account-statements/extract", response_model=OCRExtractionResponse)
async def extract_customer_account_statement(
    file: UploadFile = File(..., description="PDF or image file containing the customer account statement"),
    additional_instructions: Optional[str] = Form(None, description="Additional extraction instructions"),
    ocr_service: OCRService = Depends(get_ocr_service)
):
    """Extract structured data from customer account statements."""
    with logfire.span('api_extract_customer_account_statement'):
        try:
            file_content = await _read_and_validate_upload(file)
            logfire.info(f'Processing customer account statement for file: {file.filename}')

            result = ocr_service.extract_customer_account_statement(
                file_content=file_content,
                filename=file.filename
            )

            if result.success:
                is_valid, error_msg = ocr_service.validate_extraction(
                    result.extracted_data,
                    "customer_account_statement"
                )
                if not is_valid:
                    result.success = False
                    result.error_message = f"Validation failed: {error_msg}"

            return JSONResponse(
                status_code=200 if result.success else 422,
                content={
                    "data": result.model_dump(mode="json"),
                    "meta": {
                        "timestamp": datetime.utcnow().isoformat(),
                        "version": "1.0",
                        "document_type": "customer_account_statement",
                        "filename": file.filename
                    }
                }
            )

        except HTTPException:
            raise
        except Exception as e:
            logfire.error(f'Failed to extract customer account statement: {str(e)}')
            raise HTTPException(
                status_code=500,
                detail=f"Failed to extract customer account statement: {str(e)}"
            )


@router.post("/supplier-invoices/extract", response_model=OCRExtractionResponse)
async def extract_supplier_invoice(
    file: UploadFile = File(..., description="PDF or image file containing the supplier invoice"),
    additional_instructions: Optional[str] = Form(None, description="Additional extraction instructions"),
    ocr_service: OCRService = Depends(get_ocr_service)
):
    """Extract structured data from supplier invoices."""
    with logfire.span('api_extract_supplier_invoice'):
        try:
            file_content = await _read_and_validate_upload(file)
            logfire.info(f'Processing supplier invoice for file: {file.filename}')

            result = ocr_service.extract_supplier_invoice(
                file_content=file_content,
                filename=file.filename
            )

            if result.success:
                is_valid, error_msg = ocr_service.validate_extraction(
                    result.extracted_data,
                    "supplier_invoice"
                )
                if not is_valid:
                    result.success = False
                    result.error_message = f"Validation failed: {error_msg}"

            return JSONResponse(
                status_code=200 if result.success else 422,
                content={
                    "data": result.model_dump(mode="json"),
                    "meta": {
                        "timestamp": datetime.utcnow().isoformat(),
                        "version": "1.0",
                        "document_type": "supplier_invoice",
                        "filename": file.filename
                    }
                }
            )

        except HTTPException:
            raise
        except Exception as e:
            logfire.error(f'Failed to extract supplier invoice: {str(e)}')
            raise HTTPException(
                status_code=500,
                detail=f"Failed to extract supplier invoice: {str(e)}"
            )


@router.post("/vendor-quotes/extract", response_model=OCRExtractionResponse)
async def extract_vendor_quote(
    file: UploadFile = File(..., description="PDF or image file containing the vendor quote"),
    additional_instructions: Optional[str] = Form(None, description="Additional extraction instructions"),
    ocr_service: OCRService = Depends(get_ocr_service)
):
    """Extract structured data from vendor quotes."""
    with logfire.span('api_extract_vendor_quote'):
        try:
            file_content = await _read_and_validate_upload(file)
            logfire.info(f'Processing vendor quote for file: {file.filename}')

            result = ocr_service.extract_vendor_quote(
                file_content=file_content,
                filename=file.filename,
                additional_instructions=additional_instructions,
            )

            if result.success:
                is_valid, error_msg = ocr_service.validate_extraction(
                    result.extracted_data,
                    "vendor_quote"
                )
                if not is_valid:
                    result.success = False
                    result.error_message = f"Validation failed: {error_msg}"

            return JSONResponse(
                status_code=200 if result.success else 422,
                content={
                    "data": result.model_dump(mode="json"),
                    "meta": {
                        "timestamp": datetime.utcnow().isoformat(),
                        "version": "1.0",
                        "document_type": "vendor_quote",
                        "filename": file.filename
                    }
                }
            )

        except HTTPException:
            raise
        except Exception as e:
            logfire.error(f'Failed to extract vendor quote: {str(e)}')
            raise HTTPException(
                status_code=500,
                detail=f"Failed to extract vendor quote: {str(e)}"
            )


@router.post("/order-confirmations/extract", response_model=OCRExtractionResponse)
async def extract_order_confirmation(
    file: UploadFile = File(..., description="PDF or image file containing the order confirmation"),
    additional_instructions: Optional[str] = Form(None, description="Additional extraction instructions"),
    ocr_service: OCRService = Depends(get_ocr_service)
):
    """Extract structured data from order confirmations."""
    with logfire.span('api_extract_order_confirmation'):
        try:
            file_content = await _read_and_validate_upload(file)
            logfire.info(f'Processing order confirmation for file: {file.filename}')

            result = ocr_service.extract_order_confirmation(
                file_content=file_content,
                filename=file.filename,
                additional_instructions=additional_instructions,
            )

            if result.success:
                is_valid, error_msg = ocr_service.validate_extraction(
                    result.extracted_data,
                    "order_confirmation"
                )
                if not is_valid:
                    result.success = False
                    result.error_message = f"Validation failed: {error_msg}"

            return JSONResponse(
                status_code=200 if result.success else 422,
                content={
                    "data": result.model_dump(mode="json"),
                    "meta": {
                        "timestamp": datetime.utcnow().isoformat(),
                        "version": "1.0",
                        "document_type": "order_confirmation",
                        "filename": file.filename
                    }
                }
            )

        except HTTPException:
            raise
        except Exception as e:
            logfire.error(f'Failed to extract order confirmation: {str(e)}')
            raise HTTPException(
                status_code=500,
                detail=f"Failed to extract order confirmation: {str(e)}"
            )


@router.post("/shipping-bills/extract", response_model=OCRExtractionResponse)
async def extract_shipping_bill(
    file: UploadFile = File(..., description="PDF or image file containing the shipping bill"),
    additional_instructions: Optional[str] = Form(None, description="Additional extraction instructions"),
    ocr_service: OCRService = Depends(get_ocr_service)
):
    """Extract structured data from shipping bills."""
    with logfire.span('api_extract_shipping_bill'):
        try:
            file_content = await _read_and_validate_upload(file)
            logfire.info(f'Processing shipping bill for file: {file.filename}')

            result = ocr_service.extract_shipping_bill(
                file_content=file_content,
                filename=file.filename
            )

            if result.success:
                is_valid, error_msg = ocr_service.validate_extraction(
                    result.extracted_data,
                    "shipping_bill"
                )
                if not is_valid:
                    result.success = False
                    result.error_message = f"Validation failed: {error_msg}"

            return JSONResponse(
                status_code=200 if result.success else 422,
                content={
                    "data": result.model_dump(mode="json"),
                    "meta": {
                        "timestamp": datetime.utcnow().isoformat(),
                        "version": "1.0",
                        "document_type": "shipping_bill",
                        "filename": file.filename
                    }
                }
            )

        except HTTPException:
            raise
        except Exception as e:
            logfire.error(f'Failed to extract shipping bill: {str(e)}')
            raise HTTPException(
                status_code=500,
                detail=f"Failed to extract shipping bill: {str(e)}"
            )


@router.post("/commercial-invoices/extract", response_model=OCRExtractionResponse)
async def extract_commercial_invoice(
    file: UploadFile = File(..., description="PDF or image file containing the commercial invoice"),
    additional_instructions: Optional[str] = Form(None, description="Additional extraction instructions"),
    ocr_service: OCRService = Depends(get_ocr_service)
):
    """Extract structured data from commercial invoices."""
    with logfire.span('api_extract_commercial_invoice'):
        try:
            file_content = await _read_and_validate_upload(file)
            logfire.info(f'Processing commercial invoice for file: {file.filename}')

            result = ocr_service.extract_commercial_invoice(
                file_content=file_content,
                filename=file.filename
            )

            if result.success:
                is_valid, error_msg = ocr_service.validate_extraction(
                    result.extracted_data,
                    "commercial_invoice"
                )
                if not is_valid:
                    result.success = False
                    result.error_message = f"Validation failed: {error_msg}"

            return JSONResponse(
                status_code=200 if result.success else 422,
                content={
                    "data": result.model_dump(mode="json"),
                    "meta": {
                        "timestamp": datetime.utcnow().isoformat(),
                        "version": "1.0",
                        "document_type": "commercial_invoice",
                        "filename": file.filename
                    }
                }
            )

        except HTTPException:
            raise
        except Exception as e:
            logfire.error(f'Failed to extract commercial invoice: {str(e)}')
            raise HTTPException(
                status_code=500,
                detail=f"Failed to extract commercial invoice: {str(e)}"
            )


@router.post("/complex/extract", response_model=OCRExtractionResponse)
async def extract_complex_document(
    file: UploadFile = File(..., description="PDF or image file containing a complex document"),
    additional_instructions: Optional[str] = Form(None, description="Additional extraction instructions"),
    ocr_service: OCRService = Depends(get_ocr_service),
):
    """
    Extract layout-aware content from complex documents, including text, tables, and figures.
    """
    with logfire.span('api_extract_complex_document'):
        try:
            file_content = await _read_and_validate_upload(file)
            logfire.info(f'Processing complex document extraction for file: {file.filename}')

            result = ocr_service.extract_complex_document(
                file_content=file_content,
                filename=file.filename,
                additional_instructions=additional_instructions,
            )

            return JSONResponse(
                status_code=200 if result.success else 422,
                content={
                    "data": result.model_dump(mode="json"),
                    "meta": {
                        "timestamp": datetime.utcnow().isoformat(),
                        "version": "1.0",
                        "document_type": "complex_document",
                        "filename": file.filename,
                    },
                },
            )

        except HTTPException:
            raise
        except Exception as e:
            logfire.error(f'Failed to extract complex document: {str(e)}')
            raise HTTPException(
                status_code=500,
                detail=f"Failed to extract complex document: {str(e)}",
            )


@router.post("/custom/extract", response_model=OCRExtractionResponse)
async def extract_custom_document(
    file: UploadFile = File(..., description="PDF or image file to process"),
    document_type: str = Form(..., description="Document type label used to guide extraction"),
    output_schema: str = Form(..., description="JSON schema defining expected output structure"),
    additional_instructions: Optional[str] = Form(None, description="Additional extraction instructions"),
    ocr_service: OCRService = Depends(get_ocr_service),
):
    """
    Extract structured data from any document using a custom JSON schema.
    """
    with logfire.span('api_extract_custom_document'):
        try:
            file_content = await _read_and_validate_upload(file)
            logfire.info(f'Processing custom extraction for file: {file.filename}')

            try:
                schema_dict = json.loads(output_schema)
            except json.JSONDecodeError as exc:
                raise HTTPException(
                    status_code=400,
                    detail=f"output_schema must be valid JSON: {exc.msg}"
                ) from exc

            try:
                output_model = build_pydantic_model_from_schema(
                    schema_dict,
                    model_name=f"{document_type.title().replace('-', '').replace('_', '')}Extraction",
                )
            except ValueError as exc:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid output_schema: {exc}"
                ) from exc

            result = ocr_service.extract_custom_document(
                file_content=file_content,
                filename=file.filename,
                document_type=document_type,
                output_model=output_model,
                additional_instructions=additional_instructions,
            )

            return JSONResponse(
                status_code=200 if result.success else 422,
                content={
                    "data": result.model_dump(mode="json"),
                    "meta": {
                        "timestamp": datetime.utcnow().isoformat(),
                        "version": "1.0",
                        "document_type": document_type,
                        "filename": file.filename,
                    },
                },
            )

        except HTTPException:
            raise
        except Exception as e:
            logfire.error(f'Failed to extract custom document: {str(e)}')
            raise HTTPException(
                status_code=500,
                detail=f"Failed to extract custom document: {str(e)}",
            )

@router.post("/batch/extract")
async def extract_batch_documents(
    files: list[UploadFile] = File(..., description="Multiple PDF or image files"),
    document_type: str = Form(..., description="Type of documents (e.g., purchase_order, supplier_invoice)"),
    ocr_service: OCRService = Depends(get_ocr_service)
):
    """
    Extract structured data from multiple documents in batch.
    
    This endpoint processes multiple PDF or image files and extracts
    structured information from each document.
    
    Args:
        files: List of uploaded documents
        document_type: Type of documents being processed
        
    Returns:
        Batch extraction results
    """
    with logfire.span('api_extract_batch_documents'):
        try:
            if document_type not in DOCUMENT_HANDLER_MAP:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported document type. Supported types: {', '.join(DOCUMENT_HANDLER_MAP.keys())}"
                )
            
            if len(files) > 10:
                raise HTTPException(
                    status_code=400,
                    detail="Maximum 10 files allowed per batch"
                )
            
            results = []
            
            for file in files:
                try:
                    # Read file content
                    file_content = await _read_and_validate_upload(file)
                    
                    # Extract based on document type
                    handler_name = DOCUMENT_HANDLER_MAP[document_type]
                    handler = getattr(ocr_service, handler_name)
                    result = handler(
                        file_content=file_content,
                        filename=file.filename
                    )
                    
                    results.append({
                        "filename": file.filename,
                        "success": result.success,
                        "data": result.model_dump(mode="json").get("extracted_data") if result.success else None,
                        "error": result.error_message if not result.success else None
                    })
                    
                except Exception as e:
                    results.append({
                        "filename": file.filename,
                        "success": False,
                        "error": str(e)
                    })
            
            successful = sum(1 for r in results if r["success"])
            
            return JSONResponse(
                status_code=200,
                content={
                    "data": {
                        "results": results,
                        "summary": {
                            "total": len(files),
                            "successful": successful,
                            "failed": len(files) - successful
                        }
                    },
                    "meta": {
                        "timestamp": datetime.utcnow().isoformat(),
                        "version": "1.0",
                        "document_type": document_type
                    }
                }
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logfire.error(f'Failed to process batch extraction: {str(e)}')
            raise HTTPException(
                status_code=500,
                detail=f"Failed to process batch extraction: {str(e)}"
            )


@router.get("/status")
async def get_ocr_status(ocr_service: OCRService = Depends(get_ocr_service)):
    """
    Check OCR service status and configuration.
    
    Returns:
        OCR service status information
    """
    try:
        return JSONResponse(
            status_code=200,
            content={
                "data": {
                    "enabled": ocr_service.ocr_client.enabled,
                    "model": settings.ocr_llm_model,
                    "supported_formats": ["pdf", "png", "jpg", "jpeg", "tiff"],
                    "max_file_size_mb": 10,
                    "max_batch_size": 10
                },
                "meta": {
                    "timestamp": datetime.utcnow().isoformat(),
                    "version": "1.0"
                }
            }
        )
    except Exception as e:
        logfire.error(f'Failed to get OCR status: {str(e)}')
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get OCR status: {str(e)}"
        )

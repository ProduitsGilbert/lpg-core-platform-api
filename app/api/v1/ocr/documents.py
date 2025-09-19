"""
API endpoints for OCR document extraction.

These endpoints handle document uploads and extraction using AI/LLM models.
"""

from typing import Optional
from datetime import datetime
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


router = APIRouter(
    prefix="/ocr/documents",
    tags=["OCR"]
)


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
            if not file.filename.lower().endswith(('.pdf', '.png', '.jpg', '.jpeg', '.tiff')):
                raise HTTPException(
                    status_code=400,
                    detail="File must be PDF or image format (PNG, JPG, JPEG, TIFF)"
                )
            
            # Check file size (max 10MB)
            file_content = await file.read()
            if len(file_content) > 10 * 1024 * 1024:
                raise HTTPException(
                    status_code=400,
                    detail="File size must not exceed 10MB"
                )
            
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
                    "data": result.model_dump(),
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
            if not file.filename.lower().endswith(('.pdf', '.png', '.jpg', '.jpeg', '.tiff')):
                raise HTTPException(
                    status_code=400,
                    detail="File must be PDF or image format (PNG, JPG, JPEG, TIFF)"
                )
            
            # Check file size (max 10MB)
            file_content = await file.read()
            if len(file_content) > 10 * 1024 * 1024:
                raise HTTPException(
                    status_code=400,
                    detail="File size must not exceed 10MB"
                )
            
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
                    "data": result.model_dump(),
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


@router.post("/batch/extract")
async def extract_batch_documents(
    files: list[UploadFile] = File(..., description="Multiple PDF or image files"),
    document_type: str = Form(..., description="Type of documents (purchase_order or invoice)"),
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
            if document_type not in ["purchase_order", "invoice"]:
                raise HTTPException(
                    status_code=400,
                    detail="Document type must be 'purchase_order' or 'invoice'"
                )
            
            if len(files) > 10:
                raise HTTPException(
                    status_code=400,
                    detail="Maximum 10 files allowed per batch"
                )
            
            results = []
            
            for file in files:
                # Validate file type
                if not file.filename.lower().endswith(('.pdf', '.png', '.jpg', '.jpeg', '.tiff')):
                    results.append({
                        "filename": file.filename,
                        "success": False,
                        "error": "Invalid file format"
                    })
                    continue
                
                try:
                    # Read file content
                    file_content = await file.read()
                    
                    # Check file size
                    if len(file_content) > 10 * 1024 * 1024:
                        results.append({
                            "filename": file.filename,
                            "success": False,
                            "error": "File size exceeds 10MB"
                        })
                        continue
                    
                    # Extract based on document type
                    if document_type == "purchase_order":
                        result = ocr_service.extract_purchase_order(
                            file_content=file_content,
                            filename=file.filename
                        )
                    else:
                        result = ocr_service.extract_invoice(
                            file_content=file_content,
                            filename=file.filename
                        )
                    
                    results.append({
                        "filename": file.filename,
                        "success": result.success,
                        "data": result.extracted_data if result.success else None,
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
"""
Documents File Share endpoints
Implements file sharing functionality for item PDFs and other documents
"""
from fastapi import APIRouter, Depends, HTTPException, Body
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import logging
import logfire
from typing import Optional, Dict, Any
import io

from app.deps import get_db
from app.domain.documents.file_share_service import FileShareService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/file-share", tags=["Documents - File Share"])

# Initialize service
file_share_service = FileShareService()

@router.get(
    "/items/{item_no}/pdf",
    responses={
        200: {
            "description": "PDF file retrieved successfully",
            "content": {"application/pdf": {}}
        },
        404: {"description": "Item or PDF not found"},
        500: {"description": "Internal server error"}
    },
    summary="Get item PDF file",
    description="""
    Retrieves the PDF documentation file for a specific item.
    
    This endpoint:
    - Fetches technical drawings, specifications, or documentation PDFs
    - Returns the file as a streaming response
    - Supports item datasheets, manuals, and certificates
    
    The PDF is retrieved from the internal file share or document management system.
    """
)
async def get_item_pdf_file(
    item_no: str,
    db: Session = Depends(get_db)
) -> StreamingResponse:
    """Get PDF file for an item"""
    try:
        with logfire.span(f"get_item_pdf_file", item_no=item_no):
            # Get PDF file from service
            pdf_data = await file_share_service.get_item_pdf(item_no)
            
        if not pdf_data:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": {
                        "code": "PDF_NOT_FOUND",
                        "message": f"PDF file not found for item '{item_no}'",
                        "trace_id": getattr(db, 'trace_id', 'unknown')
                    }
                }
            )
        
        # Return as streaming response
        return StreamingResponse(
            io.BytesIO(pdf_data["content"]),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'inline; filename="{pdf_data["filename"]}"',
                "Content-Length": str(pdf_data["size"]),
                "Cache-Control": "public, max-age=3600"  # Cache for 1 hour
            }
        )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching PDF for item {item_no}: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "INTERNAL_ERROR", 
                    "message": "Failed to retrieve PDF file",
                    "trace_id": getattr(db, 'trace_id', 'unknown')
                }
            }
        )

@router.get(
    "/items/{item_no}/technical-sheet",
    summary="Read technical sheet content",
    description="""
    Reads text content, form fields, and provides vision fallback for technical drawings.
    Useful for extracting data from PDF forms or drawings.
    """
)
async def read_technical_sheet(
    item_no: str,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Read technical sheet content"""
    try:
        with logfire.span(f"read_technical_sheet", item_no=item_no):
            result = await file_share_service.read_technical_sheet(item_no)
            
        if not result["success"]:
            # If it's a "not found" type error (though service returns generic error string), 
            # we might want 404, but service returns success=False for various reasons.
            # Assuming if PDF missing it's a 404 logic inside service, but let's check error message or adjust service.
            # For now, 400 or 404 based on error content? 
            # The service returns "PDF file not found..." in error string.
            if "not found" in (result.get("error") or "").lower():
                 raise HTTPException(
                    status_code=404,
                    detail={
                        "error": {
                            "code": "PDF_NOT_FOUND",
                            "message": result["error"],
                            "trace_id": getattr(db, 'trace_id', 'unknown')
                        }
                    }
                )
            
            raise HTTPException(
                status_code=500,
                detail={
                    "error": {
                        "code": "PROCESSING_ERROR",
                        "message": result["error"],
                        "trace_id": getattr(db, 'trace_id', 'unknown')
                    }
                }
            )
            
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reading technical sheet for {item_no}: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "INTERNAL_ERROR", 
                    "message": "Failed to read technical sheet",
                    "trace_id": getattr(db, 'trace_id', 'unknown')
                }
            }
        )

@router.post(
    "/items/{item_no}/technical-sheet",
    summary="Fill technical sheet form fields",
    description="""
    Fills the technical sheet PDF form fields with the provided data.
    Returns the filled PDF file.
    """
)
async def fill_technical_sheet(
    item_no: str,
    fields: Dict[str, Any] = Body(..., description="Key-value pairs for form fields"),
    db: Session = Depends(get_db)
) -> StreamingResponse:
    """Fill technical sheet form fields"""
    try:
        with logfire.span(f"fill_technical_sheet", item_no=item_no):
            result = await file_share_service.write_technical_sheet(item_no, fields)
            
        if not result["success"]:
            if "not found" in (result.get("error") or "").lower():
                 raise HTTPException(
                    status_code=404,
                    detail={
                        "error": {
                            "code": "PDF_NOT_FOUND",
                            "message": result["error"],
                            "trace_id": getattr(db, 'trace_id', 'unknown')
                        }
                    }
                )
            
            raise HTTPException(
                status_code=500,
                detail={
                    "error": {
                        "code": "PROCESSING_ERROR",
                        "message": result["error"],
                        "trace_id": getattr(db, 'trace_id', 'unknown')
                    }
                }
            )
        
        return StreamingResponse(
            io.BytesIO(result["content"]),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'inline; filename="{result["filename"]}"',
                "Content-Length": str(result["size"]),
                "Cache-Control": "no-cache"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error filling technical sheet for {item_no}: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "INTERNAL_ERROR", 
                    "message": "Failed to fill technical sheet",
                    "trace_id": getattr(db, 'trace_id', 'unknown')
                }
            }
        )

"""
Documents File Share endpoints
Implements file sharing functionality for item PDFs and other documents
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import logging
import logfire
from typing import Optional
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
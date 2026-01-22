"""
Documents File Share endpoints
Implements file sharing functionality for item PDFs and other documents.
Adds direct SMB access to the Windows NTFS file share.
"""
import base64
import io
import mimetypes
import os

from fastapi import APIRouter, Depends, HTTPException, Body, Query
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import logging
import logfire
from typing import Optional, Dict, Any

from pydantic import BaseModel

from app.deps import get_db
from app.domain.documents.file_share_service import FileShareService
from app.domain.documents.file_share_connector import (
    SMBFileShareConnector,
    FileShareConnectorError,
    FileShareDisabledError,
    FileSharePathError,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/file-share", tags=["Documents - File Share"])

# Initialize services
file_share_service = FileShareService()
file_share_connector = SMBFileShareConnector()


class FileWriteRequest(BaseModel):
    path: str
    content_base64: str
    overwrite: bool = True


class FileListResponse(BaseModel):
    name: str
    is_dir: bool
    size: int | None = None
    last_modified: Any | None = None
    path: str

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


@router.get(
    "/files",
    summary="Read a file from SMB share",
    description="Reads any file from the Windows NTFS SMB share using configured credentials.",
)
async def read_file_from_share(
    path: str = Query(..., description="Path inside the SMB share (relative to base path)"),
    db: Session = Depends(get_db)
) -> StreamingResponse:
    try:
        with logfire.span("file_share.read_file", path=path):
            content: bytes = await run_in_threadpool(file_share_connector.read_file, path)

        media_type = mimetypes.guess_type(path)[0] or "application/octet-stream"
        filename = os.path.basename(path) or "file"
        return StreamingResponse(
            io.BytesIO(content),
            media_type=media_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Length": str(len(content)),
            },
        )
    except FileShareDisabledError as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "error": {
                    "code": "FILE_SHARE_DISABLED",
                    "message": str(exc),
                    "trace_id": getattr(db, 'trace_id', 'unknown')
                }
            },
        )
    except FileSharePathError as exc:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": "FILE_NOT_FOUND",
                    "message": str(exc),
                    "trace_id": getattr(db, 'trace_id', 'unknown')
                }
            },
        )
    except FileShareConnectorError as exc:
        logger.error(f"SMB read error for path {path}: {exc}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "FILE_SHARE_ERROR",
                    "message": "Failed to read file from SMB share",
                    "trace_id": getattr(db, 'trace_id', 'unknown')
                }
            },
        )
    except Exception as exc:
        logger.error(f"Unexpected error reading file {path}: {exc}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "Unexpected error while reading file",
                    "trace_id": getattr(db, 'trace_id', 'unknown')
                }
            },
        )


@router.get(
    "/files/list",
    summary="List folder contents on SMB share",
    description="Lists files and subfolders inside the specified path on the Windows NTFS SMB share.",
)
async def list_files_on_share(
    path: str = Query("/", description="Directory path inside the SMB share (relative to base path)"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    try:
        with logfire.span("file_share.list_directory", path=path):
            entries = await run_in_threadpool(file_share_connector.list_directory, path)

        return {
            "success": True,
            "path": path,
            "entries": entries,
        }
    except FileShareDisabledError as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "error": {
                    "code": "FILE_SHARE_DISABLED",
                    "message": str(exc),
                    "trace_id": getattr(db, 'trace_id', 'unknown')
                }
            },
        )
    except FileSharePathError as exc:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": "FILE_NOT_FOUND",
                    "message": str(exc),
                    "trace_id": getattr(db, 'trace_id', 'unknown')
                }
            },
        )
    except FileShareConnectorError as exc:
        logger.error(f"SMB list error for path {path}: {exc}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "FILE_SHARE_ERROR",
                    "message": "Failed to list directory from SMB share",
                    "trace_id": getattr(db, 'trace_id', 'unknown')
                }
            },
        )
    except Exception as exc:
        logger.error(f"Unexpected error listing directory {path}: {exc}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "Unexpected error while listing directory",
                    "trace_id": getattr(db, 'trace_id', 'unknown')
                }
            },
        )


@router.put(
    "/files",
    summary="Write a file to SMB share",
    description="Writes a file to the Windows NTFS SMB share. Content must be base64 encoded.",
)
async def write_file_to_share(
    payload: FileWriteRequest,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    try:
        with logfire.span("file_share.write_file", path=payload.path, overwrite=payload.overwrite):
            try:
                content_bytes = base64.b64decode(payload.content_base64)
            except Exception:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": {
                            "code": "INVALID_BASE64",
                            "message": "content_base64 is not valid base64",
                            "trace_id": getattr(db, 'trace_id', 'unknown')
                        }
                    }
                )

            await run_in_threadpool(
                file_share_connector.write_file,
                payload.path,
                content_bytes,
                payload.overwrite,
            )

        return {
            "success": True,
            "path": payload.path,
            "size": len(content_bytes),
        }
    except FileShareDisabledError as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "error": {
                    "code": "FILE_SHARE_DISABLED",
                    "message": str(exc),
                    "trace_id": getattr(db, 'trace_id', 'unknown')
                }
            },
        )
    except FileSharePathError as exc:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": "FILE_PATH_ERROR",
                    "message": str(exc),
                    "trace_id": getattr(db, 'trace_id', 'unknown')
                }
            },
        )
    except FileShareConnectorError as exc:
        logger.error(f"SMB write error for path {payload.path}: {exc}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "FILE_SHARE_ERROR",
                    "message": "Failed to write file to SMB share",
                    "trace_id": getattr(db, 'trace_id', 'unknown')
                }
            },
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Unexpected error writing file {payload.path}: {exc}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "Unexpected error while writing file",
                    "trace_id": getattr(db, 'trace_id', 'unknown')
                }
            },
        )

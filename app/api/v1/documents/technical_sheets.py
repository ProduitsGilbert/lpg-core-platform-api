"""Technical sheet endpoints for reading and filling PDF forms."""

from datetime import datetime
import io
from typing import Any, Dict, Optional

import logfire
from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.deps import get_db
from app.domain.documents.technical_sheet_service import TechnicalSheetService

router = APIRouter(prefix="/technical-sheets", tags=["Documents - Technical Sheets"])

technical_sheet_service = TechnicalSheetService()


class TechnicalSheetFillRequest(BaseModel):
    fields: Dict[str, Any] = Field(..., description="Key-value pairs for form fields")
    item_no: Optional[str] = Field(
        default=None,
        description="Optional item number to fetch a template from file share",
    )
    template_id: Optional[str] = Field(
        default="fiche-produit",
        description="Template identifier when item_no is not provided",
    )


@router.get(
    "/{item_no}",
    summary="Read technical sheet fields",
    description="""
    Fetches a fiche technique PDF by item number, extracts filled form fields,
    and returns a cleaned JSON payload. Falls back to text extraction if
    no form fields are detected.
    """,
)
async def read_technical_sheet_fields(
    item_no: str,
    db: Session = Depends(get_db),
) -> JSONResponse:
    try:
        with logfire.span("technical_sheet.read", item_no=item_no):
            result = await technical_sheet_service.read_fiche_technique(item_no)

        if not result["success"]:
            error_code = result.get("error_code", "PROCESSING_ERROR")
            status_code = 500
            if error_code == "PDF_NOT_FOUND":
                status_code = 404
            elif error_code == "NO_FIELDS":
                status_code = 422

            raise HTTPException(
                status_code=status_code,
                detail={
                    "error": {
                        "code": error_code,
                        "message": result.get("error", "Failed to read technical sheet"),
                        "trace_id": getattr(db, "trace_id", "unknown"),
                    }
                },
            )

        return JSONResponse(
            status_code=200,
            content={
                "data": result["data"],
                "meta": {
                    "timestamp": datetime.utcnow().isoformat(),
                    "version": "1.0",
                },
            },
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Failed to read technical sheet: {exc}",
                    "trace_id": getattr(db, "trace_id", "unknown"),
                }
            },
        ) from exc


@router.post(
    "/actions/fill",
    summary="Fill technical sheet template",
    description="""
    Fills a fiche technique template with provided fields and returns the
    generated PDF.
    """,
)
async def fill_technical_sheet_template(
    payload: TechnicalSheetFillRequest = Body(...),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    try:
        with logfire.span(
            "technical_sheet.fill",
            item_no=payload.item_no,
            template_id=payload.template_id,
        ):
            result = await technical_sheet_service.fill_fiche_technique(
                fields=payload.fields,
                item_no=payload.item_no,
                template_id=payload.template_id,
            )

        if not result["success"]:
            error_code = result.get("error_code", "PROCESSING_ERROR")
            status_code = 500
            if error_code in {"PDF_NOT_FOUND", "TEMPLATE_NOT_FOUND"}:
                status_code = 404
            elif error_code in {"NO_FIELDS", "TEMPLATE_SOURCE_REQUIRED", "INVALID_OPTION"}:
                status_code = 422

            error_detail = {
                "code": error_code,
                "message": result.get("error", "Failed to fill technical sheet"),
                "trace_id": getattr(db, "trace_id", "unknown"),
            }
            if result.get("details"):
                error_detail["details"] = result["details"]

            raise HTTPException(
                status_code=status_code,
                detail={
                    "error": error_detail
                },
            )

        return StreamingResponse(
            io.BytesIO(result["content"]),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'inline; filename="{result["filename"]}"',
                "Content-Length": str(result["size"]),
                "Cache-Control": "no-cache",
            },
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Failed to fill technical sheet: {exc}",
                    "trace_id": getattr(db, "trace_id", "unknown"),
                }
            },
        ) from exc


@router.get(
    "/templates/{template_id}/fields",
    summary="Get template field suggestions",
    description="""
    Returns the list of expected field keys (and options for select inputs)
    for a technical sheet template. Use these keys when calling the fill endpoint.
    """,
)
async def get_template_field_suggestions(
    template_id: str,
    item_no: Optional[str] = None,
    db: Session = Depends(get_db),
) -> JSONResponse:
    try:
        with logfire.span(
            "technical_sheet.template_fields",
            template_id=template_id,
            item_no=item_no,
        ):
            result = await technical_sheet_service.get_template_fields(
                item_no=item_no,
                template_id=template_id,
            )

        if not result["success"]:
            error_code = result.get("error_code", "PROCESSING_ERROR")
            status_code = 500
            if error_code == "TEMPLATE_NOT_FOUND":
                status_code = 404
            elif error_code == "TEMPLATE_SOURCE_REQUIRED":
                status_code = 422

            raise HTTPException(
                status_code=status_code,
                detail={
                    "error": {
                        "code": error_code,
                        "message": result.get("error", "Failed to load template fields"),
                        "trace_id": getattr(db, "trace_id", "unknown"),
                    }
                },
            )

        return JSONResponse(
            status_code=200,
            content={
                "data": result["data"],
                "meta": {
                    "timestamp": datetime.utcnow().isoformat(),
                    "version": "1.0",
                },
            },
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Failed to load template fields: {exc}",
                    "trace_id": getattr(db, "trace_id", "unknown"),
                }
            },
        ) from exc

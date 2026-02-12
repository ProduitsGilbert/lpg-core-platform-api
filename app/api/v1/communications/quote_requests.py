"""Quote request endpoints for communications domain."""

from __future__ import annotations

import logging
from typing import List, Optional

import logfire
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.v1.models import ErrorResponse, SingleResponse
from app.deps import get_db, get_idempotency_key
from app.domain.communications.models import QuoteRequestResponse
from app.domain.communications.quote_request_service import QuoteRequestService
from app.errors import BaseAPIException

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/quote-requests", tags=["Communications - Quote Requests"])
quote_request_service = QuoteRequestService()


@router.post(
    "/actions/send",
    response_model=SingleResponse[QuoteRequestResponse],
    status_code=201,
    responses={
        201: {"description": "Quote request sent successfully"},
        400: {"description": "Invalid request", "model": ErrorResponse},
        404: {"description": "Vendor not found", "model": ErrorResponse},
        409: {"description": "Missing vendor email", "model": ErrorResponse},
        422: {"description": "Invalid table JSON", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
    summary="Send vendor quote request",
)
async def send_vendor_quote_request(
    vendor_id: str = Form(..., description="Vendor number in Business Central"),
    subject: str = Form(..., description="Email subject"),
    body: str = Form(..., description="Email body (HTML or plain text)"),
    language_override: Optional[str] = Form(
        None, description="Override vendor language (e.g., fr, en)"
    ),
    table_json: Optional[str] = Form(
        None, description="JSON array of objects to include as an HTML table"
    ),
    attach: Optional[UploadFile] = File(
        None, description="Optional single attachment"
    ),
    attachments: Optional[List[UploadFile]] = File(
        None, description="Optional multiple attachments"
    ),
    dry_run: bool = Form(False, description="When true, do not send the email"),
    idempotency_key: Optional[str] = Depends(get_idempotency_key),
    db: Session = Depends(get_db),
) -> SingleResponse[QuoteRequestResponse]:
    """Send a vendor quote request via Front."""
    try:
        if idempotency_key:
            from app.audit import get_idempotency_record

            cached = get_idempotency_record(db, idempotency_key)
            if cached:
                return SingleResponse(data=QuoteRequestResponse(**cached))

        uploaded_files = []
        if attach:
            uploaded_files.append(attach)
        if attachments:
            uploaded_files.extend(attachments)

        attachment_payloads = []
        for file in uploaded_files:
            content = await file.read()
            attachment_payloads.append(
                {
                    "filename": file.filename or "attachment",
                    "content": content,
                    "content_type": file.content_type,
                }
            )

        with logfire.span(
            "send_vendor_quote_request",
            vendor_id=vendor_id,
            attachment_count=len(attachment_payloads),
            dry_run=dry_run,
        ):
            response = await quote_request_service.send_quote_request(
                vendor_id=vendor_id,
                subject=subject,
                body=body,
                language_override=language_override,
                table_json=table_json,
                attachments=attachment_payloads,
                dry_run=dry_run,
            )

        if idempotency_key:
            from app.audit import save_idempotency_record, write_audit_log

            save_idempotency_record(db, idempotency_key, response.model_dump())
            write_audit_log(
                db,
                event_type="QuoteRequest.Sent",
                entity_type="vendor",
                entity_id=vendor_id,
                actor="system",
                changes={
                    "vendor_email": response.vendor_email,
                    "language": response.language,
                    "subject": response.subject_final,
                    "front_message_id": response.front_message_id,
                    "dry_run": response.dry_run,
                },
                trace_id=idempotency_key,
            )

        return SingleResponse(data=response)
    except HTTPException:
        raise
    except BaseAPIException:
        raise
    except Exception as exc:
        logger.error("Error sending quote request for %s: %s", vendor_id, exc)
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "Failed to send vendor quote request",
                    "trace_id": getattr(db, "trace_id", "unknown"),
                }
            },
        )

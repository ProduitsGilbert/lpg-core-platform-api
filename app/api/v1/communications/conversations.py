"""Conversations endpoints for communications domain."""

from __future__ import annotations

import io
import logging
from typing import Optional

import logfire
from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.v1.models import CollectionResponse, ErrorResponse, SingleResponse
from app.deps import get_db, get_idempotency_key
from app.domain.communications.conversation_service import ConversationService
from app.domain.communications.models import (
    ConversationArchiveResponse,
    ConversationCommentRequest,
    ConversationCommentResponse,
    ConversationReplyRequest,
    ConversationReplyResponse,
    ConversationResponse,
    ConversationSnoozeRequest,
    ConversationSnoozeResponse,
    Message,
)
from app.errors import BaseAPIException

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/conversations", tags=["Communications - Conversations"])

conversation_service = ConversationService()


@router.get(
    "/{conversation_id}",
    response_model=SingleResponse[ConversationResponse],
    responses={
        200: {"description": "Conversation retrieved successfully"},
        404: {"description": "Conversation not found", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
    summary="Get conversation by ID",
)
async def get_conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
) -> SingleResponse[ConversationResponse]:
    """Return a conversation with messages and comments."""
    try:
        with logfire.span("get_conversation", conversation_id=conversation_id):
            conversation = await conversation_service.get_conversation(conversation_id)
        if not conversation:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": {
                        "code": "CONVERSATION_NOT_FOUND",
                        "message": f"Conversation '{conversation_id}' not found",
                        "trace_id": getattr(db, "trace_id", "unknown"),
                    }
                },
            )
        return SingleResponse(data=conversation)
    except HTTPException:
        raise
    except BaseAPIException:
        raise
    except Exception as exc:
        logger.error("Error fetching conversation %s: %s", conversation_id, exc)
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "Failed to retrieve conversation",
                    "trace_id": getattr(db, "trace_id", "unknown"),
                }
            },
        )


@router.get(
    "/{conversation_id}/messages",
    response_model=CollectionResponse[Message],
    responses={
        200: {"description": "Messages retrieved successfully"},
        404: {"description": "Conversation not found", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
    summary="List conversation messages",
)
async def list_conversation_messages(
    conversation_id: str,
    db: Session = Depends(get_db),
) -> CollectionResponse[Message]:
    """Return all messages for a conversation."""
    try:
        with logfire.span("list_conversation_messages", conversation_id=conversation_id):
            messages = await conversation_service.get_messages(conversation_id)
        return CollectionResponse(data=messages)
    except HTTPException:
        raise
    except BaseAPIException:
        raise
    except Exception as exc:
        logger.error("Error retrieving messages for %s: %s", conversation_id, exc)
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "Failed to retrieve conversation messages",
                    "trace_id": getattr(db, "trace_id", "unknown"),
                }
            },
        )


@router.get(
    "/{conversation_id}/messages/last",
    response_model=SingleResponse[Message],
    responses={
        200: {"description": "Last message retrieved successfully"},
        404: {"description": "Conversation or message not found", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
    summary="Get last message",
)
async def get_last_conversation_message(
    conversation_id: str,
    db: Session = Depends(get_db),
) -> SingleResponse[Message]:
    """Return the most recent message for a conversation."""
    try:
        with logfire.span("get_last_message", conversation_id=conversation_id):
            message = await conversation_service.get_last_message(conversation_id)
        if not message:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": {
                        "code": "MESSAGE_NOT_FOUND",
                        "message": f"Conversation '{conversation_id}' has no messages",
                        "trace_id": getattr(db, "trace_id", "unknown"),
                    }
                },
            )
        return SingleResponse(data=message)
    except HTTPException:
        raise
    except BaseAPIException:
        raise
    except Exception as exc:
        logger.error("Error retrieving last message for %s: %s", conversation_id, exc)
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "Failed to retrieve last message",
                    "trace_id": getattr(db, "trace_id", "unknown"),
                }
            },
        )


@router.get(
    "/{conversation_id}/messages/{message_id}",
    response_model=SingleResponse[Message],
    responses={
        200: {"description": "Message retrieved successfully"},
        404: {"description": "Message not found", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
    summary="Get message by ID",
)
async def get_conversation_message(
    conversation_id: str,
    message_id: str,
    db: Session = Depends(get_db),
) -> SingleResponse[Message]:
    """Return a specific message inside a conversation."""
    try:
        with logfire.span(
            "get_conversation_message", conversation_id=conversation_id, message_id=message_id
        ):
            message = await conversation_service.get_message(message_id)
        return SingleResponse(data=message)
    except HTTPException:
        raise
    except BaseAPIException:
        raise
    except Exception as exc:
        logger.error("Error retrieving message %s: %s", message_id, exc)
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "Failed to retrieve message",
                    "trace_id": getattr(db, "trace_id", "unknown"),
                }
            },
        )


@router.get(
    "/{conversation_id}/messages/{message_id}/attachments/{attachment_id}",
    responses={
        200: {
            "content": {"application/octet-stream": {}},
            "description": "Attachment downloaded successfully",
        },
        404: {"description": "Attachment not found", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
    summary="Download attachment",
)
async def download_attachment(
    conversation_id: str,
    message_id: str,
    attachment_id: str,
    db: Session = Depends(get_db),
) -> StreamingResponse:
    """Download an attachment from a conversation message."""
    try:
        with logfire.span(
            "download_attachment",
            conversation_id=conversation_id,
            message_id=message_id,
            attachment_id=attachment_id,
        ):
            attachment = await conversation_service.download_attachment(message_id, attachment_id)

        media_type = attachment.content_type or "application/octet-stream"
        headers = {
            "Content-Disposition": f'attachment; filename="{attachment.filename}"',
            "X-Attachment-Id": attachment.id,
        }
        if attachment.size:
            headers["Content-Length"] = str(attachment.size)
        return StreamingResponse(io.BytesIO(attachment.content), media_type=media_type, headers=headers)
    except HTTPException:
        raise
    except BaseAPIException:
        raise
    except Exception as exc:
        logger.error("Error downloading attachment %s: %s", attachment_id, exc)
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "Failed to download attachment",
                    "trace_id": getattr(db, "trace_id", "unknown"),
                }
            },
        )


@router.post(
    "/{conversation_id}/comments",
    response_model=SingleResponse[ConversationCommentResponse],
    status_code=201,
    responses={
        201: {"description": "Comment created successfully"},
        404: {"description": "Conversation not found", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
    summary="Add conversation comment",
)
async def create_comment(
    conversation_id: str,
    request: ConversationCommentRequest = Body(...),
    db: Session = Depends(get_db),
) -> SingleResponse[ConversationCommentResponse]:
    """Create a new internal comment inside a conversation."""
    try:
        with logfire.span("create_comment", conversation_id=conversation_id):
            comment = await conversation_service.create_comment(conversation_id, request)
        return SingleResponse(data=comment)
    except HTTPException:
        raise
    except BaseAPIException:
        raise
    except Exception as exc:
        logger.error("Error creating comment for %s: %s", conversation_id, exc)
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "Failed to create comment",
                    "trace_id": getattr(db, "trace_id", "unknown"),
                }
            },
        )


@router.post(
    "/{conversation_id}/actions/reply",
    response_model=SingleResponse[ConversationReplyResponse],
    status_code=201,
    responses={
        201: {"description": "Reply sent successfully"},
        400: {"description": "Invalid request", "model": ErrorResponse},
        404: {"description": "Conversation not found", "model": ErrorResponse},
        409: {"description": "Duplicate reply", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
    summary="Reply to conversation",
)
async def reply_to_conversation(
    conversation_id: str,
    request: ConversationReplyRequest = Body(...),
    idempotency_key: Optional[str] = Depends(get_idempotency_key),
    db: Session = Depends(get_db),
) -> SingleResponse[ConversationReplyResponse]:
    """Reply to a conversation thread."""
    try:
        with logfire.span(
            "reply_to_conversation",
            conversation_id=conversation_id,
            reply_type=request.reply_type,
        ):
            if idempotency_key:
                from app.audit import get_idempotency_record

                cached = get_idempotency_record(db, idempotency_key)
                if cached:
                    logfire.info(
                        "Returning cached reply for idempotency key", idempotency_key=idempotency_key
                    )
                    return SingleResponse(data=ConversationReplyResponse(**cached))

            reply = await conversation_service.reply_to_conversation(
                conversation_id,
                request,
                idempotency_key,
                db,
            )
        if not reply:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": {
                        "code": "CONVERSATION_NOT_FOUND",
                        "message": f"Conversation '{conversation_id}' not found",
                        "trace_id": getattr(db, "trace_id", "unknown"),
                    }
                },
            )
        return SingleResponse(data=reply)
    except HTTPException:
        raise
    except BaseAPIException:
        raise
    except Exception as exc:
        logger.error("Error replying to conversation %s: %s", conversation_id, exc)
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "Failed to send reply",
                    "trace_id": getattr(db, "trace_id", "unknown"),
                }
            },
        )


@router.post(
    "/{conversation_id}/actions/archive",
    response_model=SingleResponse[ConversationArchiveResponse],
    responses={
        200: {"description": "Conversation archived successfully"},
        404: {"description": "Conversation not found", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
    summary="Archive conversation",
)
async def archive_conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
) -> SingleResponse[ConversationArchiveResponse]:
    """Archive a conversation."""
    try:
        with logfire.span("archive_conversation", conversation_id=conversation_id):
            response = await conversation_service.archive_conversation(conversation_id)
        return SingleResponse(data=response)
    except HTTPException:
        raise
    except BaseAPIException:
        raise
    except Exception as exc:
        logger.error("Error archiving conversation %s: %s", conversation_id, exc)
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "Failed to archive conversation",
                    "trace_id": getattr(db, "trace_id", "unknown"),
                }
            },
        )


@router.post(
    "/{conversation_id}/actions/snooze",
    response_model=SingleResponse[ConversationSnoozeResponse],
    responses={
        200: {"description": "Conversation snoozed successfully"},
        404: {"description": "Conversation not found", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
    summary="Snooze conversation",
)
async def snooze_conversation(
    conversation_id: str,
    request: ConversationSnoozeRequest = Body(...),
    db: Session = Depends(get_db),
) -> SingleResponse[ConversationSnoozeResponse]:
    """Snooze a conversation until the given datetime."""
    try:
        with logfire.span(
            "snooze_conversation",
            conversation_id=conversation_id,
            snooze_until=str(request.snooze_until),
        ):
            response = await conversation_service.snooze_conversation(conversation_id, request)
        return SingleResponse(data=response)
    except HTTPException:
        raise
    except BaseAPIException:
        raise
    except Exception as exc:
        logger.error("Error snoozing conversation %s: %s", conversation_id, exc)
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "Failed to snooze conversation",
                    "trace_id": getattr(db, "trace_id", "unknown"),
                }
            },
        )

"""Conversation service for Front email client integration."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Type

import logfire

from sqlalchemy.orm import Session

from app.adapters.front_client import FrontClient
from app.domain.communications.models import (
    AttachmentContent,
    ConversationArchiveResponse,
    ConversationComment,
    ConversationCommentRequest,
    ConversationCommentResponse,
    ConversationReplyRequest,
    ConversationReplyResponse,
    ConversationResponse,
    ConversationSnoozeRequest,
    ConversationSnoozeResponse,
    Message,
    MessageAttachment,
    MessageAuthor,
    MessageRecipient,
)
from app.errors import CommunicationsNotFound
from app.ports import FrontClientProtocol

logger = logging.getLogger(__name__)


class ConversationService:
    """Service for conversation operations with the Front API."""

    def __init__(self, front_client_class: Type[FrontClientProtocol] = FrontClient):
        self._front_client_class = front_client_class

    def _client(self) -> FrontClientProtocol:
        return self._front_client_class()  # type: ignore[return-value]

    async def get_conversation(self, conversation_id: str) -> Optional[ConversationResponse]:
        """Get full conversation data including messages and comments."""
        with logfire.span("conversation_service.get_conversation", conversation_id=conversation_id):
            async with self._client() as client:
                conversation_data = await client.get_conversation(conversation_id)
                if not conversation_data:
                    return None

                messages_data = await self._collect_all_messages(client, conversation_id)
                comments_data = await client.get_conversation_comments(conversation_id)

        return self._build_conversation(conversation_data, messages_data, comments_data)

    async def get_messages(self, conversation_id: str) -> List[Message]:
        """Return all messages of a conversation."""
        with logfire.span("conversation_service.get_messages", conversation_id=conversation_id):
            async with self._client() as client:
                raw_messages = await self._collect_all_messages(client, conversation_id)
        messages = [self._map_message(message) for message in raw_messages]
        return sorted(messages, key=lambda msg: msg.created_at)

    async def get_last_message(self, conversation_id: str) -> Optional[Message]:
        """Return the last message in a conversation."""
        messages = await self.get_messages(conversation_id)
        return messages[-1] if messages else None

    async def create_comment(
        self, conversation_id: str, request: ConversationCommentRequest
    ) -> ConversationCommentResponse:
        """Create a new comment in a conversation."""
        with logfire.span("conversation_service.create_comment", conversation_id=conversation_id):
            async with self._client() as client:
                comment_data = await client.create_comment(
                    conversation_id,
                    request.body,
                    author_id=request.author_id,
                )

        comment = self._map_comment(comment_data)
        return ConversationCommentResponse(
            id=comment.id,
            conversation_id=conversation_id,
            body=comment.body,
            created_at=comment.created_at,
            author=comment.author,
        )

    async def reply_to_conversation(
        self,
        conversation_id: str,
        request: ConversationReplyRequest,
        idempotency_key: Optional[str],
        db: Optional[Session],
    ) -> Optional[ConversationReplyResponse]:
        """Send a reply to a conversation via Front."""
        with logfire.span(
            "conversation_service.reply_to_conversation",
            conversation_id=conversation_id,
            reply_type=request.reply_type,
        ):
            if request.reply_type == "comment":
                comment_response = await self.create_comment(
                    conversation_id,
                    ConversationCommentRequest(body=request.body, author_id=request.author_id),
                )
                return ConversationReplyResponse(
                    id=comment_response.id,
                    conversation_id=conversation_id,
                    reply_type="comment",
                    status="sent",
                    created_at=comment_response.created_at,
                    author=comment_response.author,
                )

            payload: Dict[str, Any] = {"body": request.body}
            if request.author_id:
                payload["author_id"] = request.author_id
            if request.to:
                payload["to"] = [str(address) for address in request.to]
            if request.cc:
                payload["cc"] = [str(address) for address in request.cc]
            if request.bcc:
                payload["bcc"] = [str(address) for address in request.bcc]
            if request.attachments:
                payload["attachments"] = request.attachments

            async with self._client() as client:
                reply_data = await client.send_conversation_reply(conversation_id, payload)

            message = self._map_message(reply_data)

            if idempotency_key and db:
                from app.audit import save_idempotency_record, write_audit_log

                save_idempotency_record(
                    db,
                    idempotency_key,
                    ConversationReplyResponse(
                        id=message.id,
                        conversation_id=conversation_id,
                        reply_type=request.reply_type,
                        status="sent",
                        created_at=message.created_at,
                        author=message.author,
                    ).model_dump(),
                )

                write_audit_log(
                    db,
                    event_type="Conversation.ReplySent",
                    entity_type="conversation",
                    entity_id=conversation_id,
                    actor=request.author_id or "system",
                    changes={
                        "reply_type": request.reply_type,
                        "to": payload.get("to"),
                        "cc": payload.get("cc"),
                        "bcc": payload.get("bcc"),
                        "message_id": message.id,
                    },
                    trace_id=idempotency_key,
                )

            return ConversationReplyResponse(
                id=message.id,
                conversation_id=conversation_id,
                reply_type=request.reply_type,
                status="sent",
                created_at=message.created_at,
                author=message.author,
            )

    async def archive_conversation(self, conversation_id: str) -> ConversationArchiveResponse:
        """Archive a Front conversation."""
        with logfire.span("conversation_service.archive_conversation", conversation_id=conversation_id):
            async with self._client() as client:
                await client.archive_conversation(conversation_id)

        archived_at = datetime.now(timezone.utc)
        return ConversationArchiveResponse(
            conversation_id=conversation_id,
            status="archived",
            archived_at=archived_at,
        )

    async def snooze_conversation(
        self, conversation_id: str, request: ConversationSnoozeRequest
    ) -> ConversationSnoozeResponse:
        """Snooze a conversation until a specific datetime."""
        with logfire.span(
            "conversation_service.snooze_conversation",
            conversation_id=conversation_id,
            snooze_until=str(request.snooze_until),
        ):
            async with self._client() as client:
                await client.snooze_conversation(conversation_id, request.snooze_until)

        return ConversationSnoozeResponse(
            conversation_id=conversation_id,
            snooze_until=request.snooze_until,
        )

    async def download_attachment(
        self, message_id: str, attachment_id: str
    ) -> AttachmentContent:
        """Download an attachment from a specific message."""
        with logfire.span(
            "conversation_service.download_attachment",
            message_id=message_id,
            attachment_id=attachment_id,
        ):
            async with self._client() as client:
                message_data = await client.get_message(message_id)
                attachment_meta = self._find_attachment(message_data, attachment_id)
                content = await client.download_attachment(attachment_id)

        return AttachmentContent(
            id=attachment_id,
            filename=attachment_meta.get("filename", attachment_id),
            content_type=attachment_meta.get("content_type"),
            size=attachment_meta.get("size"),
            content=content,
        )

    async def get_message(self, message_id: str) -> Message:
        """Fetch a single Front message by ID."""
        with logfire.span("conversation_service.get_message", message_id=message_id):
            async with self._client() as client:
                message_data = await client.get_message(message_id)
        return self._map_message(message_data)

    async def _collect_all_messages(
        self, client: FrontClientProtocol, conversation_id: str
    ) -> List[Dict[str, Any]]:
        """Collect all messages for a conversation, following pagination."""
        messages: List[Dict[str, Any]] = []
        next_page: Optional[str] = None

        while True:
            response = await client.get_conversation_messages(conversation_id, page=next_page)
            results = response.get("_results", [])
            messages.extend(results)

            pagination = response.get("_pagination") or {}
            next_page = pagination.get("next")
            if not next_page:
                break

        return messages

    def _build_conversation(
        self,
        conversation_data: Dict[str, Any],
        messages_data: Sequence[Dict[str, Any]],
        comments_data: Dict[str, Any],
    ) -> ConversationResponse:
        messages = [self._map_message(message) for message in messages_data]
        messages.sort(key=lambda msg: msg.created_at)

        comment_results = comments_data.get("_results", []) if comments_data else []
        comments = [self._map_comment(comment) for comment in comment_results]
        comments.sort(key=lambda cmt: cmt.created_at)

        last_message = None
        if conversation_data.get("last_message"):
            last_message = self._map_message(conversation_data["last_message"])
        elif messages:
            last_message = messages[-1]

        created_at = self._parse_timestamp(conversation_data.get("created_at"))
        updated_at = (
            self._parse_timestamp(conversation_data.get("updated_at"))
            if conversation_data.get("updated_at")
            else (last_message.created_at if last_message else created_at)
        )

        tags = [tag.get("name", "") for tag in conversation_data.get("tags", []) if tag]
        assignee = self._map_author(conversation_data.get("assignee")) if conversation_data.get("assignee") else None

        participant_count = self._estimate_participants(messages, comments, assignee)

        return ConversationResponse(
            id=conversation_data.get("id"),
            subject=conversation_data.get("subject"),
            status=conversation_data.get("status", "open"),
            assignee=assignee,
            tags=[tag for tag in tags if tag],
            messages=messages,
            comments=comments,
            last_message=last_message,
            created_at=created_at,
            updated_at=updated_at,
            is_private=conversation_data.get("is_private", False),
            participant_count=participant_count,
            message_count=len(messages),
        )

    def _map_message(self, data: Dict[str, Any]) -> Message:
        author = self._map_author(data.get("author"))
        recipients = [self._map_recipient(recipient) for recipient in data.get("recipients", []) if recipient]
        attachments = [self._map_attachment(attachment) for attachment in data.get("attachments", []) if attachment]
        created_at = self._parse_timestamp(data.get("created_at"))

        is_internal = not data.get("is_inbound", False) and (author.is_team_member if author else False)

        return Message(
            id=data.get("id"),
            type=data.get("type", "message"),
            author=author,
            body=data.get("body"),
            text=data.get("text"),
            blurb=data.get("blurb"),
            created_at=created_at,
            is_internal=is_internal,
            is_inbound=data.get("is_inbound"),
            recipients=recipients,
            attachments=attachments,
        )

    def _map_comment(self, data: Dict[str, Any]) -> ConversationComment:
        created_at = self._parse_timestamp(data.get("posted_at") or data.get("created_at"))
        author = self._map_author(data.get("author"))
        return ConversationComment(
            id=data.get("id"),
            body=data.get("body", ""),
            created_at=created_at,
            author=author,
        )

    def _map_author(self, data: Optional[Dict[str, Any]]) -> MessageAuthor:
        if not data:
            return MessageAuthor(name="Unknown", is_team_member=False)

        name_parts = [data.get("first_name"), data.get("last_name")]
        name = " ".join(part for part in name_parts if part).strip()
        if not name:
            name = data.get("name") or data.get("username") or data.get("email") or None

        return MessageAuthor(
            id=data.get("id"),
            email=data.get("email"),
            name=name,
            is_team_member=data.get("is_teammate", False),
        )

    @staticmethod
    def _map_recipient(data: Dict[str, Any]) -> MessageRecipient:
        return MessageRecipient(
            handle=data.get("handle", ""),
            role=data.get("role", "to"),
        )

    @staticmethod
    def _map_attachment(data: Dict[str, Any]) -> MessageAttachment:
        return MessageAttachment(
            id=data.get("id"),
            filename=data.get("filename", data.get("id", "attachment")),
            content_type=data.get("content_type"),
            size=data.get("size"),
            download_url=data.get("url"),
        )

    @staticmethod
    def _parse_timestamp(value: Any) -> datetime:
        if value is None:
            return datetime.now(timezone.utc)
        if isinstance(value, datetime):
            return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        try:
            if isinstance(value, (int, float)):
                return datetime.fromtimestamp(value, tz=timezone.utc)
            if isinstance(value, str):
                if value.isdigit():
                    return datetime.fromtimestamp(int(value), tz=timezone.utc)
                return datetime.fromisoformat(value)
        except Exception:
            logger.debug("Unable to parse timestamp", extra={"value": value})
        return datetime.now(timezone.utc)

    @staticmethod
    def _estimate_participants(
        messages: Sequence[Message],
        comments: Sequence[ConversationComment],
        assignee: Optional[MessageAuthor],
    ) -> int:
        participants = set()
        if assignee and (assignee.id or assignee.email or assignee.name):
            participants.add(assignee.id or assignee.email or assignee.name)

        for message in messages:
            author = message.author
            if author and (author.id or author.email or author.name):
                participants.add(author.id or author.email or author.name)
            for recipient in message.recipients:
                participants.add(recipient.handle)

        for comment in comments:
            author = comment.author
            if author and (author.id or author.email or author.name):
                participants.add(author.id or author.email or author.name)

        return len(participants)

    @staticmethod
    def _find_attachment(message_data: Dict[str, Any], attachment_id: str) -> Dict[str, Any]:
        attachments = message_data.get("attachments", [])
        for attachment in attachments:
            if attachment.get("id") == attachment_id:
                return attachment
        raise CommunicationsNotFound("Attachment", attachment_id)

"""Tests for the conversation service Front integration."""

import asyncio
from datetime import datetime, timezone

from app.domain.communications.conversation_service import ConversationService
from app.domain.communications.models import (
    ConversationCommentRequest,
    ReceivablesEmailSendRequest,
    ConversationSnoozeRequest,
)
from app.settings import settings

CONVERSATION_ID = "cnv_123"

CONVERSATION_DATA = {
    "id": CONVERSATION_ID,
    "subject": "Vendor follow up",
    "status": "open",
    "assignee": {
        "id": "tea_1",
        "email": "buyer@example.com",
        "first_name": "Buyer",
        "last_name": "Team",
        "is_teammate": True,
    },
    "tags": [{"name": "purchasing"}],
    "created_at": 1_700_000_000,
    "updated_at": 1_700_000_800,
    "is_private": False,
    "last_message": {
        "id": "msg_2",
        "type": "email",
        "created_at": 1_700_000_600,
        "author": {
            "id": "tea_1",
            "email": "buyer@example.com",
            "first_name": "Buyer",
            "last_name": "Team",
            "is_teammate": True,
        },
        "recipients": [{"handle": "contact@example.com", "role": "to"}],
        "attachments": [],
        "body": "<p>Thanks</p>",
        "text": "Thanks",
        "is_inbound": False,
    },
}

MESSAGES = [
    {
        "id": "msg_1",
        "type": "email",
        "created_at": 1_700_000_100,
        "author": {
            "id": "cnt_1",
            "email": "contact@example.com",
            "first_name": "Vendor",
            "last_name": "Rep",
            "is_teammate": False,
        },
        "recipients": [{"handle": "buyer@example.com", "role": "to"}],
        "attachments": [
            {
                "id": "att_1",
                "filename": "quote.pdf",
                "url": "https://front/attachments/att_1",
                "content_type": "application/pdf",
                "size": 1234,
            }
        ],
        "body": "<p>Hello</p>",
        "text": "Hello",
        "is_inbound": True,
    },
    CONVERSATION_DATA["last_message"],
]

COMMENTS = [
    {
        "id": "cmt_1",
        "body": "Need to review pricing",
        "posted_at": 1_700_000_200,
        "author": {
            "id": "tea_2",
            "email": "analyst@example.com",
            "first_name": "Analyst",
            "last_name": "User",
            "is_teammate": True,
        },
    }
]

MESSAGES_BY_ID = {message["id"]: message for message in MESSAGES}


class StubFrontClient:
    """Async stub implementing the Front client protocol."""

    def __init__(self, *, api_key: str | None = None) -> None:
        self.archived = False
        self.snoozed_until = None
        self.api_key = api_key

    async def __aenter__(self) -> "StubFrontClient":
        return self

    async def __aexit__(self, exc_type, exc, exc_tb) -> None:
        return None

    async def get_conversation(self, conversation_id: str):
        return CONVERSATION_DATA

    async def get_conversation_messages(self, conversation_id: str, page: str | None = None):
        return {"_results": MESSAGES, "_pagination": {}}

    async def get_conversation_comments(self, conversation_id: str):
        return {"_results": COMMENTS}

    async def create_comment(self, conversation_id: str, body: str, author_id: str | None = None):
        return {
            "id": "cmt_new",
            "body": body,
            "posted_at": 1_700_000_500,
            "author": {
                "id": author_id or "tea_1",
                "email": "buyer@example.com",
                "first_name": "Buyer",
                "last_name": "Team",
                "is_teammate": True,
            },
        }

    async def send_conversation_reply(self, conversation_id: str, payload: dict):
        return MESSAGES[0]

    async def send_channel_message(self, channel_id: str, payload: dict, attachments=None):
        return {
            "id": "msg_new",
            "conversation_id": "cnv_new",
            "created_at": 1_700_001_000,
            "type": "email",
        }

    async def get_inbox_channels(self, inbox_id: str):
        return {
            "_results": [
                {"id": "cha_receivables", "type": "email"},
            ]
        }

    async def archive_conversation(self, conversation_id: str):
        self.archived = True
        return {}

    async def snooze_conversation(self, conversation_id: str, snooze_until: datetime):
        self.snoozed_until = snooze_until
        return {}

    async def get_message(self, message_id: str):
        return MESSAGES_BY_ID[message_id]

    async def download_attachment(self, attachment_id: str) -> bytes:
        return b"file"


def run(coro):
    """Run an async coroutine for testing."""
    return asyncio.run(coro)


def test_get_conversation_maps_messages_and_comments():
    service = ConversationService(front_client_class=StubFrontClient)

    conversation = run(service.get_conversation(CONVERSATION_ID))

    assert conversation is not None
    assert conversation.id == CONVERSATION_ID
    assert conversation.message_count == len(MESSAGES)
    assert conversation.messages[0].attachments[0].filename == "quote.pdf"
    assert conversation.comments[0].body == "Need to review pricing"
    assert conversation.last_message and conversation.last_message.id == "msg_2"


def test_download_attachment_includes_metadata():
    service = ConversationService(front_client_class=StubFrontClient)

    attachment = run(service.download_attachment("msg_1", "att_1"))

    assert attachment.filename == "quote.pdf"
    assert attachment.content == b"file"
    assert attachment.size == 1234


def test_create_comment_returns_response():
    service = ConversationService(front_client_class=StubFrontClient)

    response = run(
        service.create_comment(
            CONVERSATION_ID, ConversationCommentRequest(body="New note", author_id="tea_9")
        )
    )

    assert response.body == "New note"
    assert response.author.is_team_member is True


def test_snooze_conversation_returns_requested_time():
    service = ConversationService(front_client_class=StubFrontClient)
    until = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)

    response = run(
        service.snooze_conversation(CONVERSATION_ID, ConversationSnoozeRequest(snooze_until=until))
    )

    assert response.snooze_until == until


def test_send_receivables_email_returns_response(monkeypatch):
    monkeypatch.setattr(settings, "front_accounting_api_key", "test-accounting-key")
    monkeypatch.setattr(settings, "front_receivables_inbox_id", "inb_cunq0")
    monkeypatch.setattr(settings, "front_receivables_channel_id", None)

    service = ConversationService(front_client_class=StubFrontClient)
    request = ReceivablesEmailSendRequest(
        subject="Invoice follow-up",
        body="<p>Please find the invoice attached.</p>",
        to=["customer@example.com"],
        cc=["ar@example.com"],
    )

    response = run(service.send_receivables_email(request))

    assert response.id == "msg_new"
    assert response.conversation_id == "cnv_new"
    assert response.channel_id == "cha_receivables"
    assert response.inbox_id == "inb_cunq0"


class StubODataService:
    def __init__(self, records):
        self.records = records

    async def fetch_collection(self, resource, *, filter_field=None, filter_value=None, top=None):
        return self.records


def test_send_receivables_email_accepts_customer_no(monkeypatch):
    monkeypatch.setattr(settings, "front_accounting_api_key", "test-accounting-key")
    monkeypatch.setattr(settings, "front_receivables_inbox_id", "inb_cunq0")
    monkeypatch.setattr(settings, "front_receivables_channel_id", None)

    odata = StubODataService(records=[{"No": "C10000", "Email": "ar-customer@example.com"}])
    service = ConversationService(front_client_class=StubFrontClient, odata_service=odata)
    request = ReceivablesEmailSendRequest(
        subject="Invoice follow-up",
        body="<p>Please review your statement.</p>",
        customer_no="C10000",
    )

    response = run(service.send_receivables_email(request))

    assert response.to == ["ar-customer@example.com"]
    assert response.customer_no == "C10000"

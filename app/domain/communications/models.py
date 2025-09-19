"""Domain models for communications entities."""

from typing import Optional, List, Literal
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr


class MessageAuthor(BaseModel):
    """Author of a message or comment."""

    id: Optional[str] = None
    email: Optional[EmailStr] = None
    name: Optional[str] = None
    is_team_member: bool = False


class MessageRecipient(BaseModel):
    """Recipient of a Front message."""

    handle: str
    role: str = "to"


class MessageAttachment(BaseModel):
    """Attachment metadata for a message."""

    id: str
    filename: str
    content_type: Optional[str] = None
    size: Optional[int] = None
    download_url: Optional[str] = None


class Message(BaseModel):
    """Individual message within a conversation."""

    id: str
    type: str
    author: MessageAuthor
    body: Optional[str] = None
    text: Optional[str] = None
    blurb: Optional[str] = None
    created_at: datetime
    is_internal: bool = Field(default=False, description="Internal comment vs external message")
    is_inbound: Optional[bool] = None
    recipients: List[MessageRecipient] = Field(default_factory=list)
    attachments: List[MessageAttachment] = Field(default_factory=list)


class ConversationComment(BaseModel):
    """Comment record inside a conversation."""

    id: str
    author: MessageAuthor
    body: str
    created_at: datetime


class ConversationResponse(BaseModel):
    """Conversation thread from Front."""

    id: str
    type: str = "conversation"
    subject: Optional[str] = None
    status: Literal["open", "archived", "deleted", "spam"]
    assignee: Optional[MessageAuthor] = None
    tags: List[str] = Field(default_factory=list)
    messages: List[Message] = Field(default_factory=list)
    comments: List[ConversationComment] = Field(default_factory=list)
    last_message: Optional[Message] = None
    created_at: datetime
    updated_at: datetime
    is_private: bool = False
    participant_count: int = 0
    message_count: int = 0

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat() if v else None}


class ConversationReplyRequest(BaseModel):
    """Request to reply to a conversation."""

    reply_type: Literal["email", "comment"] = Field(
        ...,
        description="'email' for external reply, 'comment' for internal note",
    )
    body: str = Field(..., description="Reply content (HTML or plain text)")
    to: Optional[List[EmailStr]] = Field(
        None,
        description="Recipients for email reply (not used for comments)",
    )
    cc: Optional[List[EmailStr]] = Field(None, description="CC recipients")
    bcc: Optional[List[EmailStr]] = Field(None, description="BCC recipients")
    attachments: Optional[List[str]] = Field(
        None,
        description="List of attachment IDs included in the reply",
    )
    author_id: Optional[str] = Field(
        None,
        description="ID of the teammate sending the reply",
    )


class ConversationReplyResponse(BaseModel):
    """Response after replying to a conversation."""

    id: str = Field(..., description="ID of the created message")
    type: str = "message"
    conversation_id: str
    reply_type: Literal["email", "comment"]
    status: Literal["sent", "pending", "failed"]
    created_at: datetime
    author: MessageAuthor

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat() if v else None}


class ConversationCommentRequest(BaseModel):
    """Request payload to create a new comment."""

    body: str = Field(..., description="Comment text (HTML or plain text)")
    author_id: Optional[str] = Field(
        None,
        description="Optional teammate ID used as the comment author",
    )


class ConversationCommentResponse(BaseModel):
    """Response payload after creating a comment."""

    id: str
    conversation_id: str
    body: str
    created_at: datetime
    author: MessageAuthor

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat() if v else None}


class ConversationArchiveResponse(BaseModel):
    """Response returned when archiving a conversation."""

    conversation_id: str
    status: Literal["archived", "open"]
    archived_at: datetime


class ConversationSnoozeRequest(BaseModel):
    """Request payload to snooze a conversation."""

    snooze_until: datetime = Field(
        ..., description="UTC datetime when the conversation should reopen"
    )


class ConversationSnoozeResponse(BaseModel):
    """Response payload after snoozing a conversation."""

    conversation_id: str
    snooze_until: datetime


class AttachmentContent(BaseModel):
    """Downloaded attachment payload."""

    id: str
    filename: str
    content_type: Optional[str] = None
    size: Optional[int] = None
    content: bytes

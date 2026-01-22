"""ClickUp domain models."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ClickUpTask(BaseModel):
    """ClickUp task model."""
    id: str
    name: str
    description: Optional[str] = None
    status: ClickUpTaskStatus
    priority: Optional[ClickUpPriority] = None
    due_date: Optional[datetime] = None
    start_date: Optional[datetime] = None
    time_estimate: Optional[int] = None  # in milliseconds
    time_spent: Optional[int] = None  # in milliseconds
    assignees: List[ClickUpUser] = Field(default_factory=list)
    tags: List[ClickUpTag] = Field(default_factory=list)
    custom_fields: List[ClickUpCustomField] = Field(default_factory=list)
    list: ClickUpList
    folder: ClickUpFolder
    space: ClickUpSpace
    url: str
    created_at: datetime
    updated_at: datetime
    archived: bool = False
    creator: ClickUpUser

    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> ClickUpTask:
        """Create a ClickUpTask from ClickUp API response."""
        return cls(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            status=ClickUpTaskStatus.from_api_response(data["status"]),
            priority=ClickUpPriority.from_api_response(data.get("priority")) if data.get("priority") else None,
            due_date=datetime.fromtimestamp(int(data["due_date"]) / 1000) if data.get("due_date") else None,
            start_date=datetime.fromtimestamp(int(data["start_date"]) / 1000) if data.get("start_date") else None,
            time_estimate=data.get("time_estimate"),
            time_spent=data.get("time_spent"),
            assignees=[ClickUpUser.from_api_response(user) for user in data.get("assignees", [])],
            tags=[ClickUpTag.from_api_response(tag) for tag in data.get("tags", [])],
            custom_fields=[ClickUpCustomField.from_api_response(field) for field in data.get("custom_fields", [])],
            list=ClickUpList.from_api_response(data["list"]),
            folder=ClickUpFolder.from_api_response(data["folder"]),
            space=ClickUpSpace.from_api_response(data["space"]),
            url=data["url"],
            created_at=datetime.fromtimestamp(int(data["date_created"]) / 1000),
            updated_at=datetime.fromtimestamp(int(data["date_updated"]) / 1000),
            archived=data.get("archived", False),
            creator=ClickUpUser.from_api_response(data["creator"])
        )


class ClickUpTaskStatus(BaseModel):
    """ClickUp task status model."""
    id: str
    status: str
    color: str
    orderindex: int
    type: str

    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> ClickUpTaskStatus:
        """Create a ClickUpTaskStatus from ClickUp API response."""
        return cls(**data)


class ClickUpPriority(BaseModel):
    """ClickUp priority model."""
    id: str
    priority: str
    color: str
    orderindex: str

    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> ClickUpPriority:
        """Create a ClickUpPriority from ClickUp API response."""
        return cls(**data)


class ClickUpUser(BaseModel):
    """ClickUp user model."""
    id: int
    username: str
    email: str
    color: Optional[str] = None
    profile_picture: Optional[str] = None
    initials: Optional[str] = None

    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> ClickUpUser:
        """Create a ClickUpUser from ClickUp API response."""
        return cls(
            id=data["id"],
            username=data["username"],
            email=data["email"],
            color=data.get("color"),
            profile_picture=data.get("profilePicture"),
            initials=data.get("initials")
        )


class ClickUpTag(BaseModel):
    """ClickUp tag model."""
    name: str
    tag_fg: str
    tag_bg: str
    creator: int

    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> ClickUpTag:
        """Create a ClickUpTag from ClickUp API response."""
        return cls(
            name=data["name"],
            tag_fg=data["tag_fg"],
            tag_bg=data["tag_bg"],
            creator=data["creator"]
        )


class ClickUpCustomField(BaseModel):
    """ClickUp custom field model."""
    id: str
    name: Optional[str] = None
    type: Optional[str] = None
    type_config: Dict[str, Any] = Field(default_factory=dict)
    value: Any = None
    required: bool = False

    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> ClickUpCustomField:
        """Create a ClickUpCustomField from ClickUp API response."""
        return cls(
            id=data["id"],
            name=data.get("name"),
            type=data.get("type"),
            type_config=data.get("type_config", {}),
            value=data.get("value"),
            required=bool(data.get("required", False))
        )


class ClickUpList(BaseModel):
    """ClickUp list model."""
    id: str
    name: str
    access: bool
    archived: bool = False

    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> ClickUpList:
        """Create a ClickUpList from ClickUp API response."""
        return cls(**data)


class ClickUpFolder(BaseModel):
    """ClickUp folder model."""
    id: str
    name: str
    access: bool
    archived: bool = False

    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> ClickUpFolder:
        """Create a ClickUpFolder from ClickUp API response."""
        return cls(**data)


class ClickUpSpace(BaseModel):
    """ClickUp space model."""
    id: str
    name: Optional[str] = None
    access: Optional[bool] = None

    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> ClickUpSpace:
        """Create a ClickUpSpace from ClickUp API response."""
        return cls(**data)


class ClickUpTaskResponse(BaseModel):
    """Response model for ClickUp tasks."""
    id: str
    name: str
    description: Optional[str] = None
    status: str
    priority: Optional[str] = None
    due_date: Optional[datetime] = None
    start_date: Optional[datetime] = None
    assignees: List[str] = Field(default_factory=list)  # usernames
    tags: List[str] = Field(default_factory=list)  # tag names
    url: str
    created_at: datetime
    updated_at: datetime
    customer_id: Optional[str] = None  # extracted from custom fields or name


class ClickUpTasksResponse(BaseModel):
    """Response model for multiple ClickUp tasks."""
    tasks: List[ClickUpTaskResponse]
    total_count: int
    has_more: bool = False



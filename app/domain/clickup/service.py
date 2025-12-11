"""ClickUp service for task management."""

from __future__ import annotations

import logging
import re
from typing import List, Optional, Type

import logfire

from app.adapters.clickup_client import ClickUpClient
from app.domain.clickup.models import (
    ClickUpTask,
    ClickUpTaskResponse,
    ClickUpTasksResponse,
)
from app.errors import BaseAPIException
from app.ports import ClickUpClientProtocol
from app.settings import settings

logger = logging.getLogger(__name__)


class ClickUpService:
    """Service for ClickUp operations."""

    def __init__(self, clickup_client_class: Type[ClickUpClientProtocol] = ClickUpClient):
        self._clickup_client_class = clickup_client_class

    def _client(self) -> ClickUpClientProtocol:
        return self._clickup_client_class()  # type: ignore[return-value]

    def _extract_customer_id_from_task(self, task: ClickUpTask) -> Optional[str]:
        """Extract customer ID from task name or custom fields."""
        # Try to extract from task name (common patterns: [CUST123], CUST-123, #123, etc.)
        patterns = [
            r'\[([A-Z]{3,}\d+)\]',  # [CUST123]
            r'\b([A-Z]{3,}\d+)\b',  # CUST123
            r'#(\d+)',  # #123
            r'(\d{6,})',  # 6+ digits (customer ID)
        ]

        for pattern in patterns:
            match = re.search(pattern, task.name, re.IGNORECASE)
            if match:
                return match.group(1)

        # Check custom fields for customer ID
        for field in task.custom_fields:
            if field.name.lower() in ['customer', 'customer_id', 'client', 'client_id']:
                if isinstance(field.value, str) and field.value.strip():
                    return field.value.strip()

        return None

    def _task_to_response(self, task: ClickUpTask) -> ClickUpTaskResponse:
        """Convert ClickUpTask to ClickUpTaskResponse."""
        return ClickUpTaskResponse(
            id=task.id,
            name=task.name,
            description=task.description,
            status=task.status.status,
            priority=task.priority.priority if task.priority else None,
            due_date=task.due_date,
            start_date=task.start_date,
            assignees=[assignee.username for assignee in task.assignees],
            tags=[tag.name for tag in task.tags],
            url=task.url,
            created_at=task.created_at,
            updated_at=task.updated_at,
            customer_id=self._extract_customer_id_from_task(task)
        )

    async def get_sav_rabotage_tasks(
        self,
        customer_id: Optional[str] = None,
        include_closed: bool = False,
        page: Optional[int] = None
    ) -> ClickUpTasksResponse:
        """Get tasks from SAV/Rabotage folder, optionally filtered by customer ID."""
        with logfire.span("clickup_service.get_sav_rabotage_tasks", customer_id=customer_id):
            async with self._client() as client:
                if not settings.clickup_sav_folder_id:
                    raise ValueError("ClickUp SAV folder ID not configured")

                # Get all lists in the SAV folder
                lists_response = await client.get_lists_in_folder(settings.clickup_sav_folder_id)
                lists = lists_response if isinstance(lists_response, list) else []

                # Filter for Rabotage list if specified
                if settings.clickup_rabotage_list_id:
                    lists = [lst for lst in lists if lst["id"] == settings.clickup_rabotage_list_id]

                all_tasks = []

                # Get tasks from each list
                for list_data in lists:
                    try:
                        tasks_response = await client.get_tasks_in_list(
                            list_data["id"],
                            include_closed=include_closed,
                            page=page
                        )

                        tasks_data = tasks_response.get("tasks", [])
                        for task_data in tasks_data:
                            try:
                                task = ClickUpTask.from_api_response(task_data)
                                task_response = self._task_to_response(task)

                                # Filter by customer ID if specified
                                if customer_id:
                                    if task_response.customer_id == customer_id:
                                        all_tasks.append(task_response)
                                else:
                                    all_tasks.append(task_response)

                            except Exception as exc:
                                logger.warning(
                                    f"Failed to parse task {task_data.get('id', 'unknown')}: {exc}"
                                )
                                continue

                    except Exception as exc:
                        logger.error(f"Failed to get tasks for list {list_data['id']}: {exc}")
                        continue

                return ClickUpTasksResponse(
                    tasks=all_tasks,
                    total_count=len(all_tasks),
                    has_more=False  # TODO: Implement pagination properly
                )

    async def get_task_by_id(self, task_id: str) -> Optional[ClickUpTaskResponse]:
        """Get a specific task by ID."""
        with logfire.span("clickup_service.get_task_by_id", task_id=task_id):
            async with self._client() as client:
                try:
                    task_data = await client.get_task(task_id)
                    task = ClickUpTask.from_api_response(task_data)
                    return self._task_to_response(task)
                except Exception as exc:
                    logger.error(f"Failed to get task {task_id}: {exc}")
                    return None


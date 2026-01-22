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
        """Extract customer ID from task name, description, or custom fields."""
        customer_field_names = {
            "customer",
            "customer id",
            "customer_id",
            "customer no",
            "customer_no",
            "customer number",
            "client",
            "client id",
            "client_id",
            "code client",
            "client code",
        }

        # Prefer explicit custom fields when available
        for field in task.custom_fields:
            if not field.name:
                continue
            if field.name.lower() in customer_field_names:
                if isinstance(field.value, str) and field.value.strip():
                    return field.value.strip()
                if field.value is not None:
                    return str(field.value).strip()

        # Try to extract from task name or description (common patterns)
        patterns = [
            r'\b([A-Z]{5}\d{2})\b',  # LINLU01
            r'\[([A-Z]{3,}\d+)\]',  # [CUST123]
            r'\b([A-Z]{3,}\d+)\b',  # CUST123
            r'#(\d+)',  # #123
            r'(\d{6,})',  # 6+ digits (customer ID)
        ]

        for pattern in patterns:
            match = re.search(pattern, task.name, re.IGNORECASE)
            if match:
                return match.group(1)

        if task.description:
            for pattern in patterns:
                match = re.search(pattern, task.description, re.IGNORECASE)
                if match:
                    return match.group(1)

        return None

    def _task_matches_customer_id(self, task: ClickUpTask, customer_id: str) -> bool:
        """Return True if task matches the provided customer ID."""
        target = customer_id.strip().upper()
        if not target:
            return False
        value = self._extract_customer_id_from_task(task)
        if not value:
            return False
        return value.strip().upper() == target

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
                    from app.adapters.clickup_client import ClickUpConfigurationError
                    raise ClickUpConfigurationError("ClickUp SAV folder ID not configured. Please set CLICKUP_SAV_FOLDER_ID in your .env file.")

                # Get all lists in the SAV folder
                lists_response = await client.get_lists_in_folder(settings.clickup_sav_folder_id)
                lists = lists_response if isinstance(lists_response, list) else []

                # Filter by customer_id if provided (search in list names)
                # If no customer_id provided, include all lists
                if customer_id:
                    filtered_lists = []
                    for lst in lists:
                        list_name_lower = lst.get("name", "").lower()
                        # Check if customer_id appears in the list name
                        if customer_id.lower() in list_name_lower:
                            filtered_lists.append(lst)
                    lists = filtered_lists
                # If no customer_id, include all lists in the folder

                all_tasks = []

                # Get tasks from each matching list
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

                                # When customer_id is provided, we already filtered lists by customer_id,
                                # so include all tasks from those lists
                                if customer_id:
                                    # Since lists were pre-filtered by customer_id, include all tasks
                                    all_tasks.append(task_response)
                                else:
                                    # No filtering, include all tasks
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

    async def get_tasks_for_customer_in_space(
        self,
        space_id: str,
        customer_id: str,
        include_closed: bool = True,
        page: Optional[int] = None
    ) -> ClickUpTasksResponse:
        """Get all tasks in a space filtered by customer ID."""
        with logfire.span(
            "clickup_service.get_tasks_for_customer_in_space",
            space_id=space_id,
            customer_id=customer_id,
            include_closed=include_closed,
            page=page
        ):
            async with self._client() as client:
                folders = await client.get_folders_in_space(space_id)
                folder_lists: List[dict] = []
                for folder in folders:
                    folder_id = folder.get("id")
                    if not folder_id:
                        continue
                    folder_lists.extend(await client.get_lists_in_folder(folder_id))

                space_lists = await client.get_lists_in_space(space_id)

                lists = folder_lists + space_lists
                seen_list_ids = set()
                all_tasks: List[ClickUpTaskResponse] = []

                for list_data in lists:
                    list_id = list_data.get("id")
                    if not list_id or list_id in seen_list_ids:
                        continue
                    seen_list_ids.add(list_id)

                    try:
                        tasks_response = await client.get_tasks_in_list(
                            list_id,
                            include_closed=include_closed,
                            page=page
                        )
                        tasks_data = tasks_response.get("tasks", [])
                        for task_data in tasks_data:
                            try:
                                task = ClickUpTask.from_api_response(task_data)
                                if self._task_matches_customer_id(task, customer_id):
                                    all_tasks.append(self._task_to_response(task))
                            except Exception as exc:
                                logger.warning(
                                    "Failed to parse task %s: %s",
                                    task_data.get("id", "unknown"),
                                    exc
                                )
                                continue
                    except Exception as exc:
                        logger.error("Failed to get tasks for list %s: %s", list_id, exc)
                        continue

                return ClickUpTasksResponse(
                    tasks=all_tasks,
                    total_count=len(all_tasks),
                    has_more=False  # TODO: Implement pagination properly
                )



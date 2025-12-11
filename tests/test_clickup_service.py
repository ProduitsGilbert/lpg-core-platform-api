"""Unit tests for ClickUp service."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.domain.clickup.service import ClickUpService
from app.domain.clickup.models import ClickUpTask, ClickUpTasksResponse


class TestClickUpService:
    """Test suite for ClickUp service methods."""

    @pytest.fixture
    def mock_client(self):
        """Mock ClickUp client."""
        client = MagicMock()
        client.get_lists_in_folder = AsyncMock()
        client.get_tasks_in_list = AsyncMock()
        client.get_task = AsyncMock()
        return client

    @pytest.fixture
    def service(self, mock_client):
        """Create ClickUp service with mocked client."""
        service = ClickUpService()
        service._client = mock_client
        return service

    @patch('app.domain.clickup.service.settings')
    def test_get_sav_rabotage_tasks_success(self, mock_settings, service, mock_client):
        """Test successful retrieval of SAV/Rabotage tasks."""
        # Mock settings
        mock_settings.clickup_sav_folder_id = "folder123"
        mock_settings.clickup_rabotage_list_id = "list456"

        # Mock client responses
        mock_client.get_lists_in_folder.return_value = [
            {"id": "list456", "name": "Rabotage"},
            {"id": "list789", "name": "Other List"}
        ]

        mock_client.get_tasks_in_list.return_value = {
            "tasks": [
                {
                    "id": "task1",
                    "name": "Task 1",
                    "status": {"status": "in progress"},
                    "priority": {"priority": "high"}
                },
                {
                    "id": "task2",
                    "name": "Task 2",
                    "status": {"status": "completed"},
                    "priority": {"priority": "normal"}
                }
            ]
        }

        result = await service.get_sav_rabotage_tasks()

        assert isinstance(result, ClickUpTasksResponse)
        assert len(result.tasks) == 2
        assert result.tasks[0].name == "Task 1"
        assert result.tasks[1].name == "Task 2"
        assert result.total_count == 2

        # Verify client calls
        mock_client.get_lists_in_folder.assert_called_once_with("folder123")
        mock_client.get_tasks_in_list.assert_called_once_with(
            "list456",
            include_closed=False,
            page=None
        )

    @patch('app.domain.clickup.service.settings')
    def test_get_sav_rabotage_tasks_no_rabotage_list(self, mock_settings, service, mock_client):
        """Test when no specific rabotage list is configured."""
        mock_settings.clickup_sav_folder_id = "folder123"
        mock_settings.clickup_rabotage_list_id = None

        mock_client.get_lists_in_folder.return_value = [
            {"id": "list1", "name": "List 1"},
            {"id": "list2", "name": "List 2"}
        ]

        mock_client.get_tasks_in_list.return_value = {"tasks": []}

        result = await service.get_sav_rabotage_tasks()

        assert isinstance(result, ClickUpTasksResponse)
        # Should call get_tasks_in_list for each list
        assert mock_client.get_tasks_in_list.call_count == 2

    @patch('app.domain.clickup.service.settings')
    def test_get_sav_rabotage_tasks_with_customer_filter(self, mock_settings, service, mock_client):
        """Test filtering tasks by customer ID."""
        mock_settings.clickup_sav_folder_id = "folder123"
        mock_settings.clickup_rabotage_list_id = "list456"

        mock_client.get_lists_in_folder.return_value = [{"id": "list456"}]
        mock_client.get_tasks_in_list.return_value = {
            "tasks": [
                {
                    "id": "task1",
                    "name": "[CUST123] Customer Task",
                    "status": {"status": "in progress"}
                },
                {
                    "id": "task2",
                    "name": "Other Task",
                    "status": {"status": "completed"}
                }
            ]
        }

        result = await service.get_sav_rabotage_tasks(customer_id="CUST123")

        assert len(result.tasks) == 1
        assert result.tasks[0].name == "[CUST123] Customer Task"

    def test_customer_id_extraction_patterns(self, service):
        """Test various customer ID extraction patterns."""
        task = ClickUpTask(
            id="task1",
            name="[CUST123] Test Task",
            status="in progress"
        )

        customer_id = service._extract_customer_id_from_task(task)
        assert customer_id == "CUST123"

        # Test different patterns
        task.name = "CUST456 - Another Task"
        customer_id = service._extract_customer_id_from_task(task)
        assert customer_id == "CUST456"

        task.name = "#789 Task with number"
        customer_id = service._extract_customer_id_from_task(task)
        assert customer_id == "789"

    @patch('app.domain.clickup.service.settings')
    def test_get_task_by_id_success(self, mock_settings, service, mock_client):
        """Test successful retrieval of individual task."""
        mock_client.get_task.return_value = {
            "id": "task123",
            "name": "Test Task",
            "status": {"status": "in progress"},
            "priority": {"priority": "high"}
        }

        result = await service.get_task_by_id("task123")

        assert result is not None
        assert result.id == "task123"
        assert result.name == "Test Task"

        mock_client.get_task.assert_called_once_with("task123")

    def test_get_task_by_id_not_found(self, service, mock_client):
        """Test task not found scenario."""
        mock_client.get_task.return_value = None

        result = await service.get_task_by_id("nonexistent")

        assert result is None

    @patch('app.domain.clickup.service.logger')
    @patch('app.domain.clickup.service.settings')
    def test_error_handling_list_operations(self, mock_settings, mock_logger, service, mock_client):
        """Test error handling during list operations."""
        mock_settings.clickup_sav_folder_id = "folder123"
        mock_client.get_lists_in_folder.side_effect = Exception("API Error")

        result = await service.get_sav_rabotage_tasks()

        # Should return empty response on error
        assert isinstance(result, ClickUpTasksResponse)
        assert len(result.tasks) == 0
        mock_logger.error.assert_called()

    @patch('app.domain.clickup.service.logger')
    def test_error_handling_task_retrieval(self, mock_logger, service, mock_client):
        """Test error handling during task retrieval."""
        mock_client.get_task.side_effect = Exception("API Error")

        result = await service.get_task_by_id("task123")

        assert result is None
        mock_logger.error.assert_called()

    @patch('app.domain.clickup.service.settings')
    def test_pagination_support(self, mock_settings, service, mock_client):
        """Test pagination parameter passing."""
        mock_settings.clickup_sav_folder_id = "folder123"
        mock_settings.clickup_rabotage_list_id = "list456"

        mock_client.get_lists_in_folder.return_value = [{"id": "list456"}]
        mock_client.get_tasks_in_list.return_value = {"tasks": []}

        result = await service.get_sav_rabotage_tasks(page=2)

        mock_client.get_tasks_in_list.assert_called_once_with(
            "list456",
            include_closed=False,
            page=2
        )

    def test_task_response_conversion(self, service):
        """Test conversion of API response to domain model."""
        api_response = {
            "id": "task123",
            "name": "Test Task",
            "status": {"status": "in progress"},
            "priority": {"priority": "urgent"},
            "due_date": "1640995200000",  # Example timestamp
            "date_created": "1640908800000"
        }

        task = ClickUpTask.from_api_response(api_response)

        assert task.id == "task123"
        assert task.name == "Test Task"
        assert task.status == "in progress"
        assert task.priority == "urgent"

    def test_empty_folder_handling(self, service, mock_client):
        """Test handling of empty folder with no lists."""
        mock_client.get_lists_in_folder.return_value = []

        result = await service.get_sav_rabotage_tasks()

        assert isinstance(result, ClickUpTasksResponse)
        assert len(result.tasks) == 0
        # Should not call get_tasks_in_list if no lists
        mock_client.get_tasks_in_list.assert_not_called()

    @patch('app.domain.clickup.service.settings')
    def test_include_closed_parameter(self, mock_settings, service, mock_client):
        """Test include_closed parameter handling."""
        mock_settings.clickup_sav_folder_id = "folder123"
        mock_settings.clickup_rabotage_list_id = "list456"

        mock_client.get_lists_in_folder.return_value = [{"id": "list456"}]
        mock_client.get_tasks_in_list.return_value = {"tasks": []}

        # Test with include_closed=True
        await service.get_sav_rabotage_tasks(include_closed=True)

        mock_client.get_tasks_in_list.assert_called_with(
            "list456",
            include_closed=True,
            page=None
        )

        # Reset mock
        mock_client.get_tasks_in_list.reset_mock()

        # Test with include_closed=False (default)
        await service.get_sav_rabotage_tasks(include_closed=False)

        mock_client.get_tasks_in_list.assert_called_with(
            "list456",
            include_closed=False,
            page=None
        )

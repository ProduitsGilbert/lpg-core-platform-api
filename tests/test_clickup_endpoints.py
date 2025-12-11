"""Tests for ClickUp API endpoints."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI

from app.api.v1.clickup.router import router as clickup_router
from app.domain.clickup.models import ClickUpTaskResponse, ClickUpTasksResponse


@pytest.fixture
def test_app():
    """Create test FastAPI app with only ClickUp routes."""
    app = FastAPI()
    app.include_router(clickup_router, prefix="/api/v1")
    return app


@pytest.fixture
def test_client(test_app):
    """Create test client for FastAPI app."""
    return TestClient(test_app)


@pytest.fixture
def mock_clickup_service():
    """Mock ClickUp service for testing."""
    with patch('app.api.v1.clickup.tasks.clickup_service') as mock_service:
        yield mock_service


class TestClickUpTasksEndpoints:
    """Test suite for ClickUp tasks endpoints."""

    def test_get_sav_rabotage_tasks_success(self, test_client, mock_clickup_service):
        """Test successful retrieval of SAV/Rabotage tasks."""
        # Mock the service response
        mock_response = ClickUpTasksResponse(
            tasks=[
                ClickUpTaskResponse(
                    id="abc123",
                    name="Test Task 1",
                    status="in progress",
                    priority="high"
                ),
                ClickUpTaskResponse(
                    id="def456",
                    name="Test Task 2",
                    status="completed",
                    priority="normal"
                )
            ],
            total_count=2,
            has_more=False
        )

        mock_clickup_service.get_sav_rabotage_tasks = AsyncMock(return_value=mock_response)

        response = test_client.get(
            "/api/v1/clickup/tasks/sav-rabotage?customer_id=CUST123&include_closed=false&page=1"
        )

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert len(data["data"]) == 2
        assert data["data"][0]["name"] == "Test Task 1"
        assert data["data"][1]["name"] == "Test Task 2"

        # Verify service was called with correct parameters
        mock_clickup_service.get_sav_rabotage_tasks.assert_called_once_with(
            customer_id="CUST123",
            include_closed=False,
            page=1
        )

    def test_get_sav_rabotage_tasks_no_customer_filter(self, test_client, mock_clickup_service):
        """Test SAV/Rabotage tasks without customer filtering."""
        mock_response = ClickUpTasksResponse(tasks=[], total_count=0, has_more=False)
        mock_clickup_service.get_sav_rabotage_tasks = AsyncMock(return_value=mock_response)

        response = test_client.get("/api/v1/clickup/tasks/sav-rabotage")

        assert response.status_code == 200
        mock_clickup_service.get_sav_rabotage_tasks.assert_called_once_with(
            customer_id=None,
            include_closed=True,
            page=None
        )

    def test_get_sav_rabotage_tasks_include_closed(self, test_client, mock_clickup_service):
        """Test SAV/Rabotage tasks with include_closed parameter."""
        mock_response = ClickUpTasksResponse(tasks=[], total_count=0, has_more=False)
        mock_clickup_service.get_sav_rabotage_tasks = AsyncMock(return_value=mock_response)

        response = test_client.get("/api/v1/clickup/tasks/sav-rabotage?include_closed=true")

        assert response.status_code == 200
        mock_clickup_service.get_sav_rabotage_tasks.assert_called_once_with(
            customer_id=None,
            include_closed=True,
            page=None
        )

    def test_get_task_by_id_success(self, test_client, mock_clickup_service):
        """Test successful retrieval of individual task."""
        mock_task = ClickUpTaskResponse(
            id="task123",
            name="Individual Task",
            status="in progress",
            priority="urgent"
        )

        mock_clickup_service.get_task_by_id = AsyncMock(return_value=mock_task)

        response = test_client.get("/api/v1/clickup/tasks/sav-rabotage/task123")

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert data["data"]["id"] == "task123"
        assert data["data"]["name"] == "Individual Task"

        mock_clickup_service.get_task_by_id.assert_called_once_with("task123")

    def test_get_task_by_id_not_found(self, test_client, mock_clickup_service):
        """Test task not found scenario."""
        mock_clickup_service.get_task_by_id = AsyncMock(return_value=None)

        response = test_client.get("/api/v1/clickup/tasks/sav-rabotage/nonexistent")

        assert response.status_code == 404
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "TASK_NOT_FOUND"

    @patch('app.api.v1.clickup.tasks.logger')
    def test_service_exception_handling(self, mock_logger, test_client, mock_clickup_service):
        """Test that service exceptions are properly handled."""
        from app.errors import ExternalServiceException

        # Mock service to raise an exception
        mock_clickup_service.get_sav_rabotage_tasks.side_effect = ExternalServiceException(
            "ClickUp API unavailable",
            service="clickup"
        )

        response = test_client.get("/api/v1/clickup/tasks/sav-rabotage")

        assert response.status_code == 503  # Service Unavailable
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "EXTERNAL_SERVICE_ERROR"
        assert "ClickUp API unavailable" in data["error"]["detail"]

        # Verify logging occurred
        mock_logger.error.assert_called()

    def test_invalid_page_parameter(self, test_client):
        """Test validation of page parameter."""
        response = test_client.get("/api/v1/clickup/tasks/sav-rabotage?page=0")
        assert response.status_code == 422  # Unprocessable Entity

        response = test_client.get("/api/v1/clickup/tasks/sav-rabotage?page=-1")
        assert response.status_code == 422

    def test_boolean_parameter_validation(self, test_client):
        """Test validation of boolean include_closed parameter."""
        # Valid boolean values should work (would fail at service level)
        response = test_client.get("/api/v1/clickup/tasks/sav-rabotage?include_closed=true")
        assert response.status_code == 200 or response.status_code == 503  # Service level error is OK

        response = test_client.get("/api/v1/clickup/tasks/sav-rabotage?include_closed=false")
        assert response.status_code == 200 or response.status_code == 503

        # Invalid boolean values should fail validation
        response = test_client.get("/api/v1/clickup/tasks/sav-rabotage?include_closed=maybe")
        assert response.status_code == 422

    def test_customer_id_parameter(self, test_client):
        """Test customer_id parameter handling."""
        # Test with various customer ID formats
        response = test_client.get("/api/v1/clickup/tasks/sav-rabotage?customer_id=12345")
        assert response.status_code == 200 or response.status_code == 503

        response = test_client.get("/api/v1/clickup/tasks/sav-rabotage?customer_id=CUST-123")
        assert response.status_code == 200 or response.status_code == 503

        response = test_client.get("/api/v1/clickup/tasks/sav-rabotage?customer_id=test@example.com")
        assert response.status_code == 200 or response.status_code == 503

    def test_empty_customer_id(self, test_client, mock_clickup_service):
        """Test handling of empty customer_id parameter."""
        mock_response = ClickUpTasksResponse(tasks=[], total_count=0, has_more=False)
        mock_clickup_service.get_sav_rabotage_tasks = AsyncMock(return_value=mock_response)

        response = test_client.get("/api/v1/clickup/tasks/sav-rabotage?customer_id=")

        assert response.status_code == 200
        mock_clickup_service.get_sav_rabotage_tasks.assert_called_once_with(
            customer_id="",
            include_closed=True,
            page=None
        )

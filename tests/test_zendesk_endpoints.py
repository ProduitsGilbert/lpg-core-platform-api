"""Tests for Zendesk API endpoints."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI
from httpx import AsyncClient

from app.api.v1.zendesk.tickets import router as zendesk_router
from app.domain.zendesk.models import ZendeskTicket, ZendeskTicketsResponse


@pytest.fixture
def test_app():
    """Create test FastAPI app with only Zendesk routes."""
    app = FastAPI()
    app.include_router(zendesk_router, prefix="/api/v1")
    return app


@pytest.fixture
def test_client(test_app):
    """Create test client for FastAPI app."""
    return TestClient(test_app)


@pytest.fixture
def mock_zendesk_service():
    """Mock Zendesk service for testing."""
    with patch('app.api.v1.zendesk.tickets.zendesk_service') as mock_service:
        yield mock_service


class TestZendeskTicketsEndpoints:
    """Test suite for Zendesk tickets endpoints."""

    def test_get_open_tickets_success(self, test_client, mock_zendesk_service):
        """Test successful retrieval of open tickets."""
        # Mock the service response
        mock_response = ZendeskTicketsResponse(
            tickets=[
                ZendeskTicket(
                    id=123,
                    subject="Test Ticket 1",
                    status="open",
                    requester_id=456,
                    created_at="2024-01-01T00:00:00Z"
                ),
                ZendeskTicket(
                    id=124,
                    subject="Test Ticket 2",
                    status="open",
                    requester_id=457,
                    created_at="2024-01-02T00:00:00Z"
                )
            ],
            count=2
        )

        mock_zendesk_service.get_open_tickets = AsyncMock(return_value=mock_response)

        response = test_client.get("/api/v1/zendesk/tickets/open?page=1&per_page=25")

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert len(data["data"]) == 2
        assert data["data"][0]["ticket"]["subject"] == "Test Ticket 1"
        assert data["data"][1]["ticket"]["subject"] == "Test Ticket 2"

        # Verify service was called with correct parameters
        mock_zendesk_service.get_open_tickets.assert_called_once_with(
            page=1,
            per_page=25
        )

    def test_get_open_tickets_with_pagination(self, test_client, mock_zendesk_service):
        """Test open tickets endpoint with pagination parameters."""
        mock_response = ZendeskTicketsResponse(tickets=[], count=0)
        mock_zendesk_service.get_open_tickets = AsyncMock(return_value=mock_response)

        response = test_client.get("/api/v1/zendesk/tickets/open?page=2&per_page=10")

        assert response.status_code == 200
        mock_zendesk_service.get_open_tickets.assert_called_once_with(
            page=2,
            per_page=10
        )

    def test_get_open_tickets_default_params(self, test_client, mock_zendesk_service):
        """Test open tickets endpoint with default parameters."""
        mock_response = ZendeskTicketsResponse(tickets=[], count=0)
        mock_zendesk_service.get_open_tickets = AsyncMock(return_value=mock_response)

        response = test_client.get("/api/v1/zendesk/tickets/open")

        assert response.status_code == 200
        mock_zendesk_service.get_open_tickets.assert_called_once_with(
            page=None,
            per_page=None
        )

    def test_get_tickets_for_customer_success(self, test_client, mock_zendesk_service):
        """Test successful retrieval of customer tickets."""
        mock_response = ZendeskTicketsResponse(
            tickets=[
                ZendeskTicket(
                    id=125,
                    subject="Customer Ticket",
                    status="open",
                    requester_id=456,
                    created_at="2024-01-01T00:00:00Z"
                )
            ],
            count=1
        )

        mock_zendesk_service.get_tickets_for_customer = AsyncMock(return_value=mock_response)

        response = test_client.get(
            "/api/v1/zendesk/tickets/customer/test@example.com?include_closed=false&page=1"
        )

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert len(data["data"]) == 1
        assert data["data"][0]["ticket"]["subject"] == "Customer Ticket"

        mock_zendesk_service.get_tickets_for_customer.assert_called_once_with(
            customer_id="test@example.com",
            include_closed=False,
            page=1,
            per_page=None
        )

    def test_get_tickets_for_customer_organization_id(self, test_client, mock_zendesk_service):
        """Test customer tickets with organization ID (numeric)."""
        mock_response = ZendeskTicketsResponse(tickets=[], count=0)
        mock_zendesk_service.get_tickets_for_customer = AsyncMock(return_value=mock_response)

        response = test_client.get("/api/v1/zendesk/tickets/customer/12345")

        assert response.status_code == 200
        mock_zendesk_service.get_tickets_for_customer.assert_called_once_with(
            customer_id="12345",
            include_closed=True,
            page=None,
            per_page=None
        )

    def test_get_past_year_tickets_success(self, test_client, mock_zendesk_service):
        """Test successful retrieval of past year tickets."""
        mock_response = ZendeskTicketsResponse(
            tickets=[
                ZendeskTicket(
                    id=126,
                    subject="Old Ticket",
                    status="closed",
                    requester_id=456,
                    created_at="2024-01-01T00:00:00Z"
                )
            ],
            count=1
        )

        mock_zendesk_service.get_past_year_tickets = AsyncMock(return_value=mock_response)

        response = test_client.get("/api/v1/zendesk/tickets/past-year?page=1&per_page=50")

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert len(data["data"]) == 1

        mock_zendesk_service.get_past_year_tickets.assert_called_once_with(
            page=1,
            per_page=50
        )

    def test_get_ticket_by_id_success(self, test_client, mock_zendesk_service):
        """Test successful retrieval of individual ticket."""
        mock_ticket = ZendeskTicket(
            id=127,
            subject="Individual Ticket",
            status="open",
            requester_id=456,
            created_at="2024-01-01T00:00:00Z"
        )

        mock_zendesk_service.get_ticket_by_id = AsyncMock(return_value=mock_ticket)

        response = test_client.get("/api/v1/zendesk/tickets/127")

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert data["data"]["ticket"]["id"] == 127
        assert data["data"]["ticket"]["subject"] == "Individual Ticket"

        mock_zendesk_service.get_ticket_by_id.assert_called_once_with(127)

    def test_get_ticket_by_id_not_found(self, test_client, mock_zendesk_service):
        """Test ticket not found scenario."""
        mock_zendesk_service.get_ticket_by_id = AsyncMock(return_value=None)

        response = test_client.get("/api/v1/zendesk/tickets/999")

        assert response.status_code == 404
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "TICKET_NOT_FOUND"

    @patch('app.api.v1.zendesk.tickets.logger')
    def test_service_exception_handling(self, mock_logger, test_client, mock_zendesk_service):
        """Test that service exceptions are properly handled."""
        from app.errors import ExternalServiceException

        # Mock service to raise an exception
        mock_zendesk_service.get_open_tickets.side_effect = ExternalServiceException(
            "Zendesk API unavailable",
            service="zendesk"
        )

        response = test_client.get("/api/v1/zendesk/tickets/open")

        assert response.status_code == 503  # Service Unavailable
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "EXTERNAL_SERVICE_ERROR"
        assert "Zendesk API unavailable" in data["error"]["detail"]

        # Verify logging occurred
        mock_logger.error.assert_called()

    def test_invalid_pagination_params(self, test_client):
        """Test validation of pagination parameters."""
        # Test invalid page number
        response = test_client.get("/api/v1/zendesk/tickets/open?page=0")
        assert response.status_code == 422

        # Test invalid per_page
        response = test_client.get("/api/v1/zendesk/tickets/open?per_page=150")
        assert response.status_code == 422

    def test_customer_id_validation(self, test_client):
        """Test customer ID parameter validation."""
        response = test_client.get("/api/v1/zendesk/tickets/customer/")
        assert response.status_code == 405  # Method not allowed (empty customer_id)

        response = test_client.get("/api/v1/zendesk/tickets/customer/valid@example.com")
        assert response.status_code == 200  # Would fail at service level but validates parameter

    def test_ticket_id_validation(self, test_client):
        """Test ticket ID parameter validation."""
        response = test_client.get("/api/v1/zendesk/tickets/abc")
        assert response.status_code == 422  # Invalid integer

        response = test_client.get("/api/v1/zendesk/tickets/123")
        assert response.status_code == 200  # Would fail at service level but validates parameter

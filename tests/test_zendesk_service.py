"""Unit tests for Zendesk service."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

from app.domain.zendesk.service import ZendeskService
from app.domain.zendesk.models import ZendeskTicket, ZendeskTicketsResponse


class TestZendeskService:
    """Test suite for Zendesk service methods."""

    @pytest.fixture
    def mock_client(self):
        """Mock Zendesk client."""
        client = MagicMock()
        client.search_tickets = AsyncMock()
        client.list_tickets = AsyncMock()
        client.get_ticket = AsyncMock()
        return client

    @pytest.fixture
    def service(self, mock_client):
        """Create Zendesk service with mocked client."""
        service = ZendeskService()
        service._client = mock_client
        return service

    @pytest.mark.asyncio
    async def test_get_tickets_for_customer_email(self, service, mock_client):
        """Test getting tickets for customer by email."""
        # Mock response
        mock_client.search_tickets.return_value = {
            "results": [
                {
                    "result_type": "ticket",
                    "ticket": {
                        "id": 123,
                        "subject": "Test Ticket",
                        "status": "open",
                        "requester_id": 456,
                        "created_at": "2024-01-01T00:00:00Z"
                    }
                }
            ],
            "count": 1
        }

        result = await service.get_tickets_for_customer("test@example.com")

        assert isinstance(result, ZendeskTicketsResponse)
        assert len(result.tickets) == 1
        assert result.tickets[0].id == 123
        assert result.tickets[0].subject == "Test Ticket"

        # Verify search was called with email query
        mock_client.search_tickets.assert_called_once()
        call_args = mock_client.search_tickets.call_args
        assert "requester:test@example.com" in call_args[1]["query"]
        assert "status<solved" not in call_args[1]["query"]  # include_closed=True by default

    @pytest.mark.asyncio
    async def test_get_tickets_for_customer_organization(self, service, mock_client):
        """Test getting tickets for customer by organization ID."""
        mock_client.search_tickets.return_value = {
            "results": [],
            "count": 0
        }

        result = await service.get_tickets_for_customer("ORG123")

        assert isinstance(result, ZendeskTicketsResponse)
        assert len(result.tickets) == 0

        # Verify search was called with organization query
        mock_client.search_tickets.assert_called_once()
        call_args = mock_client.search_tickets.call_args
        assert "organization:ORG123" in call_args[1]["query"]

    @pytest.mark.asyncio
    async def test_get_tickets_for_customer_exclude_closed(self, service, mock_client):
        """Test getting tickets excluding closed ones."""
        mock_client.search_tickets.return_value = {
            "results": [],
            "count": 0
        }

        result = await service.get_tickets_for_customer("test@example.com", include_closed=False)

        # Verify search was called with status filter
        mock_client.search_tickets.assert_called_once()
        call_args = mock_client.search_tickets.call_args
        assert "status<solved" in call_args[1]["query"]

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_get_open_tickets(self, service, mock_client):
        """Test getting open tickets."""
        mock_client.search_tickets.return_value = {
            "results": [
                {
                    "result_type": "ticket",
                    "ticket": {
                    "id": 124,
                    "subject": "Open Ticket",
                    "status": "open",
                    "requester_id": 457,
                    "created_at": "2024-01-02T00:00:00Z"
                    }
                }
            ],
            "count": 1
        }

        result = await service.get_open_tickets()

        assert isinstance(result, ZendeskTicketsResponse)
        assert len(result.tickets) == 1
        assert result.tickets[0].status == "open"

        # Verify search_tickets was called with status:open query
        mock_client.search_tickets.assert_called_once()
        args, kwargs = mock_client.search_tickets.call_args
        assert "status:open" in kwargs["query"]
        )

    @pytest.mark.asyncio
    async def test_get_past_year_tickets(self, service, mock_client):
        """Test getting tickets from the past year."""
        mock_client.search_tickets.return_value = {
            "results": [
                {
                    "result_type": "ticket",
                    "ticket": {
                        "id": 125,
                        "subject": "Recent Ticket",
                        "status": "solved",
                        "requester_id": 458,
                        "created_at": "2024-06-01T00:00:00Z"
                    }
                }
            ],
            "count": 1
        }

        result = await service.get_past_year_tickets()

        assert isinstance(result, ZendeskTicketsResponse)
        assert len(result.tickets) == 1

        # Verify search was called with date filter
        mock_client.search_tickets.assert_called_once()
        call_args = mock_client.search_tickets.call_args
        query = call_args[1]["query"]
        assert "created>" in query
        # Should filter for tickets created after a date about 1 year ago
        assert "2024-" in query or "2025-" in query

    @pytest.mark.asyncio
    async def test_get_ticket_by_id_success(self, service, mock_client):
        """Test getting individual ticket by ID."""
        mock_client.get_ticket.return_value = {
            "ticket": {
                "id": 126,
                "subject": "Individual Ticket",
                "status": "pending",
                "requester_id": 459,
                "created_at": "2024-01-03T00:00:00Z"
            }
        }

        result = await service.get_ticket_by_id(126)

        assert isinstance(result, ZendeskTicket)
        assert result.id == 126
        assert result.subject == "Individual Ticket"

        mock_client.get_ticket.assert_called_once_with(126)

    @pytest.mark.asyncio
    async def test_get_ticket_by_id_not_found(self, service, mock_client):
        """Test getting non-existent ticket."""
        mock_client.get_ticket.return_value = {}

        result = await service.get_ticket_by_id(999)

        assert result is None

    @patch('app.domain.zendesk.service.logger')
    @pytest.mark.asyncio
    async def test_service_error_handling(self, mock_logger, service, mock_client):
        """Test that service properly handles and logs errors."""
        from app.errors import ExternalServiceException

        mock_client.search_tickets.side_effect = Exception("API Error")

        with pytest.raises(ExternalServiceException) as exc_info:
            await service.get_tickets_for_customer("test@example.com")

        assert "Failed to retrieve tickets for customer test@example.com" in str(exc_info.value)
        mock_logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_ticket_parsing_error_handling(self, service, mock_client):
        """Test handling of malformed ticket data."""
        mock_client.list_tickets.return_value = {
            "tickets": [
                {
                    "id": "invalid",  # Should be int
                    "subject": None,  # Missing required field
                    "status": "open",
                    "requester_id": 456,
                }
            ],
            "count": 1
        }

        result = await service.get_open_tickets()

        # Should handle parsing errors gracefully
        # Either skip invalid tickets or log warnings
        assert isinstance(result, ZendeskTicketsResponse)

    @pytest.mark.asyncio
    async def test_pagination_parameters(self, service, mock_client):
        """Test that pagination parameters are passed correctly."""
        mock_client.list_tickets.return_value = {"tickets": [], "count": 0}

        await service.get_open_tickets(page=2, per_page=50)

        mock_client.list_tickets.assert_called_once_with(
            status="open",
            page=2,
            per_page=50,
            sort_by=None,
            sort_order=None
        )

    @pytest.mark.asyncio
    async def test_customer_id_edge_cases(self, service, mock_client):
        """Test customer ID parsing for different formats."""
        mock_client.search_tickets.return_value = {"results": [], "count": 0}

        # Test email-like string without @ (should be treated as org ID)
        await service.get_tickets_for_customer("CUST123")

        call_args = mock_client.search_tickets.call_args
        assert "organization:CUST123" in call_args[1]["query"]

        # Reset mock
        mock_client.search_tickets.reset_mock()

        # Test email with @ symbol
        await service.get_tickets_for_customer("user@company.com")

        call_args = mock_client.search_tickets.call_args
        assert "requester:user@company.com" in call_args[1]["query"]

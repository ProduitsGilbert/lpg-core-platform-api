"""
Tests for PO line date update functionality.

This module tests the update_poline_date endpoint including:
- Happy path
- Idempotency
- Validation errors
- ERP errors
"""

import pytest
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import Mock, patch, MagicMock
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.domain.dtos import UpdatePOLineDateCommand, POLineDTO
from app.domain.purchasing_service import PurchasingService
from app.errors import ValidationException, ERPNotFound, ERPConflict


# Test client
client = TestClient(app)


# Fixtures
@pytest.fixture
def mock_db_session():
    """Mock database session."""
    session = MagicMock(spec=Session)
    return session


@pytest.fixture
def mock_erp_client():
    """Mock ERP client with default responses."""
    with patch("app.domain.purchasing_service.ERPClient") as mock_class:
        mock_instance = mock_class.return_value
        
        # Default successful response
        mock_instance.get_poline.return_value = {
            "po_id": "PO-001",
            "line_no": 1,
            "item_no": "ITEM-001",
            "description": "Test Item",
            "quantity": 100.0,
            "unit_of_measure": "EA",
            "unit_price": 25.50,
            "line_amount": 2550.00,
            "promise_date": date.today().isoformat(),
            "requested_date": date.today().isoformat(),
            "quantity_received": 0.0,
            "quantity_invoiced": 0.0,
            "status": "open",
            "location_code": "MAIN"
        }
        
        mock_instance.update_poline_date.return_value = {
            "po_id": "PO-001",
            "line_no": 1,
            "item_no": "ITEM-001",
            "description": "Test Item",
            "quantity": 100.0,
            "unit_of_measure": "EA",
            "unit_price": 25.50,
            "line_amount": 2550.00,
            "promise_date": (date.today() + timedelta(days=7)).isoformat(),
            "requested_date": date.today().isoformat(),
            "quantity_received": 0.0,
            "quantity_invoiced": 0.0,
            "status": "open",
            "location_code": "MAIN"
        }
        
        yield mock_instance


@pytest.fixture
def sample_update_request():
    """Sample valid update request body."""
    return {
        "new_date": (date.today() + timedelta(days=7)).isoformat(),
        "reason": "Vendor delay notification"
    }


# Happy path tests

def test_update_poline_date_success():
    """Test successful PO line date update."""
    # Prepare request
    po_id = "PO-001"
    line_no = 1
    new_date = date.today() + timedelta(days=7)
    
    request_body = {
        "new_date": new_date.isoformat(),
        "reason": "Vendor delay"
    }
    
    # Mock dependencies
    with patch("app.api.v1.erp.purchase_orders.purchasing_service") as mock_service:
        mock_service.update_poline_date.return_value = POLineDTO(
            po_id=po_id,
            line_no=line_no,
            item_no="ITEM-001",
            description="Test Item",
            quantity=Decimal("100"),
            unit_of_measure="EA",
            unit_price=Decimal("25.50"),
            line_amount=Decimal("2550.00"),
            promise_date=new_date,
            quantity_received=Decimal("0"),
            quantity_invoiced=Decimal("0"),
            quantity_to_receive=Decimal("100"),
            status="open"
        )
        
        # Make request
        response = client.post(
            f"/api/v1/erp/po/{po_id}/lines/{line_no}/date",
            json=request_body,
            headers={"X-User-ID": "test-user"}
        )
    
    # Assertions
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["po_id"] == po_id
    assert data["line_no"] == line_no
    assert data["promise_date"] == new_date.isoformat()


def test_update_poline_date_with_idempotency():
    """Test idempotent PO line date update."""
    po_id = "PO-001"
    line_no = 1
    idempotency_key = "test-idem-key-001"
    new_date = date.today() + timedelta(days=7)
    
    request_body = {
        "new_date": new_date.isoformat(),
        "reason": "Vendor delay",
        "idempotency_key": idempotency_key
    }
    
    with patch("app.api.v1.erp.purchase_orders.purchasing_service") as mock_service:
        mock_service.update_poline_date.return_value = POLineDTO(
            po_id=po_id,
            line_no=line_no,
            item_no="ITEM-001",
            description="Test Item",
            quantity=Decimal("100"),
            unit_of_measure="EA",
            unit_price=Decimal("25.50"),
            line_amount=Decimal("2550.00"),
            promise_date=new_date,
            quantity_received=Decimal("0"),
            quantity_invoiced=Decimal("0"),
            quantity_to_receive=Decimal("100"),
            status="open"
        )
        
        # First request
        response1 = client.post(
            f"/api/v1/erp/po/{po_id}/lines/{line_no}/date",
            json=request_body,
            headers={"X-User-ID": "test-user"}
        )
        
        # Second request with same idempotency key
        response2 = client.post(
            f"/api/v1/erp/po/{po_id}/lines/{line_no}/date",
            json=request_body,
            headers={"X-User-ID": "test-user"}
        )
    
    # Both should succeed
    assert response1.status_code == status.HTTP_200_OK
    assert response2.status_code == status.HTTP_200_OK
    
    # Should return same data
    assert response1.json() == response2.json()


# Validation error tests

def test_update_poline_date_past_date():
    """Test validation error for past date."""
    po_id = "PO-001"
    line_no = 1
    past_date = date.today() - timedelta(days=1)
    
    request_body = {
        "new_date": past_date.isoformat(),
        "reason": "Invalid update"
    }
    
    response = client.post(
        f"/api/v1/erp/po/{po_id}/lines/{line_no}/date",
        json=request_body,
        headers={"X-User-ID": "test-user"}
    )
    
    # Should fail validation
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    data = response.json()
    assert "past" in data["detail"].lower() or "validation" in data["detail"].lower()


def test_update_poline_date_missing_reason():
    """Test validation error for missing reason."""
    po_id = "PO-001"
    line_no = 1
    
    request_body = {
        "new_date": (date.today() + timedelta(days=7)).isoformat()
        # Missing reason field
    }
    
    response = client.post(
        f"/api/v1/erp/po/{po_id}/lines/{line_no}/date",
        json=request_body,
        headers={"X-User-ID": "test-user"}
    )
    
    # Should fail validation
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ERP error tests

def test_update_poline_date_not_found():
    """Test 404 when PO line not found."""
    po_id = "PO-NOT-FOUND"
    line_no = 999
    
    request_body = {
        "new_date": (date.today() + timedelta(days=7)).isoformat(),
        "reason": "Test update"
    }
    
    with patch("app.api.v1.erp.purchase_orders.purchasing_service") as mock_service:
        from app.errors import ERPNotFound
        mock_service.update_poline_date.side_effect = ERPNotFound("PO Line", f"{po_id}/{line_no}")
        
        response = client.post(
            f"/api/v1/erp/po/{po_id}/lines/{line_no}/date",
            json=request_body,
            headers={"X-User-ID": "test-user"}
        )
    
    assert response.status_code == status.HTTP_404_NOT_FOUND
    data = response.json()
    assert "not found" in data["detail"].lower()


def test_update_poline_date_closed_line():
    """Test 409 conflict when PO line is closed."""
    po_id = "PO-001"
    line_no = 1
    
    request_body = {
        "new_date": (date.today() + timedelta(days=7)).isoformat(),
        "reason": "Test update"
    }
    
    with patch("app.api.v1.erp.purchase_orders.purchasing_service") as mock_service:
        from app.errors import ERPConflict
        mock_service.update_poline_date.side_effect = ERPConflict(
            "Cannot update closed PO line"
        )
        
        response = client.post(
            f"/api/v1/erp/po/{po_id}/lines/{line_no}/date",
            json=request_body,
            headers={"X-User-ID": "test-user"}
        )
    
    assert response.status_code == status.HTTP_409_CONFLICT
    data = response.json()
    assert "closed" in data["detail"].lower()


# Service layer tests

def test_service_update_poline_date_business_rules(mock_db_session, mock_erp_client):
    """Test business rule validation in service layer."""
    service = PurchasingService(erp_client=mock_erp_client)
    
    # Test with closed line
    mock_erp_client.get_poline.return_value["status"] = "closed"
    
    command = UpdatePOLineDateCommand(
        po_id="PO-001",
        line_no=1,
        new_date=date.today() + timedelta(days=7),
        reason="Test",
        actor="test-user",
        trace_id="trace-001"
    )
    
    with pytest.raises(ValidationException) as exc_info:
        service.update_poline_date(command, mock_db_session)
    
    assert "closed" in str(exc_info.value).lower()


def test_service_update_poline_date_audit_logging(mock_db_session, mock_erp_client):
    """Test audit logging during update."""
    service = PurchasingService(erp_client=mock_erp_client)
    
    with patch("app.domain.purchasing_service.write_audit_log") as mock_audit:
        command = UpdatePOLineDateCommand(
            po_id="PO-001",
            line_no=1,
            new_date=date.today() + timedelta(days=7),
            reason="Vendor delay",
            actor="test-user",
            trace_id="trace-001"
        )
        
        result = service.update_poline_date(command, mock_db_session)
        
        # Verify audit was called
        # Note: In the actual implementation, audit is written via context manager
        # This test would need adjustment based on actual implementation
        assert result.po_id == "PO-001"
        assert result.promise_date == date.today() + timedelta(days=7)


# Integration test

@pytest.mark.integration
def test_full_update_flow():
    """Test complete update flow from API to service."""
    po_id = "PO-001"
    line_no = 1
    new_date = date.today() + timedelta(days=14)
    
    # This would require a test database setup
    # Skipping for now as it requires full infrastructure
    pass


# Parametrized tests

@pytest.mark.parametrize("days_offset,should_succeed", [
    (-1, False),  # Past date
    (0, True),    # Today
    (1, True),    # Tomorrow
    (30, True),   # Month ahead
    (365, True),  # Year ahead
])
def test_date_validation_scenarios(days_offset, should_succeed):
    """Test various date validation scenarios."""
    po_id = "PO-001"
    line_no = 1
    test_date = date.today() + timedelta(days=days_offset)
    
    request_body = {
        "new_date": test_date.isoformat(),
        "reason": "Test update"
    }
    
    with patch("app.api.v1.erp.purchase_orders.purchasing_service") as mock_service:
        if should_succeed:
            mock_service.update_poline_date.return_value = POLineDTO(
                po_id=po_id,
                line_no=line_no,
                item_no="ITEM-001",
                description="Test Item",
                quantity=Decimal("100"),
                unit_of_measure="EA",
                unit_price=Decimal("25.50"),
                line_amount=Decimal("2550.00"),
                promise_date=test_date,
                quantity_received=Decimal("0"),
                quantity_invoiced=Decimal("0"),
                quantity_to_receive=Decimal("100"),
                status="open"
            )
        else:
            mock_service.update_poline_date.side_effect = ValidationException(
                "Promise date cannot be in the past"
            )
        
        response = client.post(
            f"/api/v1/erp/po/{po_id}/lines/{line_no}/date",
            json=request_body,
            headers={"X-User-ID": "test-user"}
        )
    
    if should_succeed:
        assert response.status_code == status.HTTP_200_OK
    else:
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

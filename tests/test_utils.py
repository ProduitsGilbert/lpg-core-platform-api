"""Tests for utility functions."""

import pytest
from datetime import datetime
from app.utils import (
    validate_email,
    sanitize_phone_number,
    calculate_business_days,
    format_currency,
    parse_po_number
)


class TestEmailValidation:
    """Test email validation function."""
    
    def test_valid_email(self):
        assert validate_email("user@example.com") == True
        assert validate_email("john.doe@company.org") == True
        
    def test_invalid_email(self):
        assert validate_email("invalid.email") == False
        assert validate_email("@example.com") == False
        assert validate_email("user@") == False


class TestPhoneNumberSanitization:
    """Test phone number sanitization."""
    
    def test_sanitize_valid_phone(self):
        assert sanitize_phone_number("(555) 123-4567") == "5551234567"
        assert sanitize_phone_number("+1-800-555-1234") == "18005551234"
        
    def test_sanitize_invalid_phone(self):
        assert sanitize_phone_number("123") is None
        assert sanitize_phone_number("") is None


class TestBusinessDaysCalculation:
    """Test business days calculation."""
    
    def test_add_business_days(self):
        # Starting Monday
        start = datetime(2024, 1, 8)  # Monday
        result = calculate_business_days(start, 5)
        assert result.weekday() == 0  # Should be Monday
        assert result.day == 15
        
    def test_skip_weekend(self):
        # Starting Friday
        start = datetime(2024, 1, 5)  # Friday
        result = calculate_business_days(start, 1)
        assert result.weekday() == 0  # Should be Monday
        assert result.day == 8


class TestCurrencyFormatting:
    """Test currency formatting."""
    
    def test_format_usd(self):
        assert format_currency(1234.56) == "$1,234.56"
        assert format_currency(1000000.00) == "$1,000,000.00"
        
    def test_format_other_currencies(self):
        assert format_currency(1234.56, "EUR") == "€1,234.56"
        assert format_currency(1234.56, "GBP") == "£1,234.56"
        assert format_currency(1234.56, "CAD") == "CAD 1,234.56"


class TestPONumberParsing:
    """Test PO number parsing."""
    
    def test_valid_po_number(self):
        result = parse_po_number("PO-2024-001234")
        assert result["is_valid"] == True
        assert result["year"] == 2024
        assert result["sequence"] == 1234
        
    def test_invalid_po_number(self):
        result = parse_po_number("INVALID-PO")
        assert result["is_valid"] == False
        assert result["year"] is None
        assert result["sequence"] is None
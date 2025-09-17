"""Utility functions for the LPG Core Platform API."""

from typing import Optional, Dict, Any
import re
from datetime import datetime, timedelta


def validate_email(email: str) -> bool:
    """
    Validate email address format.
    
    Args:
        email: Email address to validate
        
    Returns:
        True if valid email format, False otherwise
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def sanitize_phone_number(phone: str) -> Optional[str]:
    """
    Sanitize and format phone number.
    
    Args:
        phone: Raw phone number string
        
    Returns:
        Formatted phone number or None if invalid
    """
    # Remove all non-digit characters
    digits = re.sub(r'\D', '', phone)
    
    # Check if it's a valid phone number length
    if len(digits) < 10 or len(digits) > 15:
        return None
        
    return digits


def calculate_business_days(start_date: datetime, days: int) -> datetime:
    """
    Calculate end date by adding business days.
    
    Args:
        start_date: Starting date
        days: Number of business days to add
        
    Returns:
        End date after adding business days
    """
    current_date = start_date
    business_days_added = 0
    
    while business_days_added < days:
        current_date += timedelta(days=1)
        # Skip weekends (Saturday=5, Sunday=6)
        if current_date.weekday() < 5:
            business_days_added += 1
            
    return current_date


def format_currency(amount: float, currency: str = "USD") -> str:
    """
    Format amount as currency string.
    
    Args:
        amount: Amount to format
        currency: Currency code (default: USD)
        
    Returns:
        Formatted currency string
    """
    if currency == "USD":
        return f"${amount:,.2f}"
    elif currency == "EUR":
        return f"€{amount:,.2f}"
    elif currency == "GBP":
        return f"£{amount:,.2f}"
    else:
        return f"{currency} {amount:,.2f}"


def parse_po_number(po_number: str) -> Dict[str, Any]:
    """
    Parse purchase order number to extract components.
    
    Args:
        po_number: Purchase order number
        
    Returns:
        Dictionary with parsed components
    """
    # Example PO format: PO-2024-001234
    pattern = r'^PO-(\d{4})-(\d{6})$'
    match = re.match(pattern, po_number)
    
    if match:
        return {
            "year": int(match.group(1)),
            "sequence": int(match.group(2)),
            "is_valid": True
        }
    
    return {
        "year": None,
        "sequence": None,  
        "is_valid": False
    }
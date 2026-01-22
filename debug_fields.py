#!/usr/bin/env python3
"""
Debug script to test field extraction logic.
"""

from decimal import Decimal

# Sample quote line data
quote_line = {
    "@odata.etag": "W/\"test\"",
    "Document_Type": "Quote",
    "Document_No": "QT047953",
    "Line_No": 10000,
    "Line_Amount": 4878.06,
    "Quantity": 2
}

# Sample order line data
order_line = {
    "DocumentNo": "GI024120",
    "LineAmount": 1601.9,
    "Quantity": 1
}

def extract_amount(line, field_names):
    """Extract amount from line using multiple possible field names."""
    for amount_field in field_names:
        if amount_field in line and line[amount_field] is not None:
            try:
                return Decimal(str(line[amount_field]))
            except (ValueError, TypeError):
                continue
    return None

# Test quote line
quote_amount = extract_amount(quote_line, ["Line_Amount", "LineAmount", "Amount"])
print(f"Quote line amount: {quote_amount}")

# Test order line
order_amount = extract_amount(order_line, ["LineAmount", "Line_Amount", "Amount"])
print(f"Order line amount: {order_amount}")

# Test with current logic order
quote_amount2 = extract_amount(quote_line, ["Line_Amount", "LineAmount", "Amount"])
order_amount2 = extract_amount(order_line, ["LineAmount", "Line_Amount", "Amount"])

print(f"Quote line amount (current logic): {quote_amount2}")
print(f"Order line amount (current logic): {order_amount2}")



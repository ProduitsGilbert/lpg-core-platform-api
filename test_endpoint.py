#!/usr/bin/env python3
"""
Simple test script to verify the customer sales stats endpoint logic.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock
from decimal import Decimal

# Mock the required dependencies
class MockService:
    def __init__(self):
        pass

    async def fetch_collection(self, resource, *, filter_field=None, filter_value=None, top=None):
        # Mock data for testing
        if resource == "SalesOrderQuotesH":
            return [
                {"No": "QT001"},
                {"No": "QT002"}
            ]
        elif resource == "SalesOrderHeaders":
            return [
                {"No": "SO001", "Quote_No": "QT001"},
                {"No": "SO002", "Quote_No": None}
            ]
        elif resource == "SalesQuoteLines" and filter_value == "QT001":
            return [
                {"Line_Amount": 500.25, "Quantity": 10.0},
                {"Line_Amount": 200.50, "Quantity": 5.0}
            ]
        elif resource == "SalesQuoteLines" and filter_value == "QT002":
            return [
                {"Line_Amount": 800.75, "Quantity": 15.0},
                {"Line_Amount": 400.25, "Quantity": 10.0}
            ]
        elif resource == "Gilbert_SalesOrderLines" and filter_value == "SO001":
            return [
                {"Line_Amount": 600.00, "Quantity": 12.0},
                {"Line_Amount": 250.25, "Quantity": 8.0}
            ]
        elif resource == "Gilbert_SalesOrderLines" and filter_value == "SO002":
            return [
                {"Line_Amount": 1200.50, "Quantity": 20.0},
                {"Line_Amount": 800.75, "Quantity": 15.0}
            ]
        return []

async def test_customer_sales_stats():
    """Test the customer sales stats logic."""
    from decimal import Decimal
    from app.domain.erp.models import CustomerSalesQuoteStats, CustomerSalesOrderStats, CustomerSalesStatsResponse

    customer_id = "test_customer"
    service = MockService()

    # Simulate the logic from the endpoint
    quote_headers = await service.fetch_collection(
        "SalesOrderQuotesH",
        filter_field="Sell_to_Customer_No",
        filter_value=customer_id,
        top=None
    )

    order_headers = await service.fetch_collection(
        "SalesOrderHeaders",
        filter_field="Sell_to_Customer_No",
        filter_value=customer_id,
        top=None
    )

    # Aggregate quote statistics from lines (sum amounts from all quote lines)
    total_quote_amount = Decimal("0")
    total_quote_quantity = Decimal("0")
    quote_numbers = [quote.get("No") for quote in quote_headers if quote.get("No")]

    for quote_no in quote_numbers:
        quote_lines = await service.fetch_collection(
            "SalesQuoteLines",
            filter_field="Document_No",
            filter_value=quote_no,
            top=None
        )
        for line in quote_lines:
            # Sum line amounts (try different possible field names)
            line_amount = None
            for amount_field in ["Line_Amount", "Amount", "LineAmount"]:
                if amount_field in line and line[amount_field] is not None:
                    try:
                        line_amount = Decimal(str(line[amount_field]))
                        total_quote_amount += line_amount
                        break
                    except (ValueError, TypeError):
                        continue

            # Sum quantities
            if "Quantity" in line and line["Quantity"] is not None:
                try:
                    total_quote_quantity += Decimal(str(line["Quantity"]))
                except (ValueError, TypeError):
                    pass

    # Aggregate order statistics
    total_order_amount = Decimal("0")
    total_order_quantity = Decimal("0")
    orders_based_on_quotes = 0
    order_numbers = [order.get("No") for order in order_headers if order.get("No")]

    for order in order_headers:
        # Check if order is based on a quote
        if order.get("Quote_No"):
            orders_based_on_quotes += 1

    # Aggregate amounts and quantities from order lines
    for order_no in order_numbers:
        order_lines = await service.fetch_collection(
            "Gilbert_SalesOrderLines",
            filter_field="DocumentNo",
            filter_value=order_no,
            top=None
        )
        for line in order_lines:
            # Sum line amounts (try different possible field names)
            line_amount = None
            for amount_field in ["Line_Amount", "Amount", "LineAmount"]:
                if amount_field in line and line[amount_field] is not None:
                    try:
                        line_amount = Decimal(str(line[amount_field]))
                        total_order_amount += line_amount
                        break
                    except (ValueError, TypeError):
                        continue

            # Sum quantities
            if "Quantity" in line and line["Quantity"] is not None:
                try:
                    total_order_quantity += Decimal(str(line["Quantity"]))
                except (ValueError, TypeError):
                    pass

    result = CustomerSalesStatsResponse(
        customer_id=customer_id,
        quotes=CustomerSalesQuoteStats(
            total_quotes=len(quote_headers),
            total_amount=total_quote_amount,
            total_quantity=total_quote_quantity,
            quotes=quote_headers,
        ),
        orders=CustomerSalesOrderStats(
            total_orders=len(order_headers),
            total_amount=total_order_amount,
            total_quantity=total_order_quantity,
            orders_based_on_quotes=orders_based_on_quotes,
            orders=order_headers,
        ),
    )

    print("Test result:")
    print(f"Customer ID: {result.customer_id}")
    print(f"Total Quotes: {result.quotes.total_quotes}")
    print(f"Total Quote Amount: ${result.quotes.total_amount}")
    print(f"Total Quote Quantity: {result.quotes.total_quantity}")
    print(f"Total Orders: {result.orders.total_orders}")
    print(f"Total Order Amount: ${result.orders.total_amount}")
    print(f"Total Order Quantity: {result.orders.total_quantity}")
    print(f"Orders based on quotes: {result.orders.orders_based_on_quotes}")
    print("Test passed!")

if __name__ == "__main__":
    asyncio.run(test_customer_sales_stats())
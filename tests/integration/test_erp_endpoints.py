import os

import pytest


ITEM_ID = os.environ.get("TEST_ITEM_ID", "1510136")
PURCHASE_ORDER_ID = os.environ.get("TEST_PURCHASE_ORDER_ID", "PO030214")
VENDOR_ID = os.environ.get("TEST_VENDOR_ID", "MOTCA01")
SALES_ORDER_ID = os.environ.get("TEST_SALES_ORDER_ID", "GI021698")
SALES_QUOTE_ID = os.environ.get("TEST_SALES_QUOTE_ID", "QT030235")
CUSTOMER_ID = os.environ.get("TEST_CUSTOMER_ID", "CUST001")

REQUIRED_ERP_VARS = ("ERP_BASE_URL", "BC_API_USERNAME", "BC_API_PASSWORD")


def _require_erp_env() -> None:
    missing = [name for name in REQUIRED_ERP_VARS if not os.getenv(name)]
    if missing:
        pytest.skip(f"Missing ERP configuration environment variables: {', '.join(missing)}")


def _erp_url(base_url: str, path: str) -> str:
    return f"{base_url}/api/v1/erp{path}"


def test_get_item_detail(http_session, base_url, default_timeout) -> None:
    _require_erp_env()

    response = http_session.get(
        _erp_url(base_url, f"/items/{ITEM_ID}"),
        timeout=default_timeout,
    )
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["id"] == ITEM_ID
    assert data["description"]


def test_get_item_prices(http_session, base_url, default_timeout) -> None:
    _require_erp_env()

    response = http_session.get(
        _erp_url(base_url, f"/items/{ITEM_ID}/prices"),
        timeout=default_timeout,
    )
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["item_id"] == ITEM_ID
    for key in ("cad_price", "usd_price", "eur_price"):
        assert data[key] is not None
    assert data["cad_price"] > 0
    assert data["usd_price"] > 0
    assert data["eur_price"] > 0


def test_list_items_filtered(http_session, base_url, default_timeout) -> None:
    _require_erp_env()

    response = http_session.get(
        _erp_url(base_url, "/bc/items"),
        params={"no": ITEM_ID},
        timeout=default_timeout,
    )
    assert response.status_code == 200, response.text
    items = response.json()
    assert items, "Expected at least one item"
    assert any(str(item.get("No")) == ITEM_ID for item in items)


def test_get_purchase_order(http_session, base_url, default_timeout) -> None:
    _require_erp_env()

    response = http_session.get(
        _erp_url(base_url, f"/po/{PURCHASE_ORDER_ID}"),
        timeout=default_timeout,
    )
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["id"] == PURCHASE_ORDER_ID
    assert data["vendor_id"]


def test_get_purchase_order_lines(http_session, base_url, default_timeout) -> None:
    _require_erp_env()

    response = http_session.get(
        _erp_url(base_url, f"/po/{PURCHASE_ORDER_ID}/lines"),
        timeout=default_timeout,
    )
    assert response.status_code == 200, response.text
    lines = response.json()["data"]
    assert lines, "Expected at least one purchase order line"


def test_list_bc_purchase_order_headers(http_session, base_url, default_timeout) -> None:
    _require_erp_env()

    response = http_session.get(
        _erp_url(base_url, "/bc/purchase-order-headers"),
        params={"no": PURCHASE_ORDER_ID},
        timeout=default_timeout,
    )
    assert response.status_code == 200, response.text
    headers = response.json()
    assert headers, "Expected at least one purchase order header"
    assert any(str(header.get("No")) == PURCHASE_ORDER_ID for header in headers)


def test_list_bc_purchase_order_lines(http_session, base_url, default_timeout) -> None:
    _require_erp_env()

    response = http_session.get(
        _erp_url(base_url, "/bc/purchase-order-lines"),
        params={"document_no": PURCHASE_ORDER_ID},
        timeout=default_timeout,
    )
    assert response.status_code == 200, response.text
    lines = response.json()
    assert lines, "Expected at least one purchase order line record"


def test_list_bc_vendors(http_session, base_url, default_timeout) -> None:
    _require_erp_env()

    response = http_session.get(
        _erp_url(base_url, "/bc/vendors"),
        params={"no": VENDOR_ID},
        timeout=default_timeout,
    )
    assert response.status_code == 200, response.text
    vendors = response.json()
    assert vendors, "Expected at least one vendor record"
    assert any(str(vendor.get("No")) == VENDOR_ID for vendor in vendors)


def test_list_bc_customers_with_geocode(http_session, base_url, default_timeout) -> None:
    _require_erp_env()

    response = http_session.get(
        _erp_url(base_url, "/bc/customers"),
        params={"top": 1},
        timeout=default_timeout,
    )
    assert response.status_code == 200, response.text
    customers = response.json()
    assert customers, "Expected at least one customer record"
    customer = customers[0]
    for field in (
        "address_1",
        "address_2",
        "address_3",
        "address_4",
        "postal_code",
        "city",
        "country",
        "geocode",
    ):
        assert field in customer


def test_list_bc_sales_order_headers(http_session, base_url, default_timeout) -> None:
    _require_erp_env()

    response = http_session.get(
        _erp_url(base_url, "/bc/sales-order-headers"),
        params={"no": SALES_ORDER_ID},
        timeout=default_timeout,
    )
    assert response.status_code == 200, response.text
    orders = response.json()
    assert orders, "Expected at least one sales order header"
    assert any(str(order.get("No")) == SALES_ORDER_ID for order in orders)


def test_list_bc_sales_order_lines(http_session, base_url, default_timeout) -> None:
    _require_erp_env()

    response = http_session.get(
        _erp_url(base_url, "/bc/sales-order-lines"),
        params={"document_no": SALES_ORDER_ID},
        timeout=default_timeout,
    )
    assert response.status_code == 200, response.text
    lines = response.json()
    assert lines, "Expected at least one sales order line record"


def test_list_bc_sales_quote_headers(http_session, base_url, default_timeout) -> None:
    _require_erp_env()

    response = http_session.get(
        _erp_url(base_url, "/bc/sales-quote-headers"),
        params={"no": SALES_QUOTE_ID},
        timeout=default_timeout,
    )
    assert response.status_code == 200, response.text
    quotes = response.json()
    assert quotes, "Expected at least one sales quote header"
    assert any(str(quote.get("No")) == SALES_QUOTE_ID for quote in quotes)


def test_list_bc_sales_quote_lines(http_session, base_url, default_timeout) -> None:
    _require_erp_env()

    response = http_session.get(
        _erp_url(base_url, "/bc/sales-quote-lines"),
        params={"document_no": SALES_QUOTE_ID},
        timeout=default_timeout,
    )
    assert response.status_code == 200, response.text
    lines = response.json()
    assert lines, "Expected at least one sales quote line record"


def test_get_customer_sales_stats(http_session, base_url, default_timeout) -> None:
    _require_erp_env()

    response = http_session.get(
        _erp_url(base_url, "/bc/customer-sales-stats"),
        params={"customer_id": CUSTOMER_ID},
        timeout=default_timeout,
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["customer_id"] == CUSTOMER_ID
    assert "quotes" in data
    assert "orders" in data
    assert "total_quotes" in data["quotes"]
    assert "total_orders" in data["orders"]
    assert "orders_based_on_quotes" in data["orders"]

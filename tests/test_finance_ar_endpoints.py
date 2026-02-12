import os
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import app


def _client():
    os.environ.setdefault("FINANCE_API_TOKEN", "finance-secret")
    return TestClient(app)


def test_list_open_ar_invoices_empty():
    client = _client()
    stub = MagicMock()
    stub.list_open_invoices = AsyncMock(return_value=[])

    with patch("app.api.v1.finance.router.get_ar_service", return_value=stub):
        response = client.get(
            "/api/v1/finance/accounts-receivable/invoices?due_from=2024-01-01&due_to=2024-01-31&use_cache=false",
            headers={"X-Finance-Token": "finance-secret"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["meta"]["pagination"]["total_items"] == 0
    assert payload["data"] == []
    stub.list_open_invoices.assert_awaited_once()


def test_list_ar_invoice_lines():
    client = _client()
    invoice_no = os.getenv("AR_TEST_INVOICE_NO")
    if not invoice_no:
        pytest.skip("AR_TEST_INVOICE_NO not set")
    stub = MagicMock()
    stub.get_invoice_lines = AsyncMock(return_value=[])

    with patch("app.api.v1.finance.router.get_ar_service", return_value=stub):
        response = client.get(
            f"/api/v1/finance/accounts-receivable/invoices/{invoice_no}/lines",
            headers={"X-Finance-Token": "finance-secret"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["meta"]["pagination"]["total_items"] == 0
    assert payload["data"] == []
    stub.get_invoice_lines.assert_awaited_once_with(invoice_no)


def test_list_ar_collections_empty():
    client = _client()
    stub = MagicMock()
    stub.list_priority_collections = AsyncMock(return_value=[])

    with patch("app.api.v1.finance.router.get_ar_service", return_value=stub):
        response = client.get(
            "/api/v1/finance/accounts-receivable/collections?use_cache=false",
            headers={"X-Finance-Token": "finance-secret"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["meta"]["pagination"]["total_items"] == 0
    assert payload["data"] == []
    stub.list_priority_collections.assert_awaited_once()

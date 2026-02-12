from datetime import date

import pytest

from app.adapters.erp_client import ERPClient


@pytest.mark.asyncio
async def test_get_job_default_dimensions_encodes_special_chars(monkeypatch):
    client = ERPClient()
    captured = {}

    async def _fake_fetch(resource_path: str, *, fail_on_404: bool = False):
        _ = fail_on_404
        captured["resource"] = resource_path
        return []

    monkeypatch.setattr(client, "_fetch_odata_collection", _fake_fetch)

    await client.get_job_default_dimensions("INVMG60#01")

    resource = captured["resource"]
    assert resource.startswith("DefaultDimensions?%24filter=")
    assert "%23" in resource


@pytest.mark.asyncio
async def test_get_job_encodes_special_chars(monkeypatch):
    client = ERPClient()
    captured = {}

    async def _fake_fetch(resource_path: str, *, fail_on_404: bool = False):
        _ = fail_on_404
        captured["resource"] = resource_path
        return []

    monkeypatch.setattr(client, "_fetch_odata_collection", _fake_fetch)

    await client.get_job("INVMG60#01")

    resource = captured["resource"]
    assert resource.startswith("Jobs?%24filter=")
    assert "%23" in resource


@pytest.mark.asyncio
async def test_get_open_ar_uses_customer_ledger_entries_resource(monkeypatch):
    client = ERPClient()
    captured = {}

    async def _fake_fetch(resource_path: str, *, fail_on_404: bool = False):
        _ = fail_on_404
        captured["resource"] = resource_path
        return []

    monkeypatch.setattr(client, "_fetch_odata_collection", _fake_fetch)

    await client.get_open_posted_sales_invoices(
        due_from=date(2026, 1, 1),
        due_to=date(2026, 1, 31),
        customer_no="CUST-100",
        invoice_no="DOC-100",
        top=50,
    )

    resource = captured["resource"]
    assert resource.startswith("CustomerLedgerEntries?$select=")
    assert "Remaining_Amount" in resource
    assert "Remaining_AMT" in resource
    assert "Open eq true" in resource
    assert "Customer_No eq 'CUST-100'" in resource
    assert "Document_No eq 'DOC-100'" in resource

from decimal import Decimal

import pytest

from app.domain.kpi.payables_invoice_stats_service import PayablesInvoiceStatsService


class _StubERP:
    async def get_continia_invoices(self):
        return [
            {"No": "C-1", "Status": "Open", "Status_Code": "ATTENDS"},
            {"No": "C-2", "Status": "Open", "Status_Code": "UNMATCHED", "Amount_Including_VAT": 50},
            {"No": "C-3", "Status": "Closed", "Status_Code": "ATTENDS", "Amount": 25.5},
        ]

    async def get_open_purchase_invoices(self, select_fields=None):
        _ = select_fields
        return [
            {"No": "PI-1", "Amount_Including_VAT": 100},
            {"No": "PI-2", "Amount": 10.5},
        ]

    async def get_posted_purchase_invoices(
        self,
        start_date=None,
        end_date=None,
        include_paid=False,
        select_fields=None,
    ):
        _ = (start_date, end_date, select_fields)
        assert include_paid is True
        return [
            {"No": "PP-1", "Remaining_Amount": 0, "Amount_Including_VAT": 200},
            {"No": "PP-2", "Remaining_Amount": 10},
        ]


class _Values:
    def __init__(self, amount: Decimal) -> None:
        self.decimal_values = {"AMOUNTINCLVAT": amount}


class _StubContiniaRepo:
    is_configured = True

    def get_document_values_batch(self, document_nos):
        _ = document_nos
        return {
            "C-1": _Values(Decimal("125.00")),
        }


class _UnconfiguredContiniaRepo:
    is_configured = False


class _NoCache:
    is_configured = False


class _LatestCache:
    is_configured = True

    def __init__(self):
        self._latest = {
            "continia": {"invoice_count": 9, "total_amount": 999.0},
            "purchase_invoice": {"invoice_count": 8, "total_amount": 888.0},
            "posted_purchase_order": {"invoice_count": 7, "total_amount": 777.0},
            "continia_statuses": [{"status": "Cached", "invoice_count": 9, "total_amount": 999.0}],
        }

    def get_latest_snapshot(self):
        return self._latest

    def get_snapshot(self, snapshot_date: str):
        _ = snapshot_date
        return None

    def upsert_snapshot(self, snapshot_date: str, payload):
        _ = (snapshot_date, payload)
        return None

    def prune_before(self, snapshot_date: str):
        _ = snapshot_date
        return None


@pytest.mark.asyncio
async def test_payables_invoice_stats_aggregates_sections_and_statuses(monkeypatch) -> None:
    monkeypatch.setattr("app.domain.kpi.payables_invoice_stats_service.payables_invoice_stats_cache", _NoCache())
    service = PayablesInvoiceStatsService(client=_StubERP(), continia_repository=_StubContiniaRepo())

    stats = await service.get_stats()

    assert stats.continia.invoice_count == 2
    assert stats.continia.total_amount == 175.0

    assert stats.purchase_invoice.invoice_count == 2
    assert stats.purchase_invoice.total_amount == 110.5

    assert stats.posted_purchase_order.invoice_count == 2
    assert stats.posted_purchase_order.total_amount == 210.0

    assert [item.status for item in stats.continia_statuses] == ["ATTENDS", "UNMATCHED"]
    assert [item.invoice_count for item in stats.continia_statuses] == [1, 1]
    assert [item.total_amount for item in stats.continia_statuses] == [125.0, 50.0]


@pytest.mark.asyncio
async def test_payables_invoice_stats_without_continia_sql_amounts(monkeypatch) -> None:
    monkeypatch.setattr("app.domain.kpi.payables_invoice_stats_service.payables_invoice_stats_cache", _NoCache())
    service = PayablesInvoiceStatsService(
        client=_StubERP(),
        continia_repository=_UnconfiguredContiniaRepo(),
    )

    stats = await service.get_stats()

    assert stats.continia.invoice_count == 2
    assert stats.continia.total_amount == 50.0


@pytest.mark.asyncio
async def test_payables_invoice_stats_uses_latest_cache_when_available(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.domain.kpi.payables_invoice_stats_service.payables_invoice_stats_cache",
        _LatestCache(),
    )
    service = PayablesInvoiceStatsService(client=_StubERP(), continia_repository=_StubContiniaRepo())

    stats = await service.get_stats()

    assert stats.continia.invoice_count == 9
    assert stats.continia.total_amount == 999.0
    assert stats.continia_statuses[0].status == "Cached"

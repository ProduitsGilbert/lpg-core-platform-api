import datetime as dt

import pytest

from app.domain.kpi.sales_stats_service import SalesStatsService


class _NoCache:
    is_configured = False


class _HistoryCache:
    is_configured = True

    def __init__(self):
        self._snapshots = [
            {
                "snapshot_date": "2026-02-08",
                "new_orders_count": 1,
                "last_week_orders_amount": 100.0,
                "new_quotes_count": 1,
                "last_week_quotes_amount": 20.0,
                "total_quotes_count": 2,
                "total_quotes_amount": 35.0,
                "pending_quotes_amount": 20.0,
                "biggest_customer_last_month": None,
            }
        ]

    def list_snapshots(self, start_date: str, end_date: str):
        _ = (start_date, end_date)
        return self._snapshots

    def get_snapshot(self, snapshot_date: str):
        _ = snapshot_date
        return None

    def upsert_snapshot(self, snapshot_date: str, payload):
        _ = (snapshot_date, payload)
        return None

    def prune_before(self, snapshot_date: str):
        _ = snapshot_date
        return None


class _StubERP:
    async def get_sales_order_headers(self):
        return [
            {
                "No": "SO-1",
                "Order_Date": "2026-02-09",
                "Amount": 100,
                "Sell_to_Customer_No": "C1",
                "Sell_to_Customer_Name": "Alpha",
            },
            {
                "No": "SO-2",
                "Document_Date": "2026-02-04",
                "Amount_Including_VAT": 200,
                "Sell_to_Customer_No": "C2",
                "Sell_to_Customer_Name": "Beta",
            },
            {
                "No": "SO-3",
                "Document_Date": "2026-01-15",
                "Amount": 300,
                "Sell_to_Customer_No": "C1",
                "Sell_to_Customer_Name": "Alpha",
            },
            {
                "No": "SO-4",
                "Document_Date": "2026-01-20",
                "Amount": 250,
                "Sell_to_Customer_No": "C2",
                "Sell_to_Customer_Name": "Beta",
            },
            {
                "No": "SO-5",
                "Document_Date": "2026-01-11",
                "Amount": 100,
                "Sell_to_Customer_No": "C2",
                "Sell_to_Customer_Name": "Beta",
            },
        ]

    async def get_sales_quote_headers(self):
        return [
            {"No": "SQ-1", "Document_Date": "2026-02-09", "Status": "Open", "Amount": 500},
            {"No": "SQ-2", "Document_Date": "2026-02-06", "Status": "Closed", "Amount": 700},
            {"No": "SQ-3", "Document_Date": "2026-01-31", "Amount_Including_VAT": 50},
        ]


class _StubERPWithLineAmounts:
    async def get_sales_order_headers(self):
        return [
            {
                "No": "SO-L1",
                "Order_Date": "2026-02-09",
                "Sell_to_Customer_No": "CL1",
                "Sell_to_Customer_Name": "Line Customer",
            }
        ]

    async def get_sales_quote_headers(self):
        return [
            {"No": "SQ-L1", "Status": "Open"},
        ]

    async def get_sales_order_lines(self):
        return [
            {"DocumentNo": "SO-L1", "LineAmount": 123.45},
        ]

    async def get_sales_quote_lines(self):
        return [
            {"Document_No": "SQ-L1", "Line_Amount": 67.89},
        ]


@pytest.mark.asyncio
async def test_sales_stats_service_snapshot_calculation(monkeypatch):
    monkeypatch.setattr("app.domain.kpi.sales_stats_service.sales_stats_cache", _NoCache())
    service = SalesStatsService(client=_StubERP())

    snapshot = await service.get_snapshot(snapshot_date=dt.date(2026, 2, 9), refresh=True)

    assert snapshot.snapshot_date == "2026-02-09"
    assert snapshot.new_orders_count == 1
    assert snapshot.last_week_orders_amount == 300.0
    assert snapshot.new_quotes_count == 1
    assert snapshot.last_week_quotes_amount == 1200.0
    assert snapshot.total_quotes_count == 3
    assert snapshot.total_quotes_amount == 1250.0
    assert snapshot.pending_quotes_amount == 550.0
    assert snapshot.biggest_customer_last_month is not None
    assert snapshot.biggest_customer_last_month.customer_no == "C2"
    assert snapshot.biggest_customer_last_month.order_amount == 350.0


@pytest.mark.asyncio
async def test_sales_stats_history_ensures_end_snapshot(monkeypatch):
    monkeypatch.setattr("app.domain.kpi.sales_stats_service.sales_stats_cache", _HistoryCache())
    service = SalesStatsService(client=_StubERP())

    history = await service.get_history(end_date=dt.date(2026, 2, 9), days=2, ensure_end_snapshot=True)

    assert history.start_date == "2026-02-08"
    assert history.end_date == "2026-02-09"
    assert len(history.points) == 2
    assert [p.snapshot_date for p in history.points] == ["2026-02-08", "2026-02-09"]


@pytest.mark.asyncio
async def test_sales_stats_uses_line_amounts_when_header_amount_missing(monkeypatch):
    monkeypatch.setattr("app.domain.kpi.sales_stats_service.sales_stats_cache", _NoCache())
    service = SalesStatsService(client=_StubERPWithLineAmounts())

    snapshot = await service.get_snapshot(snapshot_date=dt.date(2026, 2, 9), refresh=True)

    assert snapshot.last_week_orders_amount == 123.45
    assert snapshot.new_quotes_count == 0
    assert snapshot.last_week_quotes_amount == 0.0
    assert snapshot.total_quotes_amount == 67.89
    assert snapshot.pending_quotes_amount == 67.89
    assert snapshot.biggest_customer_last_month is None

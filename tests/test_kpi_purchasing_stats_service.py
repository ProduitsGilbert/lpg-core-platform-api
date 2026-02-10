import datetime as dt

import pytest

from app.domain.kpi.purchasing_stats_service import PurchasingStatsService


class _StubERP:
    async def get_purchase_order_headers(self, *, select_fields=None):
        _ = select_fields
        return [
            {"No": "PO-100", "Order_Date": "2026-02-10", "Amount_Including_VAT": 100},
            {"No": "PO-101", "Document_Date": "2026-02-10", "AmountIncludingVAT": 50.5},
            {"No": "PO-102", "SystemCreatedAt": "2026-02-08T11:00:00Z", "Amount": 20},
            {"No": "PO-099", "Order_Date": "2026-01-28", "Amount": 99},
        ]


class _StubCeduleRepo:
    is_configured = True

    def list_action_counts_by_category(self, *, start_date: dt.date, end_date: dt.date):
        assert start_date == dt.date(2026, 2, 4)
        assert end_date == dt.date(2026, 2, 10)
        return [("PRICE_CHANGE", 5), ("DATE_CHANGE", 2)]


class _StubUnconfiguredCeduleRepo:
    is_configured = False

    def list_action_counts_by_category(self, *, start_date: dt.date, end_date: dt.date):
        _ = (start_date, end_date)
        return []


@pytest.mark.asyncio
async def test_purchasing_stats_aggregates_po_timeline_and_action_categories() -> None:
    service = PurchasingStatsService(client=_StubERP(), cedule_repository=_StubCeduleRepo())

    stats = await service.get_stats(
        end_date=dt.date(2026, 2, 10),
        days=7,
        period="day",
    )

    assert stats.start_date == "2026-02-04"
    assert stats.end_date == "2026-02-10"
    assert stats.total_pos == 3
    assert stats.total_amount == 170.5
    assert len(stats.po_timeline) == 2
    assert stats.po_timeline[0].period_start == "2026-02-08"
    assert stats.po_timeline[0].po_count == 1
    assert stats.po_timeline[0].total_amount == 20.0
    assert stats.po_timeline[1].period_start == "2026-02-10"
    assert stats.po_timeline[1].po_count == 2
    assert stats.po_timeline[1].total_amount == 150.5
    assert [item.action_category for item in stats.action_categories] == ["PRICE_CHANGE", "DATE_CHANGE"]
    assert stats.total_action_updates == 7


@pytest.mark.asyncio
async def test_purchasing_stats_handles_missing_cedule_config() -> None:
    service = PurchasingStatsService(
        client=_StubERP(),
        cedule_repository=_StubUnconfiguredCeduleRepo(),
    )

    stats = await service.get_stats(
        end_date=dt.date(2026, 2, 10),
        days=7,
        period="week",
    )

    assert stats.total_pos == 3
    assert stats.total_amount == 170.5
    assert len(stats.po_timeline) == 2
    assert stats.action_categories == []
    assert stats.total_action_updates == 0

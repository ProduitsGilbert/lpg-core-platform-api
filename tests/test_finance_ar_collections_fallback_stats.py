from datetime import date, timedelta
from decimal import Decimal

from app.domain.finance.accounts_receivable_service import AccountsReceivableService
from app.domain.finance.models import AccountsReceivableInvoice, AccountsReceivablePaymentStats


class _DummyERPClient:
    async def get_open_posted_sales_invoices(self, **kwargs):
        return []

    async def get_posted_sales_invoice_lines(self, invoice_no: str):
        return []


class _StatsRepoEmpty:
    def get_stats_by_customer_nos(self, customer_nos):
        return {}


class _StatsRepoPartial:
    def __init__(self, stats):
        self._stats = stats

    def get_stats_by_customer_nos(self, customer_nos):
        return {k: v for k, v in self._stats.items() if k in customer_nos}


def _invoice(customer_no: str, due_date: date) -> AccountsReceivableInvoice:
    return AccountsReceivableInvoice(
        invoice_no=f"INV-{customer_no}-{due_date.isoformat()}",
        customer_no=customer_no,
        customer_name=customer_no,
        due_date=due_date,
        posting_date=due_date,
        total_amount=Decimal("100.00"),
        remaining_amount=Decimal("100.00"),
        closed=False,
        cancelled=False,
    )


def test_collections_fallback_stats_when_repo_is_empty():
    svc = AccountsReceivableService(
        erp_client=_DummyERPClient(),
        stats_repo=_StatsRepoEmpty(),
        cache_repo=None,
    )
    today = date.today()
    invoices = [
        _invoice("CUST-A", today - timedelta(days=10)),
        _invoice("CUST-A", today + timedelta(days=5)),
        _invoice("CUST-B", today - timedelta(days=4)),
    ]

    items = svc.list_priority_collections_from_invoices(invoices)

    by_customer = {item.invoice.customer_no: item.payment_stats for item in items}

    stats_a = by_customer["CUST-A"]
    assert stats_a is not None
    assert stats_a.avg_days_late == 5.0
    assert stats_a.late_ratio == 0.5
    assert stats_a.invoice_count == 2

    stats_b = by_customer["CUST-B"]
    assert stats_b is not None
    assert stats_b.avg_days_late == 4.0
    assert stats_b.late_ratio == 1.0
    assert stats_b.invoice_count == 1


def test_collections_keeps_existing_repo_stats_and_fills_missing_customers():
    repo_stats = {
        "CUST-A": AccountsReceivablePaymentStats(
            customer_no="CUST-A",
            invoice_count=9,
            avg_days_late=12.5,
            median_days_late=8.0,
            late_ratio=0.75,
        )
    }
    svc = AccountsReceivableService(
        erp_client=_DummyERPClient(),
        stats_repo=_StatsRepoPartial(repo_stats),
        cache_repo=None,
    )
    today = date.today()
    invoices = [
        _invoice("CUST-A", today - timedelta(days=10)),
        _invoice("CUST-B", today - timedelta(days=3)),
    ]

    items = svc.list_priority_collections_from_invoices(invoices)
    by_customer = {item.invoice.customer_no: item.payment_stats for item in items}

    assert by_customer["CUST-A"] is not None
    assert by_customer["CUST-A"].avg_days_late == 12.5
    assert by_customer["CUST-A"].late_ratio == 0.75

    assert by_customer["CUST-B"] is not None
    assert by_customer["CUST-B"].avg_days_late == 3.0
    assert by_customer["CUST-B"].late_ratio == 1.0

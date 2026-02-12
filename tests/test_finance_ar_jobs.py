from datetime import date, datetime
from unittest.mock import patch

from app.domain.finance.ar_jobs import refresh_ar_payment_stats
from app.domain.finance.models import AccountsReceivablePaymentStats


class _RepoStub:
    def __init__(self):
        self.saved = None
        self.is_configured = True

    def upsert_stats(self, stats):
        self.saved = list(stats)


class _ERPStub:
    def __init__(self):
        self.called_due_from = None
        self.called_top = None

    async def get_closed_posted_sales_invoices(self, due_from=None, due_to=None, top=None):
        self.called_due_from = due_from
        self.called_top = top
        return [
            {
                "Sell_to_Customer_No": "CUST-A",
                "Due_Date": "2025-01-01",
                "Date_Time_Stamped": "2025-01-06T00:00:00Z",
            },
            {
                "Sell_to_Customer_No": "CUST-A",
                "Due_Date": "2025-01-10",
                "Date_Time_Stamped": "2025-01-10T00:00:00Z",
            },
        ]


async def _run_refresh_with_stubs(repo, erp):
    with patch("app.domain.finance.ar_jobs.ArPaymentStatsRepository", return_value=repo), patch(
        "app.domain.finance.ar_jobs.ERPClient", return_value=erp
    ), patch("app.domain.finance.ar_jobs.settings.ar_payment_stats_lookback_days", 365), patch(
        "app.domain.finance.ar_jobs.settings.ar_payment_stats_max_invoices", 1234
    ):
        await refresh_ar_payment_stats()


def test_refresh_ar_payment_stats_uses_lookback_and_persists_stats():
    import asyncio

    repo = _RepoStub()
    erp = _ERPStub()

    asyncio.run(_run_refresh_with_stubs(repo, erp))

    assert erp.called_due_from is not None
    assert isinstance(erp.called_due_from, date)
    assert (date.today() - erp.called_due_from).days == 365
    assert erp.called_top == 1234

    assert repo.saved is not None
    assert len(repo.saved) == 1
    stat = repo.saved[0]
    assert isinstance(stat, AccountsReceivablePaymentStats)
    assert stat.customer_no == "CUST-A"
    assert stat.invoice_count == 2
    assert stat.avg_days_late == 2.5
    assert stat.late_ratio == 0.5
    assert isinstance(stat.updated_at, datetime)

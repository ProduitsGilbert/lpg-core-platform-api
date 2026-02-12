import asyncio
from datetime import datetime
from decimal import Decimal

from app.domain.finance.accounts_receivable_service import AccountsReceivableService


class _LedgerERPStub:
    def __init__(self, records):
        self._records = records

    async def get_open_posted_sales_invoices(self, **kwargs):
        _ = kwargs
        return list(self._records)

    async def get_posted_sales_invoice_lines(self, invoice_no: str):
        _ = invoice_no
        return []


class _StatsRepoEmpty:
    def get_stats_by_customer_nos(self, customer_nos):
        _ = customer_nos
        return {}


class _CacheRepoStub:
    def __init__(self, existing_payload):
        self.is_configured = True
        self._cache = (datetime.utcnow(), list(existing_payload))
        self.saved_payload = None

    def get_cache(self, cache_key):
        _ = cache_key
        return self._cache

    def upsert_cache(self, cache_key, payload):
        _ = cache_key
        self.saved_payload = list(payload)
        updated_at = datetime.utcnow()
        self._cache = (updated_at, list(payload))
        return updated_at


def test_list_open_invoices_maps_customer_ledger_fields():
    erp = _LedgerERPStub(
        [
            {
                "Entry_No": 10,
                "Document_No": "DOC-100",
                "Document_Type": "Payment",
                "Customer_No": "CUST-100",
                "Customer_Name": "Customer A",
                "Due_Date": "2026-01-15",
                "Posting_Date": "2026-01-05",
                "Description": "Unapplied payment",
                "Division": "CONSTR",
                "Region_Code": "QC",
                "Remaining_Amount": "120.50",
                "Remaining_AMT": "173.25",
                "Currency_Code": "USD",
                "Open": True,
            }
        ]
    )
    svc = AccountsReceivableService(erp_client=erp, stats_repo=_StatsRepoEmpty(), cache_repo=None)

    invoices = asyncio.run(svc.list_open_invoices())

    assert len(invoices) == 1
    invoice = invoices[0]
    assert invoice.invoice_no == "DOC-100"
    assert invoice.document_no == "DOC-100"
    assert invoice.entry_no == 10
    assert invoice.document_type == "Payment"
    assert invoice.customer_no == "CUST-100"
    assert invoice.customer_name == "Customer A"
    assert invoice.description == "Unapplied payment"
    assert invoice.division == "CONSTR"
    assert invoice.region_code == "QC"
    assert invoice.remaining_amount == Decimal("120.50")
    assert invoice.remaining_amt == Decimal("173.25")
    assert invoice.closed is False


def test_refresh_open_invoices_cache_keeps_distinct_entries_with_same_document_no():
    erp = _LedgerERPStub(
        [
            {
                "Entry_No": 2,
                "Document_No": "DOC-100",
                "Document_Type": "Payment",
                "Customer_No": "CUST-100",
                "Customer_Name": "Customer A",
                "Remaining_Amount": "50.00",
                "Remaining_AMT": "50.00",
                "Open": True,
            }
        ]
    )
    cache_repo = _CacheRepoStub(
        [
            {
                "entry_no": 1,
                "invoice_no": "DOC-100",
                "document_no": "DOC-100",
                "document_type": "Invoice",
                "customer_no": "CUST-100",
                "remaining_amount": "100.00",
                "remaining_amt": "100.00",
            }
        ]
    )
    svc = AccountsReceivableService(
        erp_client=erp,
        stats_repo=_StatsRepoEmpty(),
        cache_repo=cache_repo,
    )

    status = asyncio.run(svc.refresh_open_invoices_cache("open_invoices", replace=False))

    assert status.invoice_count == 2
    assert cache_repo.saved_payload is not None
    assert {item["entry_no"] for item in cache_repo.saved_payload} == {1, 2}

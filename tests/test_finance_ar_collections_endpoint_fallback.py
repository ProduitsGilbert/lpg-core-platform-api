import os

from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from app.api.v1.finance.router import (
    router as finance_router,
    get_ar_service,
    verify_finance_token,
)
from app.domain.finance.accounts_receivable_service import AccountsReceivableService


class _DummyERPClient:
    async def get_open_posted_sales_invoices(self, **kwargs):
        return [
            {
                "No": "INV-1",
                "Sell_to_Customer_No": "CUST-A",
                "Sell_to_Customer_Name": "Customer A",
                "Due_Date": "2024-01-01",
                "Posting_Date": "2023-12-01",
                "Amount": "100.00",
                "Remaining_Amount": "100.00",
                "Closed": False,
                "Cancelled": False,
            },
            {
                "No": "INV-2",
                "Sell_to_Customer_No": "CUST-A",
                "Sell_to_Customer_Name": "Customer A",
                "Due_Date": "2099-01-01",
                "Posting_Date": "2024-12-01",
                "Amount": "100.00",
                "Remaining_Amount": "100.00",
                "Closed": False,
                "Cancelled": False,
            },
        ]

    async def get_posted_sales_invoice_lines(self, invoice_no: str):
        return []


class _StatsRepoEmpty:
    def get_stats_by_customer_nos(self, customer_nos):
        return {}


def test_collections_endpoint_populates_fallback_delay_fields():
    svc = AccountsReceivableService(
        erp_client=_DummyERPClient(),
        stats_repo=_StatsRepoEmpty(),
        cache_repo=None,
    )

    app = FastAPI()
    v1 = APIRouter(prefix="/api/v1")
    v1.include_router(finance_router)
    app.include_router(v1)
    app.dependency_overrides[get_ar_service] = lambda: svc
    app.dependency_overrides[verify_finance_token] = lambda: "test-token"

    client = TestClient(app)
    response = client.get(
        "/api/v1/finance/accounts-receivable/collections?use_cache=false",
        headers={"X-Finance-Token": os.getenv("FINANCE_API_TOKEN", "finance-secret")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]

    stats = payload["data"][0]["payment_stats"]
    assert stats is not None
    assert stats["avg_days_late"] is not None
    assert stats["late_ratio"] is not None

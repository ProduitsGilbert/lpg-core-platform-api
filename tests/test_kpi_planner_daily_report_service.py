import datetime as dt

import pytest

from app.domain.kpi.planner_daily_report_service import PlannerDailyReportService


class _StubResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self):
        return self._payload


class _StubHTTPClient:
    def __init__(self, payloads):
        self._payloads = list(payloads)
        self.calls = []

    async def get(self, resource: str):
        self.calls.append(resource)
        index = len(self.calls) - 1
        payload = self._payloads[index] if index < len(self._payloads) else {"value": []}
        return _StubResponse(payload)


class _StubERPClient:
    def __init__(self, filtered_rows, fallback_payloads):
        self._filtered_rows = list(filtered_rows)
        self.http_client = _StubHTTPClient(fallback_payloads)
        self.filtered_queries = []

    async def _fetch_odata_collection(self, resource: str):
        self.filtered_queries.append(resource)
        return list(self._filtered_rows)


@pytest.mark.asyncio
async def test_fetch_capacity_ledger_rows_falls_back_when_server_filter_ignored() -> None:
    client = _StubERPClient(
        filtered_rows=[
            {"Posting_Date": "2026-02-09", "Work_Center_No": "40210", "Order_No": "M-WRONG", "Quantity": 1},
        ],
        fallback_payloads=[
            {
                "value": [
                    {"Posting_Date": "2026-02-10", "Work_Center_No": "40210", "Order_No": "M-KEEP", "Quantity": 1},
                    {"Posting_Date": "2026-02-10", "Work_Center_No": "99999", "Order_No": "M-OTHER", "Quantity": 1},
                    {"Posting_Date": "2026-02-09", "Work_Center_No": "40210", "Order_No": "M-OLD", "Quantity": 1},
                ]
            },
            {"value": []},
        ],
    )
    service = PlannerDailyReportService(client=client)

    rows = await service._fetch_capacity_ledger_rows(
        posting_date=dt.date(2026, 2, 10),
        work_center_no="40210",
        allow_empty=False,
        page_size=1000,
        max_pages=2,
    )

    assert [row.get("Order_No") for row in rows] == ["M-KEEP"]
    assert client.http_client.calls


@pytest.mark.asyncio
async def test_fetch_capacity_ledger_rows_uses_filtered_rows_when_in_scope() -> None:
    client = _StubERPClient(
        filtered_rows=[
            {"Posting_Date": "2026-02-09", "Work_Center_No": "40210", "Order_No": "M-WRONG-DATE", "Quantity": 1},
            {"Posting_Date": "2026-02-10", "Work_Center_No": "99999", "Order_No": "M-WRONG-WC", "Quantity": 1},
            {"Posting_Date": "2026-02-10", "Work_Center_No": "40210", "Order_No": "M-KEEP", "Quantity": 1},
        ],
        fallback_payloads=[],
    )
    service = PlannerDailyReportService(client=client)

    rows = await service._fetch_capacity_ledger_rows(
        posting_date=dt.date(2026, 2, 10),
        work_center_no="40210",
        allow_empty=False,
    )

    assert [row.get("Order_No") for row in rows] == ["M-KEEP"]
    assert not client.http_client.calls


def test_daily_report_cache_key_includes_version_prefix() -> None:
    key = PlannerDailyReportService._build_daily_report_cache_key(
        posting_date=dt.date(2026, 2, 10),
        tasklist_filter=None,
        work_center_no=None,
    )

    assert key.startswith("v2|2026-02-10|")

from __future__ import annotations

import datetime as dt
from decimal import Decimal
from typing import Any, Dict, Iterable, Optional

from app.adapters.erp_client import ERPClient
from app.domain.kpi.models import (
    SalesStatsBiggestCustomer,
    SalesStatsHistoryResponse,
    SalesStatsSnapshotResponse,
)
from app.domain.kpi.sales_stats_cache import sales_stats_cache
from app.settings import settings


def parse_snapshot_date(value: Optional[str]) -> dt.date:
    cleaned = (value or "").strip().lower()
    if not cleaned or cleaned == "today":
        return dt.date.today()
    try:
        return dt.date.fromisoformat(cleaned)
    except ValueError as exc:
        raise ValueError("Date must be YYYY-MM-DD or 'today'.") from exc


def _coerce_decimal(value: Any) -> Decimal:
    if value is None:
        return Decimal("0")
    try:
        return Decimal(str(value))
    except Exception:
        return Decimal("0")


def _coerce_bool(value: Any) -> Optional[bool]:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes"}:
            return True
        if normalized in {"false", "0", "no"}:
            return False
    return None


def _coerce_date(value: Any) -> Optional[dt.date]:
    if value is None:
        return None
    if isinstance(value, dt.date) and not isinstance(value, dt.datetime):
        return value
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, str):
        cleaned = value.strip()
        if not cleaned:
            return None
        try:
            return dt.date.fromisoformat(cleaned.split("T")[0])
        except ValueError:
            return None
    return None


def _first_non_empty(row: Dict[str, Any], fields: Iterable[str]) -> Optional[Any]:
    for field in fields:
        value = row.get(field)
        if value is not None and value != "":
            return value
    return None


def _sum_amounts_by_document(
    rows: Iterable[Dict[str, Any]],
    *,
    document_fields: Iterable[str],
    amount_fields: Iterable[str],
) -> Dict[str, Decimal]:
    totals: Dict[str, Decimal] = {}
    for row in rows:
        document_no_raw = _first_non_empty(row, document_fields)
        if not document_no_raw:
            continue
        document_no = str(document_no_raw)
        amount = _coerce_decimal(_first_non_empty(row, amount_fields))
        totals[document_no] = totals.get(document_no, Decimal("0")) + amount
    return totals


class SalesStatsService:
    """Build daily sales KPI snapshots from Business Central sales quotes and orders."""

    def __init__(self, client: Optional[ERPClient] = None) -> None:
        self._client = client or ERPClient()

    async def get_snapshot(
        self,
        *,
        snapshot_date: dt.date,
        refresh: bool = False,
    ) -> SalesStatsSnapshotResponse:
        snapshot_iso = snapshot_date.isoformat()
        if not refresh and sales_stats_cache.is_configured:
            cached = sales_stats_cache.get_snapshot(snapshot_iso)
            if cached:
                return SalesStatsSnapshotResponse.model_validate(cached)

        response = await self._compute_snapshot(snapshot_date=snapshot_date)

        if sales_stats_cache.is_configured:
            retention_cutoff = snapshot_date - dt.timedelta(days=settings.sales_stats_cache_retention_days)
            sales_stats_cache.upsert_snapshot(snapshot_iso, response.model_dump())
            sales_stats_cache.prune_before(retention_cutoff.isoformat())
        return response

    async def get_latest_snapshot(self) -> SalesStatsSnapshotResponse:
        if sales_stats_cache.is_configured:
            cached = sales_stats_cache.get_latest_snapshot()
            if cached:
                return SalesStatsSnapshotResponse.model_validate(cached)
        return await self.get_snapshot(snapshot_date=dt.date.today(), refresh=True)

    async def get_history(
        self,
        *,
        end_date: dt.date,
        days: int,
        ensure_end_snapshot: bool = True,
    ) -> SalesStatsHistoryResponse:
        start_date = end_date - dt.timedelta(days=days - 1)
        snapshots: list[SalesStatsSnapshotResponse] = []

        if sales_stats_cache.is_configured:
            cached = sales_stats_cache.list_snapshots(
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
            )
            snapshots = [SalesStatsSnapshotResponse.model_validate(item) for item in cached]

        if ensure_end_snapshot and end_date.isoformat() not in {item.snapshot_date for item in snapshots}:
            snapshots.append(await self.get_snapshot(snapshot_date=end_date, refresh=False))

        snapshots.sort(key=lambda item: item.snapshot_date)
        return SalesStatsHistoryResponse(
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            days=days,
            points=snapshots,
        )

    async def _compute_snapshot(self, *, snapshot_date: dt.date) -> SalesStatsSnapshotResponse:
        orders = await self._client.get_sales_order_headers()
        quotes = await self._client.get_sales_quote_headers()
        snapshot_iso = snapshot_date.isoformat()
        order_amounts_by_doc, quote_amounts_by_doc = await self._load_line_amount_maps()

        trailing_week_start = snapshot_date - dt.timedelta(days=6)
        previous_month_start = (snapshot_date.replace(day=1) - dt.timedelta(days=1)).replace(day=1)
        previous_month_end = snapshot_date.replace(day=1) - dt.timedelta(days=1)

        new_orders_count = 0
        last_week_orders_amount = Decimal("0")
        customer_totals_previous_month: Dict[str, Decimal] = {}
        customer_names: Dict[str, str] = {}

        for order in orders:
            order_date = _coerce_date(
                _first_non_empty(
                    order,
                    [
                        "Order_Date",
                        "Document_Date",
                        "Posting_Date",
                        "SystemCreatedAt",
                        "Created_At",
                    ],
                )
            )
            order_amount = _coerce_decimal(
                _first_non_empty(
                    order,
                    [
                        "Amount_Including_VAT",
                        "AmountIncludingVAT",
                        "Total_Amount",
                        "TotalAmount",
                        "Amount",
                    ],
                )
            )
            if order_amount == Decimal("0"):
                order_no = _first_non_empty(order, ["No", "Document_No", "DocumentNo"])
                if order_no:
                    order_amount = order_amounts_by_doc.get(str(order_no), Decimal("0"))
            if order_date == snapshot_date:
                new_orders_count += 1
            if order_date and trailing_week_start <= order_date <= snapshot_date:
                last_week_orders_amount += order_amount
            if order_date and previous_month_start <= order_date <= previous_month_end:
                customer_no = str(
                    _first_non_empty(
                        order,
                        ["Sell_to_Customer_No", "Bill_to_Customer_No", "Customer_No", "CustomerNo"],
                    )
                    or "UNKNOWN"
                )
                customer_totals_previous_month[customer_no] = (
                    customer_totals_previous_month.get(customer_no, Decimal("0")) + order_amount
                )
                customer_name_value = _first_non_empty(
                    order,
                    ["Sell_to_Customer_Name", "Bill_to_Name", "Customer_Name", "CustomerName"],
                )
                if customer_name_value:
                    customer_names[customer_no] = str(customer_name_value)

        total_quotes_count = len(quotes)
        new_quotes_count = 0
        total_quotes_amount = Decimal("0")
        last_week_quotes_amount = Decimal("0")
        pending_quotes_amount = Decimal("0")
        for quote in quotes:
            quote_date = _coerce_date(
                _first_non_empty(
                    quote,
                    [
                        "Quote_Date",
                        "Document_Date",
                        "Order_Date",
                        "Posting_Date",
                        "SystemCreatedAt",
                        "Created_At",
                    ],
                )
            )
            if not self._is_pending_quote(quote):
                quote_is_pending = False
            else:
                quote_is_pending = True
            quote_amount = _coerce_decimal(
                _first_non_empty(
                    quote,
                    [
                        "Amount_Including_VAT",
                        "AmountIncludingVAT",
                        "Total_Amount",
                        "TotalAmount",
                        "Amount",
                    ],
                )
            )
            if quote_amount == Decimal("0"):
                quote_no = _first_non_empty(quote, ["No", "Document_No", "DocumentNo"])
                if quote_no:
                    quote_amount = quote_amounts_by_doc.get(str(quote_no), Decimal("0"))
            if quote_date == snapshot_date:
                new_quotes_count += 1
            if quote_date and trailing_week_start <= quote_date <= snapshot_date:
                last_week_quotes_amount += quote_amount
            total_quotes_amount += quote_amount
            if quote_is_pending:
                pending_quotes_amount += quote_amount

        biggest_customer: Optional[SalesStatsBiggestCustomer] = None
        if customer_totals_previous_month:
            customer_no, amount = max(customer_totals_previous_month.items(), key=lambda item: item[1])
            biggest_customer = SalesStatsBiggestCustomer(
                customer_no=customer_no,
                customer_name=customer_names.get(customer_no),
                order_amount=round(float(amount), 2),
            )

        return SalesStatsSnapshotResponse(
            snapshot_date=snapshot_iso,
            new_orders_count=new_orders_count,
            last_week_orders_amount=round(float(last_week_orders_amount), 2),
            new_quotes_count=new_quotes_count,
            last_week_quotes_amount=round(float(last_week_quotes_amount), 2),
            total_quotes_count=total_quotes_count,
            total_quotes_amount=round(float(total_quotes_amount), 2),
            pending_quotes_amount=round(float(pending_quotes_amount), 2),
            biggest_customer_last_month=biggest_customer,
        )

    @staticmethod
    def _is_pending_quote(row: Dict[str, Any]) -> bool:
        for key in ("Closed", "Cancelled", "Canceled"):
            bool_value = _coerce_bool(row.get(key))
            if bool_value is True:
                return False

        status_value = _first_non_empty(
            row,
            ["Status", "Quote_Status", "Document_Status", "Order_Status", "State"],
        )
        if not status_value:
            return True

        status_normalized = str(status_value).strip().lower()
        non_pending_states = {
            "won",
            "accepted",
            "converted",
            "ordered",
            "closed",
            "cancelled",
            "canceled",
            "lost",
            "declined",
            "expired",
        }
        return status_normalized not in non_pending_states

    async def _load_line_amount_maps(self) -> tuple[Dict[str, Decimal], Dict[str, Decimal]]:
        order_totals: Dict[str, Decimal] = {}
        quote_totals: Dict[str, Decimal] = {}

        get_order_lines = getattr(self._client, "get_sales_order_lines", None)
        if callable(get_order_lines):
            try:
                order_lines = await get_order_lines()
                order_totals = _sum_amounts_by_document(
                    order_lines,
                    document_fields=["DocumentNo", "Document_No", "Document No", "DocumentNo_"],
                    amount_fields=[
                        "LineAmount",
                        "Line_Amount",
                        "Amount",
                        "AmountIncludingVAT",
                        "Amount_Including_VAT",
                    ],
                )
            except Exception:
                order_totals = {}

        get_quote_lines = getattr(self._client, "get_sales_quote_lines", None)
        if callable(get_quote_lines):
            try:
                quote_lines = await get_quote_lines()
                quote_totals = _sum_amounts_by_document(
                    quote_lines,
                    document_fields=["Document_No", "DocumentNo", "Document No", "DocumentNo_"],
                    amount_fields=[
                        "Line_Amount",
                        "LineAmount",
                        "Amount",
                        "Amount_Including_VAT",
                        "AmountIncludingVAT",
                        "Total_Amount_Excl_VAT",
                        "Subtotal_Excl_VAT",
                    ],
                )
            except Exception:
                quote_totals = {}

        return order_totals, quote_totals

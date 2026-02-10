from __future__ import annotations

import asyncio
import datetime as dt
from decimal import Decimal
from typing import Any, Dict, Iterable, Literal, Optional

from app.adapters.erp_client import ERPClient
from app.domain.kpi.models import (
    PurchasingActionCategoryStats,
    PurchasingPoTimelinePoint,
    PurchasingStatsResponse,
)
from app.integrations.cedule_purchasing_kpi_repository import CedulePurchasingKpiRepository

PurchasingPeriod = Literal["day", "week", "month"]


def parse_purchasing_stats_date(value: Optional[str]) -> dt.date:
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
        if value not in (None, ""):
            return value
    return None


def _period_start(value: dt.date, period: PurchasingPeriod) -> dt.date:
    if period == "day":
        return value
    if period == "week":
        return value - dt.timedelta(days=value.weekday())
    return value.replace(day=1)


def _period_end(period_start: dt.date, period: PurchasingPeriod) -> dt.date:
    if period == "day":
        return period_start
    if period == "week":
        return period_start + dt.timedelta(days=6)
    if period_start.month == 12:
        next_month = dt.date(period_start.year + 1, 1, 1)
    else:
        next_month = dt.date(period_start.year, period_start.month + 1, 1)
    return next_month - dt.timedelta(days=1)


class PurchasingStatsService:
    def __init__(
        self,
        client: Optional[ERPClient] = None,
        cedule_repository: Optional[CedulePurchasingKpiRepository] = None,
    ) -> None:
        self._client = client or ERPClient()
        self._cedule_repository = cedule_repository or CedulePurchasingKpiRepository()

    async def get_stats(
        self,
        *,
        end_date: dt.date,
        days: int,
        period: PurchasingPeriod = "week",
    ) -> PurchasingStatsResponse:
        start_date = end_date - dt.timedelta(days=days - 1)

        po_rows = await self._client.get_purchase_order_headers()

        buckets: Dict[dt.date, Dict[str, Decimal | int]] = {}
        total_pos = 0
        total_amount = Decimal("0")

        for row in po_rows:
            created_date = _coerce_date(
                _first_non_empty(
                    row,
                    [
                        "Order_Date",
                        "Document_Date",
                        "Posting_Date",
                        "SystemCreatedAt",
                        "Created_At",
                    ],
                )
            )
            if not created_date or created_date < start_date or created_date > end_date:
                continue

            amount = _coerce_decimal(
                _first_non_empty(
                    row,
                    [
                        "Amount_Including_VAT",
                        "AmountIncludingVAT",
                        "Total_Amount",
                        "TotalAmount",
                        "Amount",
                    ],
                )
            )
            bucket_key = _period_start(created_date, period)
            bucket = buckets.setdefault(bucket_key, {"po_count": 0, "total_amount": Decimal("0")})
            bucket["po_count"] = int(bucket["po_count"]) + 1
            bucket["total_amount"] = Decimal(bucket["total_amount"]) + amount
            total_pos += 1
            total_amount += amount

        po_timeline = [
            PurchasingPoTimelinePoint(
                period_start=bucket_date.isoformat(),
                period_end=min(_period_end(bucket_date, period), end_date).isoformat(),
                po_count=int(values["po_count"]),
                total_amount=round(float(Decimal(values["total_amount"])), 2),
            )
            for bucket_date, values in sorted(buckets.items(), key=lambda item: item[0])
        ]

        action_categories: list[PurchasingActionCategoryStats] = []
        if self._cedule_repository.is_configured:
            action_rows = await asyncio.to_thread(
                self._cedule_repository.list_action_counts_by_category,
                start_date=start_date,
                end_date=end_date,
            )
            action_categories = [
                PurchasingActionCategoryStats(
                    action_category=action_category,
                    updates_count=updates_count,
                )
                for action_category, updates_count in action_rows
            ]

        return PurchasingStatsResponse(
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            days=days,
            period=period,
            total_pos=total_pos,
            total_amount=round(float(total_amount), 2),
            po_timeline=po_timeline,
            action_categories=action_categories,
            total_action_updates=sum(item.updates_count for item in action_categories),
        )

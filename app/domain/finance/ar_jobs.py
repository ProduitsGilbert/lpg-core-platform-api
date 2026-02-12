from __future__ import annotations

import logging
from collections import defaultdict
from datetime import date, datetime, timedelta
from statistics import mean, median
from typing import Dict, List, Optional

from app.adapters.erp_client import ERPClient
from app.domain.finance.models import AccountsReceivablePaymentStats
from app.integrations.ar_payment_stats_repository import ArPaymentStatsRepository
from app.settings import settings

logger = logging.getLogger(__name__)


async def refresh_ar_payment_stats() -> None:
    repo = ArPaymentStatsRepository()
    if not repo.is_configured:
        logger.warning("Cedule database not configured; skipping AR payment stats refresh")
        return

    erp = ERPClient()
    due_from = date.today() - timedelta(days=settings.ar_payment_stats_lookback_days)
    records = await erp.get_closed_posted_sales_invoices(
        due_from=due_from,
        top=settings.ar_payment_stats_max_invoices,
    )

    stats = _compute_payment_stats(records)
    if not stats:
        logger.info(
            "No payment history data available for AR stats refresh",
            extra={
                "due_from": due_from.isoformat(),
                "record_count": len(records),
                "max_invoices": settings.ar_payment_stats_max_invoices,
            },
        )
        return

    repo.upsert_stats(stats)
    logger.info(
        "AR payment stats refreshed",
        extra={
            "customers": len(stats),
            "record_count": len(records),
            "due_from": due_from.isoformat(),
            "max_invoices": settings.ar_payment_stats_max_invoices,
        },
    )


def _compute_payment_stats(records: List[Dict[str, object]]) -> List[AccountsReceivablePaymentStats]:
    days_late_by_customer: Dict[str, List[int]] = defaultdict(list)
    due_dates_by_customer: Dict[str, List[date]] = defaultdict(list)

    for record in records:
        customer_no = record.get("Sell_to_Customer_No") or record.get("Bill_to_Customer_No") or record.get("Customer_No")
        if not customer_no:
            continue
        due_date = _parse_date(record.get("Due_Date"))
        modified_at = _extract_closed_event_datetime(record)
        if not due_date or not modified_at:
            continue
        days_late_raw = (modified_at.date() - due_date).days
        days_late = max(days_late_raw, 0)
        days_late_by_customer[str(customer_no)].append(days_late)
        due_dates_by_customer[str(customer_no)].append(due_date)

    stats: List[AccountsReceivablePaymentStats] = []
    for customer_no, days_list in days_late_by_customer.items():
        if not days_list:
            continue
        total = len(days_list)
        late_count = sum(1 for d in days_list if d > 0)
        due_dates = due_dates_by_customer.get(customer_no) or []
        stats.append(
            AccountsReceivablePaymentStats(
                customer_no=customer_no,
                invoice_count=total,
                avg_days_late=round(mean(days_list), 2) if days_list else None,
                median_days_late=round(median(days_list), 2) if days_list else None,
                late_ratio=round(late_count / total, 4) if total else None,
                window_start=min(due_dates) if due_dates else None,
                window_end=max(due_dates) if due_dates else None,
                updated_at=datetime.utcnow(),
            )
        )

    return stats


def _parse_date(value: object) -> Optional[date]:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        parsed = _parse_datetime(value)
        return parsed.date() if parsed else None
    return None


def _parse_datetime(value: object) -> Optional[datetime]:
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str):
        return None
    try:
        cleaned = value.replace("Z", "+00:00")
        return datetime.fromisoformat(cleaned)
    except ValueError:
        return None


def _extract_closed_event_datetime(record: Dict[str, object]) -> Optional[datetime]:
    """
    Return the best available closed/payment event timestamp from BC invoice headers.
    Field availability differs by tenant.
    """
    for field in ("Date_Time_Stamped", "Date_Time_Sent", "Date_Time_Canceled", "SystemModifiedAt"):
        parsed = _parse_datetime(record.get(field))
        if parsed:
            return parsed
    return None

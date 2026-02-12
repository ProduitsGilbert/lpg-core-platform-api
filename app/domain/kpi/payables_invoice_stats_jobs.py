from __future__ import annotations

import datetime as dt
import logging

from app.domain.kpi.payables_invoice_stats_service import PayablesInvoiceStatsService

logger = logging.getLogger(__name__)


async def refresh_payables_invoice_stats_snapshot() -> None:
    """Refresh the daily payables invoice stats snapshot cache."""
    service = PayablesInvoiceStatsService()
    snapshot_date = dt.date.today()
    try:
        await service.get_snapshot(snapshot_date=snapshot_date, refresh=True)
    except Exception as exc:
        logger.warning(
            "Failed to refresh payables invoice stats snapshot",
            extra={"snapshot_date": snapshot_date.isoformat(), "error": str(exc)},
        )

from __future__ import annotations

import datetime as dt
import logging

from app.domain.kpi.sales_stats_service import SalesStatsService

logger = logging.getLogger(__name__)


async def refresh_sales_stats_snapshot() -> None:
    """Refresh the daily sales stats snapshot cache."""
    service = SalesStatsService()
    snapshot_date = dt.date.today()
    try:
        await service.get_snapshot(snapshot_date=snapshot_date, refresh=True)
    except Exception as exc:
        logger.warning(
            "Failed to refresh sales stats snapshot",
            extra={"snapshot_date": snapshot_date.isoformat(), "error": str(exc)},
        )

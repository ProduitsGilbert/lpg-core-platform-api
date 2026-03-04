from __future__ import annotations

import datetime as dt
import logging

from app.domain.kpi.tool_prediction_service import ToolPredictionKpiService

logger = logging.getLogger(__name__)


async def refresh_tool_prediction_snapshot() -> None:
    """Refresh daily tooling shortage prediction snapshots for configured targets."""
    service = ToolPredictionKpiService()
    snapshot_date = dt.date.today()
    try:
        await service.refresh_snapshot(snapshot_date=snapshot_date, refresh_sources=True)
    except Exception as exc:
        logger.warning(
            "Failed to refresh daily tool prediction snapshot",
            extra={"snapshot_date": snapshot_date.isoformat(), "error": str(exc)},
        )

from __future__ import annotations

import datetime as dt
import logging

from app.domain.kpi.jobs_snapshot_service import JobsSnapshotService

logger = logging.getLogger(__name__)


async def refresh_jobs_snapshot() -> None:
    """Refresh the daily jobs KPI snapshot cache."""
    service = JobsSnapshotService()
    snapshot_date = dt.date.today()
    try:
        await service.get_snapshot(snapshot_date=snapshot_date, refresh=True, job_status="Open")
    except Exception as exc:
        logger.warning(
            "Failed to refresh jobs KPI snapshot",
            extra={"snapshot_date": snapshot_date.isoformat(), "error": str(exc)},
        )

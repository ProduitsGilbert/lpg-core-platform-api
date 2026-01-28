from __future__ import annotations

import asyncio
import datetime as dt
import logging

import logfire

from app.domain.kpi.planner_daily_report_cache import planner_kpi_cache
from app.domain.kpi.planner_daily_report_service import PlannerDailyReportService, _last_business_day

logger = logging.getLogger(__name__)


async def refresh_planner_kpi_cache() -> None:
    """Refresh cached planner KPI history for registered work centers."""
    workcenters = await planner_kpi_cache.list_registered_workcenters()
    if not workcenters:
        return

    posting_date = _last_business_day(dt.date.today())
    service = PlannerDailyReportService()

    semaphore = asyncio.Semaphore(3)

    async def _refresh_one(work_center_no: str) -> None:
        async with semaphore:
            try:
                await service.generate_workcenter_history(
                    posting_date=posting_date,
                    days=1,
                    work_center_no=work_center_no,
                )
            except Exception as exc:
                logger.warning(
                    "Failed to refresh planner KPI cache",
                    extra={"work_center_no": work_center_no, "error": str(exc)},
                )

    with logfire.span(
        "planner_kpi_cache.refresh",
        workcenter_count=len(workcenters),
        posting_date=posting_date.isoformat(),
    ):
        await asyncio.gather(*[_refresh_one(wc) for wc in workcenters])
        try:
            await service.generate_report(posting_date=posting_date)
        except Exception as exc:
            logger.warning(
                "Failed to refresh planner daily report snapshot",
                extra={"posting_date": posting_date.isoformat(), "error": str(exc)},
            )



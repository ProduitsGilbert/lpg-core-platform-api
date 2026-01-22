from __future__ import annotations

import datetime as dt
from typing import Any, Dict, Optional

from planner_daily_report.bc_workcenters import WorkCenterResolver
from planner_daily_report.capacity_accomplished import aggregate_capacity_accomplished
from planner_daily_report.config import PlannerReportConfig
from planner_daily_report.report import build_report_rows
from planner_daily_report.tasklist_future import aggregate_workcenter_tasklist
from sales_order_history_stats.bc_odata_client import BCODataClient


def generate_daily_planner_report(
    *,
    posting_date: dt.date,
    client: Optional[BCODataClient] = None,
    config: Optional[PlannerReportConfig] = None,
    tasklist_filter: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generate the planner report as a JSON-serializable dict (FastAPI-friendly).

    Notes:
    - Accomplished comes from CapacityLedgerEntries and is filtered client-side to the posting_date
      due to tenant quirks where Posting_Date filters may not be honored.
    - Future comes from WorkCenterTaskList filtered to Released only.
    - "Customer load" (GI######) is computed factory-wide (not per work center).
    """
    cfg = config or PlannerReportConfig.from_env()
    bc = client or BCODataClient.from_env()

    resolver = WorkCenterResolver(bc, endpoints=[cfg.workcenters_endpoint, "WorkCenters"])

    # Accomplished (yesterday / last business day)
    accomplished = aggregate_capacity_accomplished(bc, posting_date=posting_date)

    # Future (Released only)
    status_filter = "Status eq 'Released'"
    combined_filter = f"({status_filter})"
    if tasklist_filter:
        combined_filter = f"({tasklist_filter}) and ({status_filter})"

    future = aggregate_workcenter_tasklist(
        bc,
        endpoint=cfg.workcentertasklist_endpoint,
        odata_filter=combined_filter,
        unique_by="order",
        released_only=True,
        max_pages=None,
    )

    rows = build_report_rows(accomplished=accomplished, future=future, resolver=resolver)

    factory_gi_minutes_done = sum(getattr(v, "gi_minutes_done", 0) for v in accomplished.values())
    factory_gi_minutes_remaining = sum(getattr(v, "gi_minutes_remaining", 0) for v in future.values())

    return {
        "posting_date": posting_date.isoformat(),
        "customer_load_gi": {
            "minutes_done": factory_gi_minutes_done,
            "hours_done": round(factory_gi_minutes_done / 60.0, 2),
            "minutes_remaining": factory_gi_minutes_remaining,
            "hours_remaining": round(factory_gi_minutes_remaining / 60.0, 2),
        },
        "workcenters": [
            {
                "work_center_no": r.work_center_no,
                "work_center_name": r.work_center_name,
                "mo_done": r.mo_done,
                "mo_remaining": r.mo_remaining,
            }
            for r in rows
        ],
    }



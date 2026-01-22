from __future__ import annotations

import datetime as dt
import asyncio
import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import httpx
import logfire

from app.adapters.erp_client import ERPClient
from app.errors import ERPError, ERPUnavailable, ValidationException
from app.domain.kpi.models import (
    PlannerDailyCustomerLoad,
    PlannerDailyHistoryPoint,
    PlannerDailyReportResponse,
    PlannerDailyWorkCenter,
    PlannerDailyWorkcenterHistoryResponse,
)

logger = logging.getLogger(__name__)

GI_JOB_RE = re.compile(r"GI\d{6}$", re.IGNORECASE)


@dataclass(slots=True)
class _WorkCenterAccumulator:
    mo_orders: set[str]
    name_hint: Optional[str] = None

    def mo_count(self) -> int:
        return len(self.mo_orders)


def parse_report_date(value: str) -> dt.date:
    """Parse report date string, supporting 'yesterday' as last business day."""
    cleaned = (value or "").strip().lower()
    if not cleaned or cleaned == "yesterday":
        return _last_business_day(dt.date.today())
    try:
        return dt.date.fromisoformat(cleaned)
    except ValueError as exc:
        raise ValueError("Date must be YYYY-MM-DD or 'yesterday'.") from exc


def _last_business_day(today: dt.date) -> dt.date:
    weekday = today.weekday()
    if weekday == 0:
        return today - dt.timedelta(days=3)
    if weekday == 5:
        return today - dt.timedelta(days=1)
    if weekday == 6:
        return today - dt.timedelta(days=2)
    return today - dt.timedelta(days=1)


def _business_days_between(start: dt.date, end: dt.date) -> List[dt.date]:
    days: List[dt.date] = []
    cursor = start
    while cursor <= end:
        if cursor.weekday() < 5:
            days.append(cursor)
        cursor += dt.timedelta(days=1)
    return days


def _parse_odata_date(value: Any) -> Optional[dt.date]:
    if not value:
        return None
    if isinstance(value, dt.date):
        return value
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, str):
        try:
            return dt.date.fromisoformat(value.split("T")[0])
        except ValueError:
            return None
    return None


def _safe_float(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return 0.0
    return 0.0


def _extract_job_no(row: Dict[str, Any]) -> Optional[str]:
    for key, raw in row.items():
        if key.lower().startswith("wsi_job_no") and raw:
            return str(raw).strip()
    return None


def _extract_minutes(row: Dict[str, Any]) -> float:
    setup = _safe_float(row.get("Setup_Time"))
    run = _safe_float(row.get("Run_Time"))
    total = setup + run
    if total > 0:
        return total
    return 0.0


class PlannerDailyReportService:
    """Compute the planner daily report from Business Central OData."""

    def __init__(self, client: Optional[ERPClient] = None) -> None:
        self._client = client or ERPClient()

    async def generate_report(
        self,
        *,
        posting_date: dt.date,
        tasklist_filter: Optional[str] = None,
        work_center_no: Optional[str] = None,
    ) -> PlannerDailyReportResponse:
        with logfire.span(
            "planner_daily_report.generate_report",
            posting_date=posting_date.isoformat(),
        ):
            accomplished_task = self._aggregate_accomplished(
                posting_date=posting_date,
                work_center_no=work_center_no,
            )
            future_task = self._aggregate_future(
                tasklist_filter=tasklist_filter,
                work_center_no=work_center_no,
            )
            (accomplished, done_minutes), (future, remaining_minutes) = await asyncio.gather(
                accomplished_task,
                future_task,
            )

        work_center_nos = sorted(set(accomplished.keys()) | set(future.keys()))
        workcenters: List[PlannerDailyWorkCenter] = []
        for work_center_no in work_center_nos:
            done_acc = accomplished.get(work_center_no)
            future_acc = future.get(work_center_no)
            name_hint = None
            if done_acc and done_acc.name_hint:
                name_hint = done_acc.name_hint
            elif future_acc and future_acc.name_hint:
                name_hint = future_acc.name_hint
            workcenters.append(
                PlannerDailyWorkCenter(
                    work_center_no=work_center_no,
                    work_center_name=name_hint,
                    mo_done=done_acc.mo_count() if done_acc else 0,
                    mo_remaining=future_acc.mo_count() if future_acc else 0,
                )
            )

        customer_load = PlannerDailyCustomerLoad(
            minutes_done=round(done_minutes, 2),
            hours_done=round(done_minutes / 60.0, 2),
            minutes_remaining=round(remaining_minutes, 2),
            hours_remaining=round(remaining_minutes / 60.0, 2),
        )

        return PlannerDailyReportResponse(
            posting_date=posting_date.isoformat(),
            customer_load_gi=customer_load,
            workcenters=workcenters,
        )

    async def generate_workcenter_history(
        self,
        *,
        posting_date: dt.date,
        days: int,
        work_center_no: str,
        tasklist_filter: Optional[str] = None,
    ) -> PlannerDailyWorkcenterHistoryResponse:
        if days < 1:
            raise ValueError("Days must be >= 1.")

        start_date = posting_date - dt.timedelta(days=days - 1)
        business_days = _business_days_between(start_date, posting_date)

        tasklist_rows = await self._fetch_tasklist_rows(
            tasklist_filter=tasklist_filter,
            work_center_no=work_center_no,
        )

        async def _fetch_for_day(day: dt.date) -> tuple[dt.date, List[Dict[str, Any]]]:
            rows = await self._fetch_capacity_ledger_rows(
                posting_date=day,
                work_center_no=work_center_no,
                allow_empty=True,
            )
            return day, rows

        semaphore = asyncio.Semaphore(5)

        async def _with_limit(day: dt.date) -> tuple[dt.date, List[Dict[str, Any]]]:
            async with semaphore:
                return await _fetch_for_day(day)

        results = await asyncio.gather(*[_with_limit(day) for day in business_days])
        done_by_date: Dict[dt.date, List[Dict[str, Any]]] = {day: rows for day, rows in results}

        work_center_name = None
        points: List[PlannerDailyHistoryPoint] = []
        for day in business_days:
            rows = done_by_date.get(day, [])
            accomplished, _ = self._aggregate_accomplished_from_rows(rows)
            accumulator = accomplished.get(work_center_no)
            if accumulator and accumulator.name_hint and not work_center_name:
                work_center_name = accumulator.name_hint

            remaining = self._count_remaining_for_day(tasklist_rows, day)
            points.append(
                PlannerDailyHistoryPoint(
                    date=day.isoformat(),
                    mo_done=accumulator.mo_count() if accumulator else 0,
                    mo_remaining=remaining,
                )
            )

        return PlannerDailyWorkcenterHistoryResponse(
            work_center_no=work_center_no,
            work_center_name=work_center_name,
            start_date=start_date.isoformat(),
            end_date=posting_date.isoformat(),
            days=days,
            points=points,
        )

    async def _aggregate_accomplished(
        self,
        *,
        posting_date: dt.date,
        work_center_no: Optional[str],
    ) -> tuple[Dict[str, _WorkCenterAccumulator], float]:
        rows = await self._fetch_capacity_ledger_rows(
            posting_date=posting_date,
            work_center_no=work_center_no,
            allow_empty=False,
        )
        return self._aggregate_accomplished_from_rows(rows)

    async def _aggregate_future(
        self,
        *,
        tasklist_filter: Optional[str],
        work_center_no: Optional[str],
    ) -> tuple[Dict[str, _WorkCenterAccumulator], float]:
        rows = await self._fetch_tasklist_rows(
            tasklist_filter=tasklist_filter,
            work_center_no=work_center_no,
        )

        aggregates: Dict[str, _WorkCenterAccumulator] = {}
        gi_minutes_total = 0.0

        for row in rows:
            work_center_no = (
                row.get("WorkCenterNo")
                or row.get("Work_Center_No")
                or row.get("WorkCenter_No")
            )
            if not work_center_no:
                continue
            prod_order_no = (
                row.get("Prod_Order_No")
                or row.get("ProdOrderNo")
                or row.get("ProdOrder_No")
            )
            accumulator = aggregates.setdefault(
                str(work_center_no),
                _WorkCenterAccumulator(mo_orders=set()),
            )
            if prod_order_no:
                accumulator.mo_orders.add(str(prod_order_no))
            if not accumulator.name_hint:
                description = row.get("Description")
                if description:
                    accumulator.name_hint = str(description).strip() or None

            job_no = _extract_job_no(row)
            if job_no and GI_JOB_RE.match(job_no):
                gi_minutes_total += _extract_minutes(row)

        return aggregates, gi_minutes_total

    async def _fetch_tasklist_rows(
        self,
        *,
        tasklist_filter: Optional[str],
        work_center_no: Optional[str],
    ) -> List[Dict[str, Any]]:
        status_filter = "Status eq 'Released'"
        combined_filter = f"({status_filter})"
        if tasklist_filter:
            combined_filter = f"({tasklist_filter}) and ({status_filter})"
        if work_center_no:
            combined_filter = f"({combined_filter}) and (WorkCenterNo eq '{work_center_no}')"

        resource = f"WorkCenterTaskList?$filter={combined_filter}"
        try:
            return await self._client._fetch_odata_collection(resource)
        except ERPError:
            raise
        except httpx.HTTPStatusError as exc:
            raise ERPError(
                "Business Central returned an error while fetching WorkCenterTaskList",
                context={"status_code": exc.response.status_code},
            ) from exc
        except httpx.RequestError as exc:
            raise ERPUnavailable("Business Central service unreachable") from exc

    async def _fetch_capacity_ledger_rows(
        self,
        *,
        posting_date: dt.date,
        work_center_no: Optional[str],
        allow_empty: bool,
        page_size: int = 1000,
        max_pages: int = 200,
    ) -> List[Dict[str, Any]]:
        select_fields = ",".join(
            [
                "Posting_Date",
                "Work_Center_No",
                "Order_No",
                "Quantity",
                "WSI_Job_No",
                "Setup_Time",
                "Run_Time",
                "Description",
            ]
        )
        rows: List[Dict[str, Any]] = []
        # Try server-side filtering first for speed.
        filter_parts = [f"Posting_Date eq {posting_date.isoformat()}"]
        if work_center_no:
            filter_parts.append(f"Work_Center_No eq '{work_center_no}'")
        filtered_query = (
            "CapacityLedgerEntries"
            f"?$filter={' and '.join(filter_parts)}&$select={select_fields}"
        )
        try:
            filtered_rows = await self._client._fetch_odata_collection(filtered_query)
        except ERPError:
            filtered_rows = []
        if filtered_rows:
            return filtered_rows

        pages = 0
        skip = 0
        base_query = (
            "CapacityLedgerEntries"
            f"?$orderby=Posting_Date desc,Entry_No desc&$top={page_size}&$select={select_fields}"
        )

        observed_dates: List[dt.date] = []

        while pages < max_pages:
            pages += 1
            resource = f"{base_query}&$skip={skip}" if skip else base_query
            try:
                response = await self._client.http_client.get(resource)
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise ERPError(
                    "Business Central returned an error while fetching CapacityLedgerEntries",
                    context={"status_code": exc.response.status_code},
                ) from exc
            except httpx.RequestError as exc:
                raise ERPUnavailable("Business Central service unreachable") from exc

            payload = response.json()
            values = payload.get("value", [])
            if not isinstance(values, list):
                logger.warning(
                    "Unexpected CapacityLedgerEntries payload",
                    extra={"payload_type": type(payload)},
                )
                break
            if not values:
                break

            for row in values:
                row_date = _parse_odata_date(row.get("Posting_Date") or row.get("PostingDate"))
                if row_date is None:
                    continue
                observed_dates.append(row_date)
                if row_date == posting_date:
                    if work_center_no:
                        row_work_center_no = (
                            row.get("Work_Center_No")
                            or row.get("WorkCenterNo")
                            or row.get("WorkCenter_No")
                        )
                        if str(row_work_center_no or "") != work_center_no:
                            continue
                    rows.append(row)

            skip += page_size

        if pages >= max_pages:
            logger.warning(
                "CapacityLedgerEntries pagination cap reached",
                extra={
                    "posting_date": posting_date.isoformat(),
                    "pages": pages,
                },
            )

        if not rows:
            if allow_empty:
                return []
            min_date = min(observed_dates).isoformat() if observed_dates else None
            max_date = max(observed_dates).isoformat() if observed_dates else None
            raise ValidationException(
                "No CapacityLedgerEntries found for posting date.",
                field="date",
                context={
                    "posting_date": posting_date.isoformat(),
                    "observed_min_date": min_date,
                    "observed_max_date": max_date,
                    "pages_scanned": pages,
                },
            )
        return rows

    def _aggregate_accomplished_from_rows(
        self,
        rows: List[Dict[str, Any]],
    ) -> tuple[Dict[str, _WorkCenterAccumulator], float]:
        aggregates: Dict[str, _WorkCenterAccumulator] = {}
        gi_minutes_total = 0.0

        for row in rows:
            work_center_no = (
                row.get("Work_Center_No")
                or row.get("WorkCenterNo")
                or row.get("WorkCenter_No")
            )
            if not work_center_no:
                continue
            order_no = row.get("Order_No") or row.get("OrderNo")
            quantity = _safe_float(row.get("Quantity"))
            if quantity <= 0:
                continue
            accumulator = aggregates.setdefault(
                str(work_center_no),
                _WorkCenterAccumulator(mo_orders=set()),
            )
            if order_no:
                accumulator.mo_orders.add(str(order_no))
            if not accumulator.name_hint:
                description = row.get("Description")
                if description:
                    accumulator.name_hint = str(description).strip() or None

            job_no = _extract_job_no(row)
            if job_no and GI_JOB_RE.match(job_no):
                gi_minutes_total += _extract_minutes(row)

        return aggregates, gi_minutes_total

    def _count_remaining_for_day(
        self,
        rows: List[Dict[str, Any]],
        day: dt.date,
    ) -> int:
        orders: set[str] = set()
        for row in rows:
            prod_order_no = (
                row.get("Prod_Order_No")
                or row.get("ProdOrderNo")
                or row.get("ProdOrder_No")
            )
            if not prod_order_no:
                continue
            ending_date = _parse_odata_date(row.get("Ending_Date") or row.get("EndingDate"))
            starting_date = _parse_odata_date(row.get("Starting_Date") or row.get("StartingDate"))
            reference_date = ending_date or starting_date
            if reference_date and reference_date < day:
                continue
            orders.add(str(prod_order_no))
        return len(orders)


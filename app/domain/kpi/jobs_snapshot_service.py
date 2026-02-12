from __future__ import annotations

import asyncio
import datetime as dt
import time
from typing import Any, Dict, Optional

from app.adapters.erp_client import ERPClient
from app.domain.kpi.jobs_snapshot_cache import JobSnapshotRow, jobs_snapshot_cache
from app.domain.kpi.models import (
    JobKpiDailySnapshotResponse,
    JobKpiProgressPoint,
    JobKpiProgressResponse,
    JobKpiSnapshotHistoryPoint,
    JobKpiSnapshotHistoryResponse,
    JobKpiSnapshotItem,
    JobKpiWarmupResponse,
)
from app.settings import settings


def parse_jobs_snapshot_date(value: Optional[str]) -> dt.date:
    cleaned = (value or "").strip().lower()
    if not cleaned or cleaned == "today":
        return dt.date.today()
    try:
        return dt.date.fromisoformat(cleaned)
    except ValueError as exc:
        raise ValueError("Date must be YYYY-MM-DD or 'today'.") from exc


def _first_non_empty(row: Dict[str, Any], fields: tuple[str, ...]) -> Optional[Any]:
    for field in fields:
        value = row.get(field)
        if value is not None and value != "":
            return value
    return None


def _normalize_avancement_bom_percent(raw_value: Any) -> float:
    if raw_value is None:
        return 0.0
    if isinstance(raw_value, str):
        cleaned = raw_value.strip().replace("%", "").replace(",", ".")
        if not cleaned:
            return 0.0
        try:
            numeric = float(cleaned)
        except ValueError:
            return 0.0
        if "%" in raw_value:
            return max(0.0, min(100.0, numeric))
        if 0.0 <= numeric <= 1.0:
            numeric *= 100.0
        return max(0.0, min(100.0, numeric))
    try:
        numeric = float(raw_value)
    except (TypeError, ValueError):
        return 0.0
    if 0.0 <= numeric <= 1.0:
        numeric *= 100.0
    return max(0.0, min(100.0, numeric))


def _extract_job_name(job: Dict[str, Any]) -> Optional[str]:
    name_value = _first_non_empty(job, ("Description", "Job_Description", "Name", "Description_2"))
    return str(name_value) if name_value is not None else None


def _extract_job_status(job: Dict[str, Any]) -> Optional[str]:
    status_value = _first_non_empty(job, ("Status", "Job_Status"))
    return str(status_value) if status_value is not None else None


def _extract_job_avancement(job: Dict[str, Any]) -> float:
    raw_value = _first_non_empty(
        job,
        (
            "AvancementBOM",
            "Avancement_BOM",
            "Avancement_BOM_",
            "AvancementBOMPercent",
            "Avancement_BOM_Percent",
            "BOM_Progress",
        ),
    )
    return _normalize_avancement_bom_percent(raw_value)


def _extract_dimension_map(rows: list[Dict[str, Any]]) -> Dict[str, str]:
    dims: Dict[str, str] = {}
    for row in rows:
        code_raw = _first_non_empty(row, ("Dimension_Code", "DimensionCode", "Dimension_Code_"))
        value_raw = _first_non_empty(
            row, ("Dimension_Value_Code", "DimensionValueCode", "Dimension_Value_Code_")
        )
        if not code_raw or value_raw is None:
            continue
        dims[str(code_raw).strip().upper()] = str(value_raw)
    return dims


class JobsSnapshotService:
    """Build daily job KPI snapshots and provide history for trend tracking."""

    def __init__(self, client: Optional[ERPClient] = None) -> None:
        self._client = client or ERPClient()

    async def get_snapshot(
        self,
        *,
        snapshot_date: dt.date,
        refresh: bool = False,
        division: Optional[str] = None,
        region: Optional[str] = None,
        job_no: Optional[str] = None,
        job_status: Optional[str] = "Open",
    ) -> JobKpiDailySnapshotResponse:
        snapshot_iso = snapshot_date.isoformat()

        should_refresh = refresh or not self._has_snapshot(snapshot_iso)
        if should_refresh:
            await self._refresh_snapshot(snapshot_date=snapshot_date, job_status=job_status)

        rows = jobs_snapshot_cache.list_snapshot_rows(
            snapshot_date=snapshot_iso,
            division=division,
            region=region,
            job_no=job_no,
            job_status=job_status,
        )
        items = [self._to_item(row) for row in rows]
        return JobKpiDailySnapshotResponse(
            snapshot_date=snapshot_iso,
            total_jobs=len(items),
            jobs=items,
        )

    async def get_latest_snapshot(
        self,
        *,
        division: Optional[str] = None,
        region: Optional[str] = None,
        job_no: Optional[str] = None,
        job_status: Optional[str] = "Open",
    ) -> JobKpiDailySnapshotResponse:
        latest = jobs_snapshot_cache.get_latest_snapshot_date() if jobs_snapshot_cache.is_configured else None
        if latest:
            snapshot_date = dt.date.fromisoformat(latest)
            return await self.get_snapshot(
                snapshot_date=snapshot_date,
                refresh=False,
                division=division,
                region=region,
                job_no=job_no,
                job_status=job_status,
            )
        return await self.get_snapshot(
            snapshot_date=dt.date.today(),
            refresh=True,
            division=division,
            region=region,
            job_no=job_no,
            job_status=job_status,
        )

    async def get_history(
        self,
        *,
        end_date: dt.date,
        days: int,
        ensure_end_snapshot: bool = True,
        division: Optional[str] = None,
        region: Optional[str] = None,
        job_no: Optional[str] = None,
        job_status: Optional[str] = "Open",
    ) -> JobKpiSnapshotHistoryResponse:
        if ensure_end_snapshot:
            await self.get_snapshot(
                snapshot_date=end_date,
                refresh=False,
                division=None,
                region=None,
                job_no=None,
                job_status=job_status,
            )

        start_date = end_date - dt.timedelta(days=days - 1)
        rows = jobs_snapshot_cache.list_history_rows(
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            division=division,
            region=region,
            job_no=job_no,
            job_status=job_status,
        )
        points = [
            JobKpiSnapshotHistoryPoint(
                snapshot_date=row.snapshot_date,
                job_no=row.job_no,
                job_name=row.job_name,
                job_status=row.job_status,
                avancement_bom_percent=round(row.avancement_bom_percent, 2),
                division=row.division,
                region=row.region,
            )
            for row in rows
        ]
        return JobKpiSnapshotHistoryResponse(
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            days=days,
            points=points,
        )

    async def get_job_progress_history(
        self,
        *,
        job_no: str,
        end_date: dt.date,
        days: int,
        ensure_end_snapshot: bool = True,
        division: Optional[str] = None,
        region: Optional[str] = None,
        job_status: Optional[str] = "Open",
    ) -> JobKpiProgressResponse:
        job_no_clean = (job_no or "").strip()
        if not job_no_clean:
            raise ValueError("job_no is required")

        if ensure_end_snapshot:
            existing_end_rows = jobs_snapshot_cache.list_snapshot_rows(
                snapshot_date=end_date.isoformat(),
                job_no=job_no_clean,
                job_status=job_status,
            )
            if not existing_end_rows:
                await self._refresh_single_job_snapshot(
                    snapshot_date=end_date,
                    job_no=job_no_clean,
                    job_status=job_status,
                )

        start_date = end_date - dt.timedelta(days=days - 1)
        rows = jobs_snapshot_cache.list_history_rows(
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            division=division,
            region=region,
            job_no=job_no_clean,
            job_status=job_status,
        )

        latest = rows[-1] if rows else None
        return JobKpiProgressResponse(
            job_no=job_no_clean,
            job_name=latest.job_name if latest else None,
            job_status=latest.job_status if latest else None,
            division=latest.division if latest else None,
            region=latest.region if latest else None,
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            days=days,
            points=[
                JobKpiProgressPoint(
                    snapshot_date=row.snapshot_date,
                    avancement_bom_percent=round(row.avancement_bom_percent, 2),
                )
                for row in rows
            ],
        )

    async def warmup_snapshot(
        self,
        *,
        snapshot_date: dt.date,
        job_status: Optional[str] = "Open",
    ) -> JobKpiWarmupResponse:
        started_at = time.monotonic()
        snapshot = await self.get_snapshot(
            snapshot_date=snapshot_date,
            refresh=True,
            job_status=job_status,
        )
        duration = time.monotonic() - started_at
        return JobKpiWarmupResponse(
            snapshot_date=snapshot.snapshot_date,
            refreshed=True,
            total_jobs=snapshot.total_jobs,
            duration_seconds=round(duration, 2),
        )

    def _has_snapshot(self, snapshot_iso: str) -> bool:
        if not jobs_snapshot_cache.is_configured:
            return False
        rows = jobs_snapshot_cache.list_snapshot_rows(snapshot_date=snapshot_iso)
        return len(rows) > 0

    async def _refresh_snapshot(self, *, snapshot_date: dt.date, job_status: Optional[str]) -> None:
        jobs = await self._client.get_jobs(status_filter=job_status)
        snapshot_iso = snapshot_date.isoformat()

        semaphore = asyncio.Semaphore(8)

        async def _build_row(job: Dict[str, Any]) -> Optional[JobSnapshotRow]:
            job_no_raw = _first_non_empty(job, ("No", "Job_No", "No_"))
            if not job_no_raw:
                return None
            job_no_value = str(job_no_raw)
            async with semaphore:
                dimension_rows = await self._client.get_job_default_dimensions(job_no_value)
            dims = _extract_dimension_map(dimension_rows)
            return JobSnapshotRow(
                snapshot_date=snapshot_iso,
                job_no=job_no_value,
                job_name=_extract_job_name(job),
                job_status=_extract_job_status(job),
                avancement_bom_percent=_extract_job_avancement(job),
                division=dims.get("DIVISION"),
                region=dims.get("REGION"),
            )

        built = await asyncio.gather(*[_build_row(job) for job in jobs]) if jobs else []
        rows = [row for row in built if row is not None]

        if jobs_snapshot_cache.is_configured:
            retention_cutoff = snapshot_date - dt.timedelta(days=settings.jobs_snapshot_cache_retention_days)
            jobs_snapshot_cache.upsert_snapshot_rows(snapshot_iso, rows)
            jobs_snapshot_cache.prune_before(retention_cutoff.isoformat())

    async def _refresh_single_job_snapshot(
        self,
        *,
        snapshot_date: dt.date,
        job_no: str,
        job_status: Optional[str],
    ) -> None:
        job = await self._client.get_job(job_no)
        if not job:
            return

        resolved_status = _extract_job_status(job)
        if job_status and resolved_status and resolved_status != job_status:
            return

        dimension_rows = await self._client.get_job_default_dimensions(job_no)
        dims = _extract_dimension_map(dimension_rows)

        row = JobSnapshotRow(
            snapshot_date=snapshot_date.isoformat(),
            job_no=job_no,
            job_name=_extract_job_name(job),
            job_status=resolved_status,
            avancement_bom_percent=_extract_job_avancement(job),
            division=dims.get("DIVISION"),
            region=dims.get("REGION"),
        )
        if jobs_snapshot_cache.is_configured:
            jobs_snapshot_cache.upsert_snapshot_rows(
                snapshot_date.isoformat(),
                [row],
                replace_snapshot=False,
            )

    @staticmethod
    def _to_item(row: JobSnapshotRow) -> JobKpiSnapshotItem:
        return JobKpiSnapshotItem(
            job_no=row.job_no,
            job_name=row.job_name,
            job_status=row.job_status,
            avancement_bom_percent=round(row.avancement_bom_percent, 2),
            division=row.division,
            region=row.region,
        )

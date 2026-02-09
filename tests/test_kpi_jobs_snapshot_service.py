import datetime as dt

import pytest

from app.domain.kpi.jobs_snapshot_cache import JobsSnapshotCache
from app.domain.kpi.jobs_snapshot_service import JobsSnapshotService


class _StubERP:
    async def get_jobs(self, *, status_filter="Open", top=None):
        _ = (status_filter, top)
        return [
            {
                "No": "GIM1136",
                "Description": "Factory Upgrade",
                "Status": "Open",
                "AvancementBOM": "65.5%",
            },
            {
                "No": "GIM2000",
                "Description": "Line Improvement",
                "Status": "Open",
                "Avancement_BOM": 0.72,
            },
        ]

    async def get_job_default_dimensions(self, job_no: str, *, dimension_code=None):
        _ = dimension_code
        if job_no == "GIM1136":
            return [
                {"Dimension_Code": "DIVISION", "Dimension_Value_Code": "CONST"},
                {"Dimension_Code": "REGION", "Dimension_Value_Code": "CAN-QC"},
            ]
        return [
            {"Dimension_Code": "DIVISION", "Dimension_Value_Code": "MFG"},
            {"Dimension_Code": "REGION", "Dimension_Value_Code": "CAN-ON"},
        ]

    async def get_job(self, job_no: str):
        if job_no == "GIM1136":
            return {
                "No": "GIM1136",
                "Description": "Factory Upgrade",
                "Status": "Open",
                "AvancementBOM": 0.665,
            }
        return None


@pytest.mark.asyncio
async def test_jobs_snapshot_service_snapshot_and_history(monkeypatch, tmp_path):
    cache_path = tmp_path / "jobs_snapshot.sqlite"
    test_cache = JobsSnapshotCache(str(cache_path))
    monkeypatch.setattr("app.domain.kpi.jobs_snapshot_service.jobs_snapshot_cache", test_cache)

    service = JobsSnapshotService(client=_StubERP())

    snapshot = await service.get_snapshot(snapshot_date=dt.date(2026, 2, 9), refresh=True)
    assert snapshot.snapshot_date == "2026-02-09"
    assert snapshot.total_jobs == 2
    assert snapshot.jobs[0].job_no == "GIM1136"
    assert snapshot.jobs[0].avancement_bom_percent == 65.5
    assert snapshot.jobs[1].avancement_bom_percent == 72.0

    filtered = await service.get_snapshot(
        snapshot_date=dt.date(2026, 2, 9),
        refresh=False,
        division="CONST",
    )
    assert filtered.total_jobs == 1
    assert filtered.jobs[0].region == "CAN-QC"

    history = await service.get_history(
        end_date=dt.date(2026, 2, 9),
        days=1,
        ensure_end_snapshot=False,
        job_no="GIM1136",
    )
    assert history.start_date == "2026-02-09"
    assert history.end_date == "2026-02-09"
    assert len(history.points) == 1
    assert history.points[0].job_no == "GIM1136"


@pytest.mark.asyncio
async def test_specific_job_history_uses_single_job_refresh(monkeypatch, tmp_path):
    class _SingleJobERP(_StubERP):
        async def get_jobs(self, *, status_filter="Open", top=None):
            raise AssertionError("get_jobs should not be called for single-job refresh")

    cache_path = tmp_path / "jobs_snapshot.sqlite"
    test_cache = JobsSnapshotCache(str(cache_path))
    monkeypatch.setattr("app.domain.kpi.jobs_snapshot_service.jobs_snapshot_cache", test_cache)

    service = JobsSnapshotService(client=_SingleJobERP())
    progress = await service.get_job_progress_history(
        job_no="GIM1136",
        end_date=dt.date(2026, 2, 9),
        days=1,
        ensure_end_snapshot=True,
    )

    assert progress.job_no == "GIM1136"
    assert len(progress.points) == 1
    assert progress.points[0].snapshot_date == "2026-02-09"
    assert progress.points[0].avancement_bom_percent == 66.5

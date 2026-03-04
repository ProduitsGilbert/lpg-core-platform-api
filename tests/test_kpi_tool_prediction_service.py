import datetime as dt

import pytest

from app.domain.kpi.tool_prediction_service import (
    ToolPredictionKpiService,
    parse_tool_prediction_targets,
)
from app.domain.tooling.models import (
    FutureToolingNeedResponse,
    FutureToolingToolSummary,
    ToolingUsageHistoryResponse,
    ToolingUsageHistoryToolSummary,
)


class _StubFutureNeedsService:
    async def get_future_needs(self, work_center_no: str, refresh: bool):
        _ = (work_center_no, refresh)
        return FutureToolingNeedResponse(
            work_center_no="40253",
            snapshot_date="2026-03-04",
            generated_at="2026-03-04T05:00:00+00:00",
            tools_summary=[
                FutureToolingToolSummary(
                    tool_id="1035",
                    total_required_use_time_seconds=3600,
                    rows_count=3,
                    program_count=2,
                )
            ],
        )


class _StubUsageHistoryService:
    async def get_usage_history(
        self,
        *,
        work_center_no: str,
        machine_center: str,
        months: int,
        refresh: bool,
    ):
        _ = (work_center_no, machine_center, months, refresh)
        return ToolingUsageHistoryResponse(
            work_center_no="40253",
            machine_center="DMC100",
            start_date="2025-12-04",
            end_date="2026-03-04",
            generated_at="2026-03-04T05:00:00+00:00",
            tools_summary=[
                ToolingUsageHistoryToolSummary(
                    tool_id="1035",
                    total_estimated_use_time_seconds=18000,
                    rows_count=5,
                    unique_program_count=3,
                    months_active=2,
                )
            ],
        )


class _StubFeatureRepository:
    is_configured = True

    def list_inventory_metrics(self, *, machine_center: str):
        _ = machine_center
        return {
            "1035": {
                "total_remaining_life": 90.0,
                "inventory_instances": 3,
                "available_instances": 2,
                "sister_count_total": 2,
                "sister_count_available": 1,
                "sister_count_machine": 1,
            }
        }

    def list_usage_metrics(self, *, machine_center: str, t0: dt.datetime):
        _ = (machine_center, t0)
        return {
            "1035": {
                "time_since_last_use_hours": 2.5,
                "uses_last_24h": 6,
                "uses_last_7d": 20,
            }
        }

    def list_wear_metrics(self, *, machine_center: str, t0: dt.datetime):
        _ = (machine_center, t0)
        return {
            "1035": {
                "wear_rate_24h": 4.0,
                "wear_rate_7d": 3.5,
            }
        }


class _StubSnapshotRepository:
    is_configured = True

    def __init__(self) -> None:
        self._latest_snapshot_date: str | None = None
        self._rows: list[dict] = []

    def upsert_snapshot_rows(
        self,
        *,
        snapshot_date: str,
        machine_center: str,
        work_center_no: str,
        generated_at: dt.datetime,
        rows: list[dict],
    ) -> int:
        self._latest_snapshot_date = snapshot_date
        self._rows = []
        for row in rows:
            self._rows.append(
                {
                    **row,
                    "snapshot_date": snapshot_date,
                    "machine_center": machine_center,
                    "work_center_no": work_center_no,
                    "generated_at": generated_at,
                    "updated_at": generated_at,
                }
            )
        return len(rows)

    def get_latest_snapshot_date(self, *, machine_center: str | None = None):
        _ = machine_center
        return self._latest_snapshot_date

    def list_snapshot_rows(self, *, snapshot_date: str, machine_center: str | None = None, limit: int = 200):
        _ = machine_center
        return self._rows[:limit] if snapshot_date == self._latest_snapshot_date else []


class _StubPredictorClient:
    async def predict_rows(self, *, machine_center: str, rows: list[dict]):
        _ = machine_center
        assert len(rows) == 1
        return {
            "1035": {
                "shortage_probability": 0.81,
                "shortage_label": "HIGH",
                "raw": {"prediction": "HIGH", "probability": 0.81},
            }
        }


@pytest.mark.asyncio
async def test_tool_prediction_service_refresh_and_latest(monkeypatch) -> None:
    monkeypatch.setattr("app.domain.kpi.tool_prediction_service.settings.tool_prediction_targets", "40253:DMC100")
    snapshot_repo = _StubSnapshotRepository()
    service = ToolPredictionKpiService(
        future_needs_service=_StubFutureNeedsService(),
        usage_history_service=_StubUsageHistoryService(),
        feature_repository=_StubFeatureRepository(),
        snapshot_repository=snapshot_repo,
        predictor_client=_StubPredictorClient(),
    )

    written = await service.refresh_snapshot(snapshot_date=dt.date(2026, 3, 4), refresh_sources=True)

    assert written == 1
    latest = await service.get_latest_snapshot(machine_center="DMC100", limit=50)
    assert latest.snapshot_date == "2026-03-04"
    assert latest.total_tools == 1
    assert latest.predictions[0].tool_id == "1035"
    assert latest.predictions[0].shortage_probability == 0.81
    assert latest.predictions[0].future_usage_minutes_24h <= latest.predictions[0].future_usage_minutes_48h
    assert latest.predictions[0].future_usage_minutes_48h <= latest.predictions[0].future_usage_minutes_7d


def test_parse_tool_prediction_targets() -> None:
    targets = parse_tool_prediction_targets("40253:DMC100, 40279:NHX5500, 40253:DMC100")
    assert targets == [("40253", "DMC100"), ("40279", "NHX5500")]

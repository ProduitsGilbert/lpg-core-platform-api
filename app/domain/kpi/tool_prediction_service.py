from __future__ import annotations

import asyncio
import datetime as dt
from typing import Any, Optional

from app.adapters.tool_prediction_client import ToolPredictionClient
from app.domain.kpi.models import (
    ToolShortagePredictionItem,
    ToolShortagePredictionSnapshotResponse,
)
from app.domain.tooling.future_needs_service import FutureToolingNeedService
from app.domain.tooling.usage_history_service import ToolingUsageHistoryService
from app.integrations.tool_prediction_feature_repository import ToolPredictionFeatureRepository
from app.integrations.tool_prediction_repository import ToolPredictionSnapshotRepository
from app.settings import settings


def parse_tool_prediction_date(value: Optional[str]) -> dt.date:
    if value is None:
        return dt.date.today()
    text = str(value).strip().lower()
    if text in {"", "today"}:
        return dt.date.today()
    if text == "yesterday":
        return dt.date.today() - dt.timedelta(days=1)
    try:
        return dt.date.fromisoformat(text)
    except ValueError as exc:
        raise ValueError("date must be YYYY-MM-DD, 'today', or 'yesterday'") from exc


def parse_tool_prediction_targets(value: str | None) -> list[tuple[str, str]]:
    raw = value or ""
    targets: list[tuple[str, str]] = []
    for token in raw.split(","):
        cleaned = token.strip()
        if not cleaned:
            continue
        if ":" not in cleaned:
            continue
        work_center_no, machine_center = cleaned.split(":", 1)
        wc = work_center_no.strip()
        mc = machine_center.strip().upper()
        if wc and mc:
            targets.append((wc, mc))

    if targets:
        # Preserve order while removing duplicates.
        deduped: list[tuple[str, str]] = []
        seen: set[tuple[str, str]] = set()
        for target in targets:
            if target in seen:
                continue
            seen.add(target)
            deduped.append(target)
        return deduped
    return [("40253", "DMC100")]


class ToolPredictionKpiService:
    """Daily tool shortage prediction snapshot generation + KPI reads."""

    def __init__(
        self,
        *,
        future_needs_service: FutureToolingNeedService | None = None,
        usage_history_service: ToolingUsageHistoryService | None = None,
        feature_repository: ToolPredictionFeatureRepository | None = None,
        snapshot_repository: ToolPredictionSnapshotRepository | None = None,
        predictor_client: ToolPredictionClient | None = None,
    ) -> None:
        self._future_needs_service = future_needs_service or FutureToolingNeedService()
        self._usage_history_service = usage_history_service or ToolingUsageHistoryService()
        self._feature_repository = feature_repository or ToolPredictionFeatureRepository()
        self._snapshot_repository = snapshot_repository or ToolPredictionSnapshotRepository()
        self._predictor_client = predictor_client or ToolPredictionClient()

    @property
    def is_configured(self) -> bool:
        return self._snapshot_repository.is_configured

    async def refresh_snapshot(
        self,
        *,
        snapshot_date: Optional[dt.date] = None,
        refresh_sources: bool = True,
    ) -> int:
        if not self._snapshot_repository.is_configured:
            return 0

        snapshot_date = snapshot_date or dt.date.today()
        generated_at = dt.datetime.now(dt.timezone.utc)
        targets = parse_tool_prediction_targets(settings.tool_prediction_targets)

        total_rows = 0
        for work_center_no, machine_center in targets:
            base_rows = await self._build_feature_rows(
                work_center_no=work_center_no,
                machine_center=machine_center,
                refresh_sources=refresh_sources,
            )
            payload_rows = [_build_prediction_payload(row) for row in base_rows]
            predictions = await self._predictor_client.predict_rows(
                machine_center=machine_center,
                rows=payload_rows,
            )

            rows_to_store: list[dict[str, Any]] = []
            for row in base_rows:
                tool_id = str(row.get("tool_id") or "").strip().upper()
                predicted = predictions.get(tool_id, {})
                rows_to_store.append(
                    {
                        **row,
                        "shortage_probability": _safe_probability(predicted.get("shortage_probability")),
                        "shortage_label": _clean_text(predicted.get("shortage_label")),
                        "prediction_payload_json": _build_prediction_payload(row),
                        "predictor_response_json": predicted.get("raw"),
                    }
                )

            written = await asyncio.to_thread(
                self._snapshot_repository.upsert_snapshot_rows,
                snapshot_date=snapshot_date.isoformat(),
                machine_center=machine_center,
                work_center_no=work_center_no,
                generated_at=generated_at,
                rows=rows_to_store,
            )
            total_rows += written

        return total_rows

    async def get_latest_snapshot(
        self,
        *,
        machine_center: Optional[str] = None,
        limit: int = 200,
    ) -> ToolShortagePredictionSnapshotResponse:
        latest_snapshot = await asyncio.to_thread(
            self._snapshot_repository.get_latest_snapshot_date,
            machine_center=_clean_machine_center(machine_center),
        )
        if not latest_snapshot:
            return ToolShortagePredictionSnapshotResponse(
                snapshot_date=dt.date.today().isoformat(),
                machine_center=_clean_machine_center(machine_center),
                total_tools=0,
                predictions=[],
            )

        return await self.get_snapshot(
            snapshot_date=dt.date.fromisoformat(latest_snapshot),
            machine_center=machine_center,
            limit=limit,
        )

    async def get_snapshot(
        self,
        *,
        snapshot_date: dt.date,
        machine_center: Optional[str] = None,
        limit: int = 200,
    ) -> ToolShortagePredictionSnapshotResponse:
        rows = await asyncio.to_thread(
            self._snapshot_repository.list_snapshot_rows,
            snapshot_date=snapshot_date.isoformat(),
            machine_center=_clean_machine_center(machine_center),
            limit=limit,
        )

        predictions = [ToolShortagePredictionItem.model_validate(_normalize_snapshot_row(row)) for row in rows]
        return ToolShortagePredictionSnapshotResponse(
            snapshot_date=snapshot_date.isoformat(),
            machine_center=_clean_machine_center(machine_center),
            total_tools=len(predictions),
            predictions=predictions,
        )

    async def _build_feature_rows(
        self,
        *,
        work_center_no: str,
        machine_center: str,
        refresh_sources: bool,
    ) -> list[dict[str, Any]]:
        future_needs = await self._future_needs_service.get_future_needs(
            work_center_no=work_center_no,
            refresh=refresh_sources,
        )
        usage_history = await self._usage_history_service.get_usage_history(
            work_center_no=work_center_no,
            machine_center=machine_center,
            months=3,
            refresh=refresh_sources,
        )

        usage_minutes_90d: dict[str, float] = {}
        for summary in usage_history.tools_summary:
            tool_id = _clean_tool_id(summary.tool_id)
            if not tool_id:
                continue
            usage_minutes_90d[tool_id] = max(float(summary.total_estimated_use_time_seconds) / 60.0, 0.0)

        now_utc = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)
        inventory_by_tool, usage_by_tool, wear_by_tool = await asyncio.gather(
            asyncio.to_thread(
                self._feature_repository.list_inventory_metrics,
                machine_center=machine_center,
            ),
            asyncio.to_thread(
                self._feature_repository.list_usage_metrics,
                machine_center=machine_center,
                t0=now_utc,
            ),
            asyncio.to_thread(
                self._feature_repository.list_wear_metrics,
                machine_center=machine_center,
                t0=now_utc,
            ),
        )

        rows: list[dict[str, Any]] = []
        for summary in future_needs.tools_summary:
            tool_id = _clean_tool_id(summary.tool_id)
            if not tool_id:
                continue

            total_required_seconds = max(int(summary.total_required_use_time_seconds or 0), 0)
            rows_count = max(int(summary.rows_count or 0), 0)
            program_count = max(int(summary.program_count or 0), 0)

            inventory = inventory_by_tool.get(tool_id, {})
            usage = usage_by_tool.get(tool_id, {})
            wear = wear_by_tool.get(tool_id, {})

            tool_usage_90d = max(float(usage_minutes_90d.get(tool_id, 0.0)), 0.0)
            uses_last_7d = max(int(usage.get("uses_last_7d", 0) or 0), 0)

            future_total_minutes = total_required_seconds / 60.0
            daily_rate = max(tool_usage_90d / 90.0, uses_last_7d / 7.0, 0.0)
            future_24h = min(future_total_minutes, daily_rate)
            future_48h = min(future_total_minutes, daily_rate * 2.0)
            future_7d = min(future_total_minutes, daily_rate * 7.0)

            # Preserve monotonic windows required by the predictor contract.
            future_48h = max(future_48h, future_24h)
            future_7d = max(future_7d, future_48h)

            rows.append(
                {
                    "tool_id": tool_id,
                    "total_required_use_time_seconds": total_required_seconds,
                    "rows_count": rows_count,
                    "program_count": program_count,
                    "total_remaining_life": max(float(inventory.get("total_remaining_life", 0.0) or 0.0), 0.0),
                    "inventory_instances": max(int(inventory.get("inventory_instances", 0) or 0), 0),
                    "available_instances": max(int(inventory.get("available_instances", 0) or 0), 0),
                    "sister_count_total": max(int(inventory.get("sister_count_total", 0) or 0), 0),
                    "sister_count_available": max(int(inventory.get("sister_count_available", 0) or 0), 0),
                    "sister_count_machine": max(int(inventory.get("sister_count_machine", 0) or 0), 0),
                    "time_since_last_use_hours": max(float(usage.get("time_since_last_use_hours", 0.0) or 0.0), 0.0),
                    "uses_last_24h": max(int(usage.get("uses_last_24h", 0) or 0), 0),
                    "uses_last_7d": uses_last_7d,
                    "wear_rate_24h": max(float(wear.get("wear_rate_24h", 0.0) or 0.0), 0.0),
                    "wear_rate_7d": max(float(wear.get("wear_rate_7d", 0.0) or 0.0), 0.0),
                    "tool_usage_minutes_90d": round(tool_usage_90d, 4),
                    "future_usage_minutes_24h": round(future_24h, 4),
                    "future_usage_minutes_48h": round(future_48h, 4),
                    "future_usage_minutes_7d": round(future_7d, 4),
                }
            )

        rows.sort(key=lambda item: str(item.get("tool_id") or ""))
        return rows


def _build_prediction_payload(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "tool_id": row.get("tool_id"),
        "total_required_use_time_seconds": row.get("total_required_use_time_seconds", 0),
        "rows_count": row.get("rows_count", 0),
        "program_count": row.get("program_count", 0),
        "total_remaining_life": row.get("total_remaining_life", 0.0),
        "inventory_instances": row.get("inventory_instances", 0),
        "available_instances": row.get("available_instances", 0),
        "sister_count_total": row.get("sister_count_total", 0),
        "sister_count_available": row.get("sister_count_available", 0),
        "sister_count_machine": row.get("sister_count_machine", 0),
        "time_since_last_use_hours": row.get("time_since_last_use_hours", 0.0),
        "uses_last_24h": row.get("uses_last_24h", 0),
        "uses_last_7d": row.get("uses_last_7d", 0),
        "wear_rate_24h": row.get("wear_rate_24h", 0.0),
        "wear_rate_7d": row.get("wear_rate_7d", 0.0),
        "future_usage_minutes_24h": row.get("future_usage_minutes_24h", 0.0),
        "future_usage_minutes_48h": row.get("future_usage_minutes_48h", 0.0),
        "future_usage_minutes_7d": row.get("future_usage_minutes_7d", 0.0),
    }


def _normalize_snapshot_row(row: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = dict(row)
    normalized["snapshot_date"] = _as_iso_date(row.get("snapshot_date"))
    normalized["generated_at"] = _as_datetime(row.get("generated_at"))
    normalized["updated_at"] = _as_datetime(row.get("updated_at"))
    normalized["work_center_no"] = _clean_text(row.get("work_center_no")) or ""
    normalized["machine_center"] = _clean_machine_center(row.get("machine_center")) or ""
    normalized["tool_id"] = _clean_tool_id(row.get("tool_id")) or ""
    normalized["shortage_probability"] = _safe_probability(row.get("shortage_probability"))
    normalized["shortage_label"] = _clean_text(row.get("shortage_label"))
    return normalized


def _as_iso_date(value: Any) -> str:
    if isinstance(value, dt.datetime):
        return value.date().isoformat()
    if isinstance(value, dt.date):
        return value.isoformat()
    text_value = str(value or "").strip()
    if not text_value:
        return dt.date.today().isoformat()
    if "T" in text_value:
        text_value = text_value.split("T", 1)[0]
    return text_value


def _as_datetime(value: Any) -> dt.datetime:
    if isinstance(value, dt.datetime):
        return value
    if isinstance(value, dt.date):
        return dt.datetime.combine(value, dt.time.min)
    text_value = str(value or "").strip()
    if not text_value:
        return dt.datetime.now(dt.timezone.utc)
    try:
        return dt.datetime.fromisoformat(text_value)
    except ValueError:
        return dt.datetime.now(dt.timezone.utc)


def _clean_tool_id(value: Any) -> Optional[str]:
    if value is None:
        return None
    cleaned = str(value).strip().upper()
    return cleaned or None


def _clean_machine_center(value: Any) -> Optional[str]:
    if value is None:
        return None
    cleaned = str(value).strip().upper()
    return cleaned or None


def _clean_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None


def _safe_probability(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        probability = float(value)
    except (TypeError, ValueError):
        return None
    return max(0.0, min(probability, 1.0))

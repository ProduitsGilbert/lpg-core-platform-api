"""Feature repository for tooling shortage prediction inputs."""

from __future__ import annotations

from datetime import datetime
import logging
from typing import Any, Optional

from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from app.errors import DatabaseError
from app.integrations.cedule_repository import get_cedule_engine

logger = logging.getLogger(__name__)


class ToolPredictionFeatureRepository:
    """Queries Cedule ToolingTasks/ToolInstanceHistory for model features."""

    def __init__(self, engine: Optional[Engine] = None) -> None:
        self._engine = engine or get_cedule_engine()

    @property
    def is_configured(self) -> bool:
        return self._engine is not None

    def list_inventory_metrics(self, *, machine_center: str) -> dict[str, dict[str, float | int]]:
        if not self._engine:
            return {}

        location_patterns = _inventory_location_patterns(machine_center)
        location_where_sql, location_params = _build_like_filter_sql(
            column="CurrentLocation",
            patterns=location_patterns,
            param_prefix="loc",
        )

        query_primary = text(
            f"""
            WITH latest AS (
              SELECT
                  ToolId,
                  SisterId,
                  RemainingLifeTime,
                  CurrentLocation,
                  Status,
                  SnapshotTimestamp,
                  ROW_NUMBER() OVER (
                    PARTITION BY ToolId, ISNULL(NULLIF(LTRIM(RTRIM(SisterId)), ''), CurrentLocation)
                    ORDER BY SnapshotTimestamp DESC
                  ) AS rn
              FROM [Cedule].[dbo].[ToolInstanceHistory]
              WHERE {location_where_sql}
            )
            SELECT
                UPPER(LTRIM(RTRIM(ToolId))) AS tool_id,
                SUM(CAST(RemainingLifeTime AS FLOAT)) AS total_remaining_life,
                COUNT(*) AS inventory_instances,
                SUM(CASE WHEN Status = 1 THEN 1 ELSE 0 END) AS available_instances,
                COUNT(DISTINCT ISNULL(NULLIF(LTRIM(RTRIM(SisterId)), ''), CurrentLocation)) AS sister_count_total,
                COUNT(DISTINCT CASE WHEN Status = 1 THEN ISNULL(NULLIF(LTRIM(RTRIM(SisterId)), ''), CurrentLocation) END) AS sister_count_available,
                COUNT(DISTINCT CASE WHEN Status = 1 THEN LEFT(CurrentLocation, CHARINDEX(':', CurrentLocation + ':') - 1) END) AS sister_count_machine
            FROM latest
            WHERE rn = 1
            GROUP BY UPPER(LTRIM(RTRIM(ToolId)));
            """
        )

        query_fallback = text(
            f"""
            WITH latest AS (
              SELECT
                  ToolId,
                  SisterId,
                  RemainingLifeTime,
                  CurrentLocation,
                  Status,
                  SnapshotDate,
                  ROW_NUMBER() OVER (
                    PARTITION BY ToolId, ISNULL(NULLIF(LTRIM(RTRIM(SisterId)), ''), CurrentLocation)
                    ORDER BY SnapshotDate DESC
                  ) AS rn
              FROM [Cedule].[dbo].[ToolInstanceHistory]
              WHERE {location_where_sql}
            )
            SELECT
                UPPER(LTRIM(RTRIM(ToolId))) AS tool_id,
                SUM(CAST(RemainingLifeTime AS FLOAT)) AS total_remaining_life,
                COUNT(*) AS inventory_instances,
                SUM(CASE WHEN Status = 1 THEN 1 ELSE 0 END) AS available_instances,
                COUNT(DISTINCT ISNULL(NULLIF(LTRIM(RTRIM(SisterId)), ''), CurrentLocation)) AS sister_count_total,
                COUNT(DISTINCT CASE WHEN Status = 1 THEN ISNULL(NULLIF(LTRIM(RTRIM(SisterId)), ''), CurrentLocation) END) AS sister_count_available,
                COUNT(DISTINCT CASE WHEN Status = 1 THEN LEFT(CurrentLocation, CHARINDEX(':', CurrentLocation + ':') - 1) END) AS sister_count_machine
            FROM latest
            WHERE rn = 1
            GROUP BY UPPER(LTRIM(RTRIM(ToolId)));
            """
        )

        rows = self._query_with_fallback(
            query_primary,
            query_fallback,
            params=location_params,
            error_message="Unable to query tool prediction inventory metrics",
        )

        features: dict[str, dict[str, float | int]] = {}
        for row in rows:
            tool_id = _clean_tool_id(row.get("tool_id"))
            if not tool_id:
                continue
            features[tool_id] = {
                "total_remaining_life": _safe_float(row.get("total_remaining_life")),
                "inventory_instances": _safe_int(row.get("inventory_instances")),
                "available_instances": _safe_int(row.get("available_instances")),
                "sister_count_total": _safe_int(row.get("sister_count_total")),
                "sister_count_available": _safe_int(row.get("sister_count_available")),
                "sister_count_machine": _safe_int(row.get("sister_count_machine")),
            }
        return features

    def list_usage_metrics(
        self,
        *,
        machine_center: str,
        t0: datetime,
    ) -> dict[str, dict[str, float | int]]:
        if not self._engine:
            return {}

        machine_patterns = _usage_machine_patterns(machine_center)
        machine_where_sql, machine_params = _build_like_filter_sql(
            column="cnc_machine",
            patterns=machine_patterns,
            param_prefix="machine",
        )

        query = text(
            f"""
            SELECT
                UPPER(LTRIM(RTRIM(tool_id))) AS tool_id,
                DATEDIFF(hour, MAX([timestamp]), :t0) AS time_since_last_use_hours,
                SUM(CASE WHEN [timestamp] >= DATEADD(hour, -24, :t0) AND [timestamp] < :t0 THEN 1 ELSE 0 END) AS uses_last_24h,
                SUM(CASE WHEN [timestamp] >= DATEADD(day, -7, :t0) AND [timestamp] < :t0 THEN 1 ELSE 0 END) AS uses_last_7d
            FROM [Cedule].[dbo].[ToolingTasks]
            WHERE {machine_where_sql}
            GROUP BY UPPER(LTRIM(RTRIM(tool_id)));
            """
        )

        try:
            with self._engine.connect() as connection:
                rows = connection.execute(
                    query,
                    {"t0": t0, **machine_params},
                ).mappings().all()
        except SQLAlchemyError as exc:
            logger.error(
                "Failed to query tool prediction usage metrics",
                exc_info=exc,
                extra={"machine_center": machine_center},
            )
            raise DatabaseError("Unable to query tool prediction usage metrics") from exc

        features: dict[str, dict[str, float | int]] = {}
        for row in rows:
            tool_id = _clean_tool_id(row.get("tool_id"))
            if not tool_id:
                continue
            features[tool_id] = {
                "time_since_last_use_hours": _safe_float(row.get("time_since_last_use_hours")),
                "uses_last_24h": _safe_int(row.get("uses_last_24h")),
                "uses_last_7d": _safe_int(row.get("uses_last_7d")),
            }
        return features

    def list_wear_metrics(
        self,
        *,
        machine_center: str,
        t0: datetime,
    ) -> dict[str, dict[str, float]]:
        if not self._engine:
            return {}

        location_patterns = _inventory_location_patterns(machine_center)
        location_where_sql, location_params = _build_like_filter_sql(
            column="CurrentLocation",
            patterns=location_patterns,
            param_prefix="loc",
        )

        query_snapshot_date = text(
            f"""
            WITH daily AS (
              SELECT
                  UPPER(LTRIM(RTRIM(ToolId))) AS tool_id,
                  CAST(SnapshotDate AS date) AS d,
                  SUM(CAST(RemainingLifeTime AS FLOAT)) AS total_remaining_life
              FROM [Cedule].[dbo].[ToolInstanceHistory]
              WHERE {location_where_sql}
                AND SnapshotDate >= DATEADD(day, -8, CAST(:t0 AS date))
                AND SnapshotDate <= CAST(:t0 AS date)
              GROUP BY UPPER(LTRIM(RTRIM(ToolId))), CAST(SnapshotDate AS date)
            ),
            deltas AS (
              SELECT
                  d0.tool_id,
                  d0.d,
                  CASE WHEN d1.total_remaining_life - d0.total_remaining_life > 0
                       THEN d1.total_remaining_life - d0.total_remaining_life
                       ELSE 0 END AS wear_value
              FROM daily d0
              LEFT JOIN daily d1
                ON d1.tool_id = d0.tool_id
               AND d1.d = DATEADD(day, -1, d0.d)
            )
            SELECT
                tool_id,
                MAX(CASE WHEN d = CAST(:t0 AS date) THEN wear_value ELSE 0 END) AS wear_rate_24h,
                AVG(CASE WHEN d >= DATEADD(day, -6, CAST(:t0 AS date))
                          AND d <= CAST(:t0 AS date)
                         THEN wear_value END) AS wear_rate_7d
            FROM deltas
            GROUP BY tool_id;
            """
        )

        query_snapshot_timestamp = text(
            f"""
            WITH daily AS (
              SELECT
                  UPPER(LTRIM(RTRIM(ToolId))) AS tool_id,
                  CAST(SnapshotTimestamp AS date) AS d,
                  SUM(CAST(RemainingLifeTime AS FLOAT)) AS total_remaining_life
              FROM [Cedule].[dbo].[ToolInstanceHistory]
              WHERE {location_where_sql}
                AND SnapshotTimestamp >= DATEADD(day, -8, CAST(:t0 AS date))
                AND SnapshotTimestamp < DATEADD(day, 1, CAST(:t0 AS date))
              GROUP BY UPPER(LTRIM(RTRIM(ToolId))), CAST(SnapshotTimestamp AS date)
            ),
            deltas AS (
              SELECT
                  d0.tool_id,
                  d0.d,
                  CASE WHEN d1.total_remaining_life - d0.total_remaining_life > 0
                       THEN d1.total_remaining_life - d0.total_remaining_life
                       ELSE 0 END AS wear_value
              FROM daily d0
              LEFT JOIN daily d1
                ON d1.tool_id = d0.tool_id
               AND d1.d = DATEADD(day, -1, d0.d)
            )
            SELECT
                tool_id,
                MAX(CASE WHEN d = CAST(:t0 AS date) THEN wear_value ELSE 0 END) AS wear_rate_24h,
                AVG(CASE WHEN d >= DATEADD(day, -6, CAST(:t0 AS date))
                          AND d <= CAST(:t0 AS date)
                         THEN wear_value END) AS wear_rate_7d
            FROM deltas
            GROUP BY tool_id;
            """
        )

        rows = self._query_with_fallback(
            query_snapshot_date,
            query_snapshot_timestamp,
            params={
                "t0": t0,
                **location_params,
            },
            error_message="Unable to query tool prediction wear metrics",
        )

        features: dict[str, dict[str, float]] = {}
        for row in rows:
            tool_id = _clean_tool_id(row.get("tool_id"))
            if not tool_id:
                continue
            features[tool_id] = {
                "wear_rate_24h": _safe_float(row.get("wear_rate_24h")),
                "wear_rate_7d": _safe_float(row.get("wear_rate_7d")),
            }
        return features

    def _query_with_fallback(
        self,
        primary_query: Any,
        fallback_query: Any,
        *,
        params: dict[str, Any],
        error_message: str,
    ) -> list[dict[str, Any]]:
        if not self._engine:
            return []

        try:
            with self._engine.connect() as connection:
                rows = connection.execute(primary_query, params).mappings().all()
                return [dict(row) for row in rows]
        except SQLAlchemyError as primary_exc:
            logger.debug("Primary tool-prediction feature query failed, trying fallback", exc_info=primary_exc)
            try:
                with self._engine.connect() as connection:
                    rows = connection.execute(fallback_query, params).mappings().all()
                    return [dict(row) for row in rows]
            except SQLAlchemyError as exc:
                logger.error(error_message, exc_info=exc)
                raise DatabaseError(error_message) from exc


def _clean_tool_id(value: Any) -> Optional[str]:
    if value is None:
        return None
    cleaned = str(value).strip().upper()
    return cleaned or None


def _safe_float(value: Any) -> float:
    if value is None:
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _safe_int(value: Any) -> int:
    if value is None:
        return 0
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def _inventory_location_patterns(machine_center: str) -> list[str]:
    center = (machine_center or "").strip()
    center_upper = center.upper()
    patterns = [f"{center}%"] if center else ["%"]

    # Fastems2 inventory is usually tracked in MC magazines/spindles and Gts robot storage.
    if center_upper in {"NHX5500", "FASTEMS2", "FASTEM2"}:
        patterns.extend(
            [
                "MC%.Magazine.%",
                "MC%.Special.Spindle%",
                "Gts Robot.Storage.%",
                "Gts Robot.%",
            ]
        )

    # Preserve order while deduplicating.
    seen: set[str] = set()
    deduped: list[str] = []
    for pattern in patterns:
        if pattern in seen:
            continue
        seen.add(pattern)
        deduped.append(pattern)
    return deduped


def _usage_machine_patterns(machine_center: str) -> list[str]:
    center = (machine_center or "").strip()
    center_upper = center.upper()
    patterns = [f"{center}%"] if center else ["%"]

    # Fastems2 tooling tasks often use cnc_machine='Fastem2'.
    if center_upper in {"NHX5500", "FASTEMS2", "FASTEM2"}:
        patterns.extend(["Fastem2%", "FASTEM2%", "NHX5500%"])

    seen: set[str] = set()
    deduped: list[str] = []
    for pattern in patterns:
        if pattern in seen:
            continue
        seen.add(pattern)
        deduped.append(pattern)
    return deduped


def _build_like_filter_sql(
    *,
    column: str,
    patterns: list[str],
    param_prefix: str,
) -> tuple[str, dict[str, str]]:
    if not patterns:
        return "1=1", {}

    clauses: list[str] = []
    params: dict[str, str] = {}
    for index, pattern in enumerate(patterns):
        param_name = f"{param_prefix}_{index}"
        clauses.append(f"{column} LIKE :{param_name}")
        params[param_name] = pattern
    return " OR ".join(clauses), params

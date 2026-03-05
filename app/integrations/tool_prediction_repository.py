"""Repository for persisted tooling shortage prediction snapshots."""

from __future__ import annotations

from datetime import date, datetime
from functools import lru_cache
import json
import logging
from typing import Any, Optional
from urllib.parse import quote_plus

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import QueuePool

from app.errors import DatabaseError
from app.settings import settings

logger = logging.getLogger(__name__)


TOOL_PREDICTION_TABLE = "[dbo].[90_USINAGE_ToolPrediction_DailySnapshot]"


def _build_tool_prediction_url() -> Optional[str]:
    """Build SQLAlchemy DSN for dedicated tool prediction database."""
    if settings.tool_prediction_db_dsn:
        return settings.tool_prediction_db_dsn.strip()

    server = settings.tool_prediction_sql_server or settings.cedule_sql_server
    database = settings.tool_prediction_sql_database or settings.cedule_sql_database
    username = settings.tool_prediction_sql_username or settings.cedule_sql_username
    password = settings.tool_prediction_sql_password or settings.cedule_sql_password
    driver = (settings.tool_prediction_sql_driver or "ODBC Driver 18 for SQL Server").replace(" ", "+")

    if not all((server, database, username, password)):
        return None

    user_encoded = quote_plus(username or "")
    password_encoded = quote_plus(password or "")

    return (
        f"mssql+pyodbc://{user_encoded}:{password_encoded}@{server}/{database}"
        f"?driver={driver}&TrustServerCertificate=yes"
    )


@lru_cache(maxsize=1)
def _cached_engine(url: str) -> Engine:
    return create_engine(
        url,
        poolclass=QueuePool,
        pool_size=min(settings.db_pool_size, 5),
        max_overflow=min(settings.db_pool_overflow, 5),
        pool_timeout=settings.db_pool_timeout,
        pool_recycle=1800,
        pool_pre_ping=True,
        connect_args={
            "timeout": settings.db_pool_timeout,
            "autocommit": False,
            "ansi": True,
        },
    )


def get_tool_prediction_engine() -> Optional[Engine]:
    """Return shared SQLAlchemy engine for tool prediction database."""
    url = _build_tool_prediction_url()
    if not url:
        logger.debug("Tool prediction database is not configured")
        return None
    return _cached_engine(url)


class ToolPredictionSnapshotRepository:
    """Read/write repository for daily tool shortage prediction rows."""

    def __init__(self, engine: Optional[Engine] = None) -> None:
        self._engine = engine or get_tool_prediction_engine()

    @property
    def is_configured(self) -> bool:
        return self._engine is not None

    def upsert_snapshot_rows(
        self,
        *,
        snapshot_date: str,
        machine_center: str,
        work_center_no: str,
        generated_at: datetime,
        rows: list[dict[str, Any]],
    ) -> int:
        if not self._engine:
            return 0

        delete_query = text(
            f"""
            DELETE FROM {TOOL_PREDICTION_TABLE}
            WHERE snapshot_date = :snapshot_date
              AND machine_center = :machine_center
            """
        )
        insert_query = text(
            f"""
            INSERT INTO {TOOL_PREDICTION_TABLE} (
                snapshot_date,
                generated_at,
                work_center_no,
                machine_center,
                tool_id,
                total_required_use_time_seconds,
                rows_count,
                program_count,
                total_remaining_life,
                inventory_instances,
                available_instances,
                sister_count_total,
                sister_count_available,
                sister_count_machine,
                time_since_last_use_hours,
                uses_last_24h,
                uses_last_7d,
                wear_rate_24h,
                wear_rate_7d,
                tool_usage_minutes_90d,
                future_usage_minutes_24h,
                future_usage_minutes_48h,
                future_usage_minutes_7d,
                shortage_probability,
                shortage_label,
                prediction_payload_json,
                predictor_response_json,
                updated_at
            )
            VALUES (
                :snapshot_date,
                :generated_at,
                :work_center_no,
                :machine_center,
                :tool_id,
                :total_required_use_time_seconds,
                :rows_count,
                :program_count,
                :total_remaining_life,
                :inventory_instances,
                :available_instances,
                :sister_count_total,
                :sister_count_available,
                :sister_count_machine,
                :time_since_last_use_hours,
                :uses_last_24h,
                :uses_last_7d,
                :wear_rate_24h,
                :wear_rate_7d,
                :tool_usage_minutes_90d,
                :future_usage_minutes_24h,
                :future_usage_minutes_48h,
                :future_usage_minutes_7d,
                :shortage_probability,
                :shortage_label,
                :prediction_payload_json,
                :predictor_response_json,
                SYSUTCDATETIME()
            )
            """
        )

        serializable_rows: list[dict[str, Any]] = []
        for row in rows:
            payload_json = row.get("prediction_payload_json")
            predictor_json = row.get("predictor_response_json")
            serializable_rows.append(
                {
                    **row,
                    "snapshot_date": snapshot_date,
                    "generated_at": generated_at,
                    "work_center_no": work_center_no,
                    "machine_center": machine_center,
                    "prediction_payload_json": _json_or_none(payload_json),
                    "predictor_response_json": _json_or_none(predictor_json),
                }
            )

        try:
            with self._engine.begin() as connection:
                connection.execute(
                    delete_query,
                    {
                        "snapshot_date": snapshot_date,
                        "machine_center": machine_center,
                    },
                )
                if serializable_rows:
                    connection.execute(insert_query, serializable_rows)
        except SQLAlchemyError as exc:
            logger.error(
                "Failed to upsert tool prediction snapshot rows",
                exc_info=exc,
                extra={
                    "snapshot_date": snapshot_date,
                    "machine_center": machine_center,
                    "row_count": len(rows),
                },
            )
            raise DatabaseError("Unable to persist tool prediction snapshot") from exc

        return len(serializable_rows)

    def get_latest_snapshot_date(self, *, machine_center: Optional[str] = None) -> Optional[str]:
        if not self._engine:
            return None

        query = (
            text(
                f"""
                SELECT MAX(snapshot_date) AS snapshot_date
                FROM {TOOL_PREDICTION_TABLE}
                WHERE machine_center = :machine_center
                """
            )
            if machine_center
            else text(
                f"""
                SELECT MAX(snapshot_date) AS snapshot_date
                FROM {TOOL_PREDICTION_TABLE}
                """
            )
        )

        params: dict[str, Any] = {"machine_center": machine_center} if machine_center else {}

        try:
            with self._engine.connect() as connection:
                row = connection.execute(query, params).mappings().first()
        except SQLAlchemyError as exc:
            logger.error("Failed to read latest tool prediction snapshot date", exc_info=exc)
            raise DatabaseError("Unable to read latest tool prediction snapshot date") from exc

        if not row:
            return None
        value = row.get("snapshot_date")
        if isinstance(value, date):
            return value.isoformat()
        if value is None:
            return None
        return str(value)

    def list_snapshot_rows(
        self,
        *,
        snapshot_date: str,
        machine_center: Optional[str] = None,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        if not self._engine:
            return []

        limit = max(1, min(limit, 5000))
        where_machine = " AND machine_center = :machine_center" if machine_center else ""
        query = text(
            f"""
            SELECT
                snapshot_date,
                generated_at,
                work_center_no,
                machine_center,
                tool_id,
                total_required_use_time_seconds,
                rows_count,
                program_count,
                total_remaining_life,
                inventory_instances,
                available_instances,
                sister_count_total,
                sister_count_available,
                sister_count_machine,
                time_since_last_use_hours,
                uses_last_24h,
                uses_last_7d,
                wear_rate_24h,
                wear_rate_7d,
                tool_usage_minutes_90d,
                future_usage_minutes_24h,
                future_usage_minutes_48h,
                future_usage_minutes_7d,
                shortage_probability,
                shortage_label,
                prediction_payload_json,
                predictor_response_json,
                updated_at,
                (
                    COALESCE(shortage_probability, 0.0)
                    + CASE WHEN COALESCE(available_instances, 0) > 0 THEN 0.10 ELSE 0.0 END
                    - CASE WHEN COALESCE(inventory_instances, 0) = 0 THEN 0.20 ELSE 0.0 END
                ) AS blended_risk_score
            FROM {TOOL_PREDICTION_TABLE}
            WHERE snapshot_date = :snapshot_date
            {where_machine}
            ORDER BY
                CASE WHEN shortage_probability IS NULL THEN 1 ELSE 0 END,
                blended_risk_score DESC,
                shortage_probability DESC,
                total_required_use_time_seconds DESC,
                tool_id ASC
            OFFSET 0 ROWS FETCH NEXT :limit ROWS ONLY
            """
        )

        params: dict[str, Any] = {
            "snapshot_date": snapshot_date,
            "limit": limit,
        }
        if machine_center:
            params["machine_center"] = machine_center

        try:
            with self._engine.connect() as connection:
                rows = connection.execute(query, params).mappings().all()
        except SQLAlchemyError as exc:
            logger.error(
                "Failed to query tool prediction snapshot rows",
                exc_info=exc,
                extra={"snapshot_date": snapshot_date, "machine_center": machine_center},
            )
            raise DatabaseError("Unable to query tool prediction snapshot rows") from exc

        return [dict(row) for row in rows]


def _json_or_none(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    try:
        return json.dumps(value)
    except TypeError:
        return None

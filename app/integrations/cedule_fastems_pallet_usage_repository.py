"""Repository for Fastems pallet usage views in Cedule."""

from __future__ import annotations

from datetime import date, datetime
import logging
from typing import List, Optional

from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from app.domain.kpi.models import Fastems1PalletUsage, Fastems2PalletUsage
from app.errors import DatabaseError
from app.integrations.cedule_repository import get_cedule_engine

logger = logging.getLogger(__name__)


class FastemsPalletUsageRepository:
    """Read-only access to Fastems pallet usage views."""

    def __init__(self, engine: Optional[Engine] = None) -> None:
        self._engine = engine or get_cedule_engine()

    @property
    def is_configured(self) -> bool:
        return self._engine is not None

    def list_fastems1_usage(self) -> List[Fastems1PalletUsage]:
        if not self._engine:
            return []

        query = text(
            """
            SELECT
                PalletNumber AS pallet_number,
                LatestSnapshotId AS latest_snapshot_id,
                LatestSnapshotTimeUtc AS latest_snapshot_time_utc,
                RoutePhase AS route_phase,
                PhaseName AS phase_name,
                CommandData AS command_data,
                ChangeCount24h AS change_count_24h,
                ChangeCount7d AS change_count_7d,
                ChangeCount30d AS change_count_30d,
                ChangeCount90d AS change_count_90d
            FROM [Cedule].[fastems1].[vw_MachinePallet_Usage]
            """
        )

        try:
            with self._engine.connect() as connection:
                rows = connection.execute(query).mappings().all()
        except SQLAlchemyError as exc:
            logger.error("Failed to query Fastems1 pallet usage", exc_info=exc)
            raise DatabaseError("Unable to query Fastems1 pallet usage") from exc

        results: List[Fastems1PalletUsage] = []
        for row in rows:
            pallet_number = _clean_str(row.get("pallet_number")) or ""
            results.append(
                Fastems1PalletUsage(
                    pallet_number=pallet_number,
                    latest_snapshot_id=_safe_int(row.get("latest_snapshot_id")),
                    latest_snapshot_time_utc=_safe_datetime(row.get("latest_snapshot_time_utc")),
                    route_phase=_clean_str(row.get("route_phase")),
                    phase_name=_clean_str(row.get("phase_name")),
                    command_data=_clean_str(row.get("command_data")),
                    change_count_24h=_safe_int(row.get("change_count_24h"), default=0),
                    change_count_7d=_safe_int(row.get("change_count_7d"), default=0),
                    change_count_30d=_safe_int(row.get("change_count_30d"), default=0),
                    change_count_90d=_safe_int(row.get("change_count_90d"), default=0),
                )
            )

        return results

    def list_fastems2_usage(self) -> List[Fastems2PalletUsage]:
        if not self._engine:
            return []

        query = text(
            """
            SELECT
                PalletNumber AS pallet_number,
                LatestSnapshotId AS latest_snapshot_id,
                LatestSnapshotTimeUtc AS latest_snapshot_time_utc,
                RoutingMode AS routing_mode,
                Stage AS stage,
                Status AS status,
                ChangeCount24h AS change_count_24h,
                ChangeCount7d AS change_count_7d,
                ChangeCount30d AS change_count_30d,
                ChangeCount90d AS change_count_90d
            FROM [Cedule].[fastems2].[vw_MachinePallet_Usage]
            """
        )

        try:
            with self._engine.connect() as connection:
                rows = connection.execute(query).mappings().all()
        except SQLAlchemyError as exc:
            logger.error("Failed to query Fastems2 pallet usage", exc_info=exc)
            raise DatabaseError("Unable to query Fastems2 pallet usage") from exc

        results: List[Fastems2PalletUsage] = []
        for row in rows:
            pallet_number = _clean_str(row.get("pallet_number")) or ""
            results.append(
                Fastems2PalletUsage(
                    pallet_number=pallet_number,
                    latest_snapshot_id=_safe_int(row.get("latest_snapshot_id")),
                    latest_snapshot_time_utc=_safe_datetime(row.get("latest_snapshot_time_utc")),
                    routing_mode=_clean_str(row.get("routing_mode")),
                    stage=_clean_str(row.get("stage")),
                    status=_clean_str(row.get("status")),
                    change_count_24h=_safe_int(row.get("change_count_24h"), default=0),
                    change_count_7d=_safe_int(row.get("change_count_7d"), default=0),
                    change_count_30d=_safe_int(row.get("change_count_30d"), default=0),
                    change_count_90d=_safe_int(row.get("change_count_90d"), default=0),
                )
            )

        return results


def _clean_str(value: Optional[object]) -> Optional[str]:
    if value is None:
        return None
    text_value = str(value).strip()
    return text_value or None


def _safe_int(value: Optional[object], default: Optional[int] = None) -> Optional[int]:
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_datetime(value: Optional[object]) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())
    if isinstance(value, str):
        cleaned = value.strip()
        if not cleaned:
            return None
        try:
            return datetime.fromisoformat(cleaned)
        except ValueError:
            pass
        for fmt in (
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M:%S.%f",
            "%m/%d/%Y %H:%M:%S",
        ):
            try:
                return datetime.strptime(cleaned, fmt)
            except ValueError:
                continue
    return None

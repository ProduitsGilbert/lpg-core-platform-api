from __future__ import annotations

import datetime as dt
import logging
from typing import List, Optional, Tuple

from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from app.errors import DatabaseError
from app.integrations.cedule_repository import get_cedule_engine

logger = logging.getLogger(__name__)


class CedulePurchasingKpiRepository:
    """Read-only Cedule queries for purchasing KPI endpoints."""

    def __init__(self, engine: Optional[Engine] = None) -> None:
        self._engine = engine or get_cedule_engine()

    @property
    def is_configured(self) -> bool:
        return self._engine is not None

    def list_action_counts_by_category(
        self,
        *,
        start_date: dt.date,
        end_date: dt.date,
    ) -> List[Tuple[str, int]]:
        if not self._engine:
            return []

        query = text(
            """
            SELECT
                COALESCE(NULLIF(LTRIM(RTRIM(action_category)), ''), 'UNKNOWN') AS action_category,
                COUNT_BIG(1) AS updates_count
            FROM [Cedule].[dbo].[Achat_Order_Action_Log]
            WHERE CAST(action_timestamp AS date) BETWEEN :start_date AND :end_date
            GROUP BY COALESCE(NULLIF(LTRIM(RTRIM(action_category)), ''), 'UNKNOWN')
            ORDER BY updates_count DESC, action_category ASC
            """
        )

        try:
            with self._engine.connect() as connection:
                rows = connection.execute(
                    query,
                    {
                        "start_date": start_date.isoformat(),
                        "end_date": end_date.isoformat(),
                    },
                ).mappings().all()
        except SQLAlchemyError as exc:
            logger.error("Failed to query Cedule order action logs", exc_info=exc)
            raise DatabaseError("Unable to query Cedule purchasing action logs") from exc

        return [
            (
                str(row.get("action_category") or "UNKNOWN"),
                int(row.get("updates_count") or 0),
            )
            for row in rows
        ]

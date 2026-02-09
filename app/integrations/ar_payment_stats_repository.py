from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Dict, Iterable, List, Optional

from sqlalchemy import bindparam, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from app.domain.finance.models import AccountsReceivablePaymentStats
from app.errors import DatabaseError
from app.integrations.cedule_repository import get_cedule_engine

logger = logging.getLogger(__name__)


class ArPaymentStatsRepository:
    """Repository for AR payment habit stats stored in Cedule."""

    def __init__(self, engine: Optional[Engine] = None) -> None:
        self._engine = engine or get_cedule_engine()

    @property
    def is_configured(self) -> bool:
        return self._engine is not None

    def get_stats_by_customer_nos(
        self, customer_nos: Iterable[str]
    ) -> Dict[str, AccountsReceivablePaymentStats]:
        if not self._engine:
            return {}
        customer_list = [c for c in customer_nos if c]
        if not customer_list:
            return {}

        query = text(
            """
            SELECT
                customer_no,
                invoice_count,
                avg_days_late,
                median_days_late,
                late_ratio,
                window_start,
                window_end,
                updated_at
            FROM [Cedule].[dbo].[30_COMPTABILITÉ ET FINANCES_AR_Payment_Stats]
            WHERE customer_no IN :customer_nos
            """
        ).bindparams(bindparam("customer_nos", expanding=True))

        try:
            with self._engine.connect() as connection:
                rows = connection.execute(query, {"customer_nos": customer_list}).mappings().all()
                result: Dict[str, AccountsReceivablePaymentStats] = {}
                for row in rows:
                    result[row["customer_no"]] = AccountsReceivablePaymentStats(
                        customer_no=row["customer_no"],
                        invoice_count=int(row["invoice_count"] or 0),
                        avg_days_late=float(row["avg_days_late"]) if row["avg_days_late"] is not None else None,
                        median_days_late=float(row["median_days_late"])
                        if row["median_days_late"] is not None
                        else None,
                        late_ratio=float(row["late_ratio"]) if row["late_ratio"] is not None else None,
                        window_start=row["window_start"],
                        window_end=row["window_end"],
                        updated_at=row["updated_at"],
                    )
                return result
        except SQLAlchemyError as exc:
            message = str(exc).lower()
            if "finance_ar_payment_stats" in message and "invalid object name" in message:
                logger.warning(
                    "AR payment stats table missing; returning empty stats",
                    exc_info=exc,
                )
                return {}
            logger.error("Failed to read AR payment stats", exc_info=exc)
            raise DatabaseError("Unable to fetch AR payment stats") from exc

    def upsert_stats(self, stats: Iterable[AccountsReceivablePaymentStats]) -> None:
        if not self._engine:
            raise DatabaseError("Database not configured")
        payload: List[Dict[str, object]] = []
        timestamp = datetime.utcnow()
        for stat in stats:
            payload.append(
                {
                    "customer_no": stat.customer_no,
                    "invoice_count": stat.invoice_count,
                    "avg_days_late": stat.avg_days_late,
                    "median_days_late": stat.median_days_late,
                    "late_ratio": stat.late_ratio,
                    "window_start": stat.window_start,
                    "window_end": stat.window_end,
                    "updated_at": stat.updated_at or timestamp,
                }
            )

        if not payload:
            return

        query = text(
            """
            MERGE [Cedule].[dbo].[30_COMPTABILITÉ ET FINANCES_AR_Payment_Stats] AS target
            USING (VALUES
                (:customer_no, :invoice_count, :avg_days_late, :median_days_late,
                 :late_ratio, :window_start, :window_end, :updated_at)
            ) AS source (
                customer_no, invoice_count, avg_days_late, median_days_late,
                late_ratio, window_start, window_end, updated_at
            )
            ON target.customer_no = source.customer_no
            WHEN MATCHED THEN
                UPDATE SET
                    invoice_count = source.invoice_count,
                    avg_days_late = source.avg_days_late,
                    median_days_late = source.median_days_late,
                    late_ratio = source.late_ratio,
                    window_start = source.window_start,
                    window_end = source.window_end,
                    updated_at = source.updated_at
            WHEN NOT MATCHED THEN
                INSERT (customer_no, invoice_count, avg_days_late, median_days_late,
                        late_ratio, window_start, window_end, updated_at)
                VALUES (source.customer_no, source.invoice_count, source.avg_days_late,
                        source.median_days_late, source.late_ratio, source.window_start,
                        source.window_end, source.updated_at);
            """
        )

        try:
            with self._engine.begin() as connection:
                connection.execute(query, payload)
        except SQLAlchemyError as exc:
            logger.error("Failed to upsert AR payment stats", exc_info=exc)
            raise DatabaseError("Unable to persist AR payment stats") from exc

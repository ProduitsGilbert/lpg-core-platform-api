"""
Lightweight repository for Cedule mill test certificate data.

This module provides read-only access to the ``Achat_Mill_Test_Certificate`` table
so domain services (e.g., tariff calculator) can enrich responses with melt & pour
information without duplicating SQL/connection boilerplate.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from typing import Optional
import logging

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import QueuePool
from urllib.parse import quote_plus

from app.errors import DatabaseError
from app.settings import settings

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class MillTestCertificate:
    """Single mill test certificate row for a part number."""

    part_number: str
    country_of_melt_and_pour: Optional[str]
    country_of_manufacture: Optional[str]
    material_description: Optional[str]
    line_total_weight: Optional[float]
    weight_unit: Optional[str]
    certification_date: Optional[datetime]


def _build_cedule_url() -> Optional[str]:
    """Construct a SQLAlchemy-compatible MSSQL DSN for the Cedule database."""
    if settings.cedule_db_dsn:
        return settings.cedule_db_dsn.strip()

    required = (
        settings.cedule_sql_server,
        settings.cedule_sql_database,
        settings.cedule_sql_username,
        settings.cedule_sql_password,
    )
    if not all(required):
        return None

    driver = (settings.cedule_sql_driver or "ODBC Driver 18 for SQL Server").replace(" ", "+")
    user = quote_plus(settings.cedule_sql_username or "")
    password = quote_plus(settings.cedule_sql_password or "")
    server = settings.cedule_sql_server or ""
    database = settings.cedule_sql_database or ""

    return (
        f"mssql+pyodbc://{user}:{password}@{server}/{database}"
        f"?driver={driver}&TrustServerCertificate=yes"
    )


@lru_cache(maxsize=1)
def _cached_engine(url: str) -> Engine:
    """Create a pooled SQLAlchemy engine for Cedule."""
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


def get_cedule_engine() -> Optional[Engine]:
    """Return a shared Cedule engine if the database is configured."""
    url = _build_cedule_url()
    if not url:
        logger.debug("Cedule database is not configured; melt/pour data unavailable.")
        return None
    return _cached_engine(url)


class MillTestCertificateRepository:
    """Simple repository for mill test certificates."""

    def __init__(self, engine: Optional[Engine] = None) -> None:
        self._engine = engine or get_cedule_engine()

    @property
    def is_configured(self) -> bool:
        """Return True when the repository can query the Cedule database."""
        return self._engine is not None

    def get_latest_certificate(self, part_number: str) -> Optional[MillTestCertificate]:
        """Return the most recent certificate for the provided part number."""
        if not part_number or not self._engine:
            return None

        query = text(
            """
            SELECT TOP 1
                id,
                part_number,
                country_of_melt_and_pour,
                country_of_manufacture,
                material_description,
                line_total_weight,
                weight_unit,
                certification_date,
                created_at
            FROM [Cedule].[dbo].[Achat_Mill_Test_Certificate]
            WHERE part_number = :part_number
            ORDER BY
                CASE WHEN certification_date = '0001-01-01' THEN NULL ELSE certification_date END DESC,
                created_at DESC
            """
        )

        try:
            with self._engine.connect() as connection:
                row = connection.execute(query, {"part_number": part_number}).mappings().first()
        except SQLAlchemyError as exc:
            logger.error(
                "Failed to query Cedule mill test certificates",
                exc_info=exc,
                extra={"part_number": part_number},
            )
            raise DatabaseError("Unable to query mill test certificates") from exc

        if not row:
            return None

        return MillTestCertificate(
            part_number=row.get("part_number", "").strip(),
            country_of_melt_and_pour=_clean_str(row.get("country_of_melt_and_pour")),
            country_of_manufacture=_clean_str(row.get("country_of_manufacture")),
            material_description=_clean_str(row.get("material_description")),
            line_total_weight=_safe_float(row.get("line_total_weight")),
            weight_unit=_clean_str(row.get("weight_unit")),
            certification_date=row.get("certification_date"),
        )


def _clean_str(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _safe_float(value: Optional[object]) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None

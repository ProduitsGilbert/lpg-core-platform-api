"""
Read-only repository for Windchill KPI queries.

Executes predefined SQL statements to retrieve drawing creation/modification
counts per user. Uses MSSQL via SQLAlchemy + pyodbc.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import List, Optional
import logging

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import QueuePool
from urllib.parse import quote_plus

from app.errors import DatabaseError
from app.settings import settings

logger = logging.getLogger(__name__)


# SQL statements are kept inline to match the reference .sql files in docs/.
SQL_CREATED_DRAWINGS_PER_USER = text(
    """
    SELECT
        COUNT(DISTINCT EPMM.idA2A2) AS Count,
        CONVERT(char(10), CAST(EPMM.createStampA2 AS date), 23) AS CreationDate,
        CUSR.fullName AS CreatedBy
    FROM pdmpl90.EPMDocumentMaster AS EPMM
        INNER JOIN pdmpl90.EPMDocument AS EPMD ON EPMD.idA3masterReference = EPMM.idA2A2
        LEFT JOIN pdmpl90.WTUser AS CUSR ON CUSR.idA2A2 = EPMD.idA3D2iterationInfo
    WHERE EPMM.docType = 'CADASSEMBLY'
        AND DATEDIFF(DAY, EPMD.modifyStampA2, GETDATE()) < 365
        AND EPMM.documentNumber LIKE '%-[67][0-9][0-9].%'
        AND EPMM.createStampA2 = EPMD.createStampA2
    GROUP BY
        CAST(EPMM.createStampA2 AS date),
        CUSR.fullName
    ORDER BY CAST(EPMM.createStampA2 AS date) DESC
    """
)

SQL_MODIFIED_DRAWINGS_PER_USER = text(
    """
    SELECT
        COUNT(DISTINCT EPMM.idA2A2) AS Count,
        CONVERT(char(10), CAST(EPMD.modifyStampA2 AS date), 23) AS LastModified,
        MUSR.fullName AS ModifiedBy
    FROM pdmpl90.EPMDocumentMaster AS EPMM
        INNER JOIN pdmpl90.EPMDocument AS EPMD ON EPMD.idA3masterReference = EPMM.idA2A2
        LEFT JOIN pdmpl90.WTUser AS MUSR ON MUSR.idA2A2 = EPMD.idA3B2iterationInfo
    WHERE EPMM.docType = 'CADASSEMBLY'
        AND DATEDIFF(DAY, EPMD.modifyStampA2, GETDATE()) < 365
        AND EPMD.statecheckoutInfo = 'c/i'
        AND EPMM.documentNumber LIKE '%-[67][0-9][0-9].%'
        AND CAST(EPMD.modifyStampA2 AS date) <> CAST(EPMM.createStampA2 AS date)
    GROUP BY
        CAST(EPMD.modifyStampA2 AS date),
        MUSR.fullName
    ORDER BY CAST(EPMD.modifyStampA2 AS date) DESC
    """
)


def _build_windchill_url() -> Optional[str]:
    """Construct a SQLAlchemy-compatible MSSQL DSN for Windchill analytics."""
    if settings.windchill_db_dsn:
        return settings.windchill_db_dsn.strip()

    required = (
        settings.windchill_sql_server,
        settings.windchill_sql_database,
        settings.windchill_sql_username,
        settings.windchill_sql_password,
    )
    if not all(required):
        return None

    driver = (settings.windchill_sql_driver or "ODBC Driver 18 for SQL Server").replace(" ", "+")
    user = quote_plus(settings.windchill_sql_username or "")
    password = quote_plus(settings.windchill_sql_password or "")
    server = settings.windchill_sql_server or ""
    database = settings.windchill_sql_database or ""

    return (
        f"mssql+pyodbc://{user}:{password}@{server}/{database}"
        f"?driver={driver}&TrustServerCertificate=yes"
    )


@lru_cache(maxsize=1)
def _cached_engine(url: str) -> Engine:
    """Create a pooled SQLAlchemy engine for Windchill."""
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


def get_windchill_engine() -> Optional[Engine]:
    """Return a shared Windchill engine if the database is configured."""
    url = _build_windchill_url()
    if not url:
        logger.debug("Windchill database is not configured; KPI queries unavailable.")
        return None
    return _cached_engine(url)


@dataclass(slots=True)
class WindchillCreatedDrawingsPerUser:
    count: int
    creation_date: str
    created_by: str


@dataclass(slots=True)
class WindchillModifiedDrawingsPerUser:
    count: int
    last_modified: str
    modified_by: str


class WindchillRepository:
    """Repository executing Windchill KPI queries."""

    def __init__(self, engine: Optional[Engine] = None) -> None:
        self._engine = engine or get_windchill_engine()

    @property
    def is_configured(self) -> bool:
        return self._engine is not None

    def list_created_drawings_per_user(self) -> List[WindchillCreatedDrawingsPerUser]:
        if not self._engine:
            raise DatabaseError("Windchill SQL connection is not configured")
        try:
            with self._engine.connect() as connection:
                rows = connection.execute(SQL_CREATED_DRAWINGS_PER_USER).mappings().all()
        except SQLAlchemyError as exc:
            logger.error("Failed to execute Windchill created drawings KPI", exc_info=exc)
            raise DatabaseError("Unable to query Windchill KPI (created drawings)") from exc

        return [
            WindchillCreatedDrawingsPerUser(
                count=int(row.get("Count", 0)),
                creation_date=str(row.get("CreationDate") or ""),
                created_by=str(row.get("CreatedBy") or "").strip(),
            )
            for row in rows
        ]

    def list_modified_drawings_per_user(self) -> List[WindchillModifiedDrawingsPerUser]:
        if not self._engine:
            raise DatabaseError("Windchill SQL connection is not configured")
        try:
            with self._engine.connect() as connection:
                rows = connection.execute(SQL_MODIFIED_DRAWINGS_PER_USER).mappings().all()
        except SQLAlchemyError as exc:
            logger.error("Failed to execute Windchill modified drawings KPI", exc_info=exc)
            raise DatabaseError("Unable to query Windchill KPI (modified drawings)") from exc

        return [
            WindchillModifiedDrawingsPerUser(
                count=int(row.get("Count", 0)),
                last_modified=str(row.get("LastModified") or ""),
                modified_by=str(row.get("ModifiedBy") or "").strip(),
            )
            for row in rows
        ]

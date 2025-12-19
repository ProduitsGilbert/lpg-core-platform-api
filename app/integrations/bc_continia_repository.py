"""
Repository for Continia (CDC) invoice data stored in Business Central SQL tables.

This is used to extract OCR invoice values like AMOUNTINCLVAT/DOCDATE/DUEDATE
from the CDC tables, since the OData Continia endpoint does not expose amounts.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from functools import lru_cache
from typing import Dict, List, Optional, Sequence, Tuple
import logging

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import QueuePool
from urllib.parse import quote_plus

from app.errors import DatabaseError
from app.settings import settings

logger = logging.getLogger(__name__)


# Default table names (as provided). These can be overridden via env if needed later.
CDC_DOCUMENT_TABLE = (
    "[Gilbert-Tech$CDC Document$6da8dd2f-e698-461f-9147-8e404244dd85]"
)
CDC_DOCUMENT_VALUE_TABLE = (
    "[Gilbert-Tech$CDC Document Value$6da8dd2f-e698-461f-9147-8e404244dd85]"
)
VENDOR_TABLE = "[Gilbert-Tech$Vendor$437dbf0e-84ff-417a-965d-ed2bb9650972]"
PAYMENT_TERMS_TABLE = (
    "[Gilbert-Tech$Payment Terms$437dbf0e-84ff-417a-965d-ed2bb9650972]"
)


@dataclass(slots=True)
class ContiniaDocument:
    document_no: str
    vendor_code: Optional[str]
    vendor_name: Optional[str]
    status: Optional[str]
    ok: Optional[bool]
    system_created_at: Optional[datetime]


@dataclass(slots=True)
class ContiniaValues:
    document_no: str
    text_values: Dict[str, str]
    decimal_values: Dict[str, Decimal]
    date_values: Dict[str, date]


def _build_bc_sql_url() -> Optional[str]:
    if not settings.bc_sql_server or not settings.bc_sql_database:
        return None
    if not settings.bc_sql_username or not settings.bc_sql_password:
        return None

    driver = (settings.bc_sql_driver or "ODBC Driver 18 for SQL Server").replace(" ", "+")
    user = quote_plus(settings.bc_sql_username or "")
    password = quote_plus(settings.bc_sql_password or "")
    server = settings.bc_sql_server or ""
    database = settings.bc_sql_database or ""
    return (
        f"mssql+pyodbc://{user}:{password}@{server}/{database}"
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


def get_bc_sql_engine() -> Optional[Engine]:
    url = _build_bc_sql_url()
    if not url:
        return None
    return _cached_engine(url)


class BusinessCentralContiniaRepository:
    """Read-only repository for Continia CDC data stored in BC SQL tables."""

    def __init__(self, engine: Optional[Engine] = None) -> None:
        self._engine = engine or get_bc_sql_engine()

    @property
    def is_configured(self) -> bool:
        return self._engine is not None

    def list_purchase_documents(
        self, *, created_from: date, created_to: date
    ) -> List[ContiniaDocument]:
        """
        List Continia purchase documents created in [created_from, created_to] (inclusive).
        """
        if not self._engine:
            raise DatabaseError("Business Central SQL connection is not configured")

        query = text(
            f"""
            SELECT
                CD.No_ as DocumentNo,
                CD.[Source Record No_] as VendorCode,
                CD.Status,
                CD.OK,
                CD.[$systemCreatedAt] as SystemCreatedAt,
                V.Name as VendorName
            FROM {CDC_DOCUMENT_TABLE} CD
            LEFT JOIN {VENDOR_TABLE} V
                ON CD.[Source Record No_] = V.No_
            WHERE
                CD.[Document Category Code] = 'PURCHASE'
                AND CD.OK = 1
                AND CAST(CD.[$systemCreatedAt] AS DATE) >= :created_from
                AND CAST(CD.[$systemCreatedAt] AS DATE) <= :created_to
            """
        )

        try:
            with self._engine.connect() as connection:
                rows = connection.execute(
                    query,
                    {
                        "created_from": created_from.isoformat(),
                        "created_to": created_to.isoformat(),
                    },
                ).mappings().all()
        except SQLAlchemyError as exc:
            logger.error("Failed to query CDC Document table", exc_info=exc)
            raise DatabaseError("Unable to query Continia CDC documents") from exc

        docs: List[ContiniaDocument] = []
        for row in rows:
            docs.append(
                ContiniaDocument(
                    document_no=str(row.get("DocumentNo") or "").strip(),
                    vendor_code=_clean_str(row.get("VendorCode")),
                    vendor_name=_clean_str(row.get("VendorName")),
                    status=_clean_str(row.get("Status")),
                    ok=row.get("OK"),
                    system_created_at=row.get("SystemCreatedAt"),
                )
            )
        return [d for d in docs if d.document_no]

    def list_purchase_documents_by_due_date(
        self, *, due_from: date, due_to: date
    ) -> List[ContiniaDocument]:
        """
        List Continia purchase documents (OK=1) whose CDC DUEDATE is within [due_from, due_to] inclusive.

        This avoids any lookback window because we filter directly on the Due Date.
        """
        if not self._engine:
            raise DatabaseError("Business Central SQL connection is not configured")

        query = text(
            f"""
            SELECT DISTINCT
                CD.No_ as DocumentNo,
                CD.[Source Record No_] as VendorCode,
                CD.Status,
                CD.OK,
                CD.[$systemCreatedAt] as SystemCreatedAt,
                V.Name as VendorName
            FROM {CDC_DOCUMENT_TABLE} CD
            INNER JOIN {CDC_DOCUMENT_VALUE_TABLE} DV
                ON DV.[Document No_] = CD.No_
            LEFT JOIN {VENDOR_TABLE} V
                ON CD.[Source Record No_] = V.No_
            WHERE
                CD.[Document Category Code] = 'PURCHASE'
                AND CD.OK = 1
                AND DV.[Is Valid] = 1
                AND UPPER(DV.Code) = 'DUEDATE'
                AND CAST(DV.[Value (Date)] AS DATE) >= :due_from
                AND CAST(DV.[Value (Date)] AS DATE) <= :due_to
            """
        )

        try:
            with self._engine.connect() as connection:
                rows = connection.execute(
                    query,
                    {
                        "due_from": due_from.isoformat(),
                        "due_to": due_to.isoformat(),
                    },
                ).mappings().all()
        except SQLAlchemyError as exc:
            logger.error("Failed to query Continia documents by DUEDATE", exc_info=exc)
            raise DatabaseError("Unable to query Continia documents by due date") from exc

        docs: List[ContiniaDocument] = []
        for row in rows:
            docs.append(
                ContiniaDocument(
                    document_no=str(row.get("DocumentNo") or "").strip(),
                    vendor_code=_clean_str(row.get("VendorCode")),
                    vendor_name=_clean_str(row.get("VendorName")),
                    status=_clean_str(row.get("Status")),
                    ok=row.get("OK"),
                    system_created_at=row.get("SystemCreatedAt"),
                )
            )
        return [d for d in docs if d.document_no]

    def get_document_values_batch(
        self, document_nos: Sequence[str]
    ) -> Dict[str, ContiniaValues]:
        """
        Fetch CDC Document Values for a batch of document numbers.
        Returns mapping: document_no -> ContiniaValues.
        """
        if not self._engine:
            raise DatabaseError("Business Central SQL connection is not configured")
        if not document_nos:
            return {}

        # Chunk to avoid SQL Server parameter limits
        chunk_size = 500
        result: Dict[str, ContiniaValues] = {}

        for i in range(0, len(document_nos), chunk_size):
            chunk = [str(x) for x in document_nos[i : i + chunk_size]]
            placeholders = ", ".join([f":p{i}_{j}" for j in range(len(chunk))])
            params = {f"p{i}_{j}": chunk[j] for j in range(len(chunk))}

            query = text(
                f"""
                SELECT
                    [Document No_] as DocumentNo,
                    Code,
                    [Value (Text)] as TextValue,
                    [Value (Decimal)] as DecimalValue,
                    [Value (Date)] as DateValue
                FROM {CDC_DOCUMENT_VALUE_TABLE}
                WHERE
                    [Document No_] IN ({placeholders})
                    AND [Is Valid] = 1
                """
            )

            try:
                with self._engine.connect() as connection:
                    rows = connection.execute(query, params).mappings().all()
            except SQLAlchemyError as exc:
                logger.error("Failed to query CDC Document Value table", exc_info=exc)
                raise DatabaseError("Unable to query Continia CDC values") from exc

            for row in rows:
                doc_no = str(row.get("DocumentNo") or "").strip()
                code = str(row.get("Code") or "").strip().upper()
                if not doc_no or not code:
                    continue
                if doc_no not in result:
                    result[doc_no] = ContiniaValues(
                        document_no=doc_no,
                        text_values={},
                        decimal_values={},
                        date_values={},
                    )

                tv = row.get("TextValue")
                dv = row.get("DecimalValue")
                datev = row.get("DateValue")

                if tv not in (None, ""):
                    result[doc_no].text_values[code] = str(tv).strip()
                if dv is not None:
                    try:
                        result[doc_no].decimal_values[code] = Decimal(str(dv))
                    except Exception:
                        pass
                if datev is not None and isinstance(datev, (date, datetime)):
                    if isinstance(datev, datetime):
                        result[doc_no].date_values[code] = datev.date()
                    else:
                        result[doc_no].date_values[code] = datev

        return result


def _clean_str(value: Optional[object]) -> Optional[str]:
    if value is None:
        return None
    s = str(value).strip()
    return s or None



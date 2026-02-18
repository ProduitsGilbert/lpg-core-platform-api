from __future__ import annotations

import datetime as dt
import logging
from typing import Any, Optional
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from app.errors import DatabaseError
from app.integrations.cedule_repository import get_cedule_engine

logger = logging.getLogger(__name__)


class CeduleProductionCostingRepository:
    """Persistence for ERP production costing snapshots in Cedule."""

    def __init__(self, engine: Optional[Engine] = None) -> None:
        self._engine = engine or get_cedule_engine()
        self._schema_checked = False

    @property
    def is_configured(self) -> bool:
        return self._engine is not None

    def ensure_schema(self) -> None:
        """Validate snapshot schema availability without requiring DDL permissions."""
        if self._schema_checked or not self._engine:
            return

        required_tables = (
            "[Cedule].[dbo].[30_COMPTABILITÉ ET FINANCES_COST_SHARE_SCANS]",
            "[Cedule].[dbo].[30_COMPTABILITÉ ET FINANCES_COST_SHARE_STATE]",
            "[Cedule].[dbo].[30_COMPTABILITÉ ET FINANCES_COST_SHARE_SNAPSHOT]",
        )
        missing = self._find_missing_tables(required_tables)
        if not missing:
            self._schema_checked = True
            return

        missing_str = ", ".join(missing)
        logger.error("Missing production costing snapshot tables: %s", missing_str)
        raise DatabaseError(
            "Costing snapshot schema is missing required tables. "
            "Run docs/erp_production_costing_snapshot_schema.sql and retry. "
            f"Missing: {missing_str}"
        )

    def _find_missing_tables(self, required_tables: tuple[str, ...]) -> list[str]:
        if not self._engine:
            raise DatabaseError("Cedule database not configured")

        missing: list[str] = []
        stmt = text("SELECT OBJECT_ID(:table_name, 'U') AS object_id")
        try:
            with self._engine.connect() as conn:
                for table_name in required_tables:
                    row = conn.execute(stmt, {"table_name": table_name}).mappings().first()
                    if not row or row.get("object_id") is None:
                        missing.append(table_name)
        except SQLAlchemyError as exc:
            logger.error("Failed to validate production costing snapshot schema", exc_info=exc)
            raise DatabaseError("Unable to validate costing snapshot schema") from exc
        return missing

    def ensure_schema_legacy_bootstrap(self) -> None:
        """Legacy DDL bootstrap kept for reference; not used by runtime path."""
        if not self._engine:
            raise DatabaseError("Cedule database not configured")

        statements = [
            """
            IF OBJECT_ID('[Cedule].[dbo].[30_COMPTABILITÉ ET FINANCES_COST_SHARE_SCANS]', 'U') IS NULL
            BEGIN
                CREATE TABLE [Cedule].[dbo].[30_COMPTABILITÉ ET FINANCES_COST_SHARE_SCANS] (
                    [scan_id] UNIQUEIDENTIFIER NOT NULL,
                    [scan_started_at] DATETIME2(3) NOT NULL CONSTRAINT [DF_EPCScans_started] DEFAULT SYSUTCDATETIME(),
                    [scan_finished_at] DATETIME2(3) NULL,
                    [scan_mode] NVARCHAR(10) NOT NULL,
                    [trigger_source] NVARCHAR(30) NOT NULL,
                    [status] NVARCHAR(20) NOT NULL,
                    [since_modified_at] DATETIME2(3) NULL,
                    [until_modified_at] DATETIME2(3) NULL,
                    [routing_headers_count] INT NOT NULL CONSTRAINT [DF_EPCScans_rh] DEFAULT (0),
                    [bom_headers_count] INT NOT NULL CONSTRAINT [DF_EPCScans_bh] DEFAULT (0),
                    [routing_lines_count] INT NOT NULL CONSTRAINT [DF_EPCScans_rl] DEFAULT (0),
                    [bom_lines_count] INT NOT NULL CONSTRAINT [DF_EPCScans_bl] DEFAULT (0),
                    [error_message] NVARCHAR(MAX) NULL,

                    CONSTRAINT [PK_EPCScans] PRIMARY KEY ([scan_id]),
                    CONSTRAINT [CK_EPCScans_mode] CHECK ([scan_mode] IN ('full', 'delta')),
                    CONSTRAINT [CK_EPCScans_status] CHECK ([status] IN ('running', 'success', 'failed'))
                )
            END
            """,
            """
            IF OBJECT_ID('[Cedule].[dbo].[30_COMPTABILITÉ ET FINANCES_COST_SHARE_STATE]', 'U') IS NULL
            BEGIN
                CREATE TABLE [Cedule].[dbo].[30_COMPTABILITÉ ET FINANCES_COST_SHARE_STATE] (
                    [source_type] NVARCHAR(20) NOT NULL,
                    [last_successful_modified_at] DATETIME2(3) NULL,
                    [last_scan_id] UNIQUEIDENTIFIER NULL,
                    [updated_at] DATETIME2(3) NOT NULL CONSTRAINT [DF_EPCSState_updated] DEFAULT SYSUTCDATETIME(),

                    CONSTRAINT [PK_EPCSState] PRIMARY KEY ([source_type]),
                    CONSTRAINT [CK_EPCSState_source] CHECK ([source_type] IN ('routing', 'bom')),
                    CONSTRAINT [FK_EPCSState_scan] FOREIGN KEY ([last_scan_id])
                        REFERENCES [Cedule].[dbo].[30_COMPTABILITÉ ET FINANCES_COST_SHARE_SCANS]([scan_id])
                )
            END
            """,
            """
            IF OBJECT_ID('[Cedule].[dbo].[30_COMPTABILITÉ ET FINANCES_COST_SHARE_SNAPSHOT]', 'U') IS NULL
            BEGIN
                CREATE TABLE [Cedule].[dbo].[30_COMPTABILITÉ ET FINANCES_COST_SHARE_SNAPSHOT] (
                    [snapshot_id] BIGINT IDENTITY(1,1) NOT NULL,
                    [scan_id] UNIQUEIDENTIFIER NOT NULL,
                    [source_type] NVARCHAR(20) NOT NULL,
                    [source_no] NVARCHAR(100) NOT NULL,
                    [source_base_item_no] NVARCHAR(50) NOT NULL,
                    [header_last_modified_at] DATETIME2(3) NULL,
                    [line_key] NVARCHAR(200) NULL,
                    [row_json] NVARCHAR(MAX) NOT NULL,
                    [created_at] DATETIME2(3) NOT NULL CONSTRAINT [DF_EPCSLine_created] DEFAULT SYSUTCDATETIME(),

                    CONSTRAINT [PK_EPCSLine] PRIMARY KEY ([snapshot_id]),
                    CONSTRAINT [FK_EPCSLine_scan] FOREIGN KEY ([scan_id])
                        REFERENCES [Cedule].[dbo].[30_COMPTABILITÉ ET FINANCES_COST_SHARE_SCANS]([scan_id]) ON DELETE CASCADE,
                    CONSTRAINT [CK_EPCSLine_source] CHECK ([source_type] IN ('routing', 'bom'))
                )
            END
            """,
            """
            IF NOT EXISTS (
                SELECT 1
                FROM sys.indexes
                WHERE name = 'IX_EPCSLine_item_lookup'
                  AND object_id = OBJECT_ID('[Cedule].[dbo].[30_COMPTABILITÉ ET FINANCES_COST_SHARE_SNAPSHOT]')
            )
            BEGIN
                CREATE INDEX [IX_EPCSLine_item_lookup]
                    ON [Cedule].[dbo].[30_COMPTABILITÉ ET FINANCES_COST_SHARE_SNAPSHOT]([source_base_item_no], [source_type], [source_no], [scan_id])
            END
            """,
            """
            IF NOT EXISTS (
                SELECT 1
                FROM sys.indexes
                WHERE name = 'IX_EPCSLine_scan_lookup'
                  AND object_id = OBJECT_ID('[Cedule].[dbo].[30_COMPTABILITÉ ET FINANCES_COST_SHARE_SNAPSHOT]')
            )
            BEGIN
                CREATE INDEX [IX_EPCSLine_scan_lookup]
                    ON [Cedule].[dbo].[30_COMPTABILITÉ ET FINANCES_COST_SHARE_SNAPSHOT]([scan_id], [source_type], [source_no])
            END
            """,
            """
            IF NOT EXISTS (
                SELECT 1
                FROM sys.indexes
                WHERE name = 'IX_EPCScans_started'
                  AND object_id = OBJECT_ID('[Cedule].[dbo].[30_COMPTABILITÉ ET FINANCES_COST_SHARE_SCANS]')
            )
            BEGIN
                CREATE INDEX [IX_EPCScans_started]
                    ON [Cedule].[dbo].[30_COMPTABILITÉ ET FINANCES_COST_SHARE_SCANS]([scan_started_at] DESC)
            END
            """,
        ]

        try:
            with self._engine.begin() as conn:
                for stmt in statements:
                    conn.execute(text(stmt))
            self._schema_checked = True
        except SQLAlchemyError as exc:
            logger.error("Failed to initialize production costing snapshot schema", exc_info=exc)
            raise DatabaseError(
                "Unable to initialize costing snapshot schema. "
                "Run docs/erp_production_costing_snapshot_schema.sql and retry."
            ) from exc

    def create_scan(
        self,
        *,
        scan_mode: str,
        trigger_source: str,
        since_modified_at: Optional[dt.datetime],
    ) -> UUID:
        if not self._engine:
            raise DatabaseError("Cedule database not configured")

        scan_id = uuid4()
        stmt = text(
            """
            INSERT INTO [Cedule].[dbo].[30_COMPTABILITÉ ET FINANCES_COST_SHARE_SCANS]
            (
                scan_id,
                scan_mode,
                trigger_source,
                status,
                since_modified_at
            )
            VALUES
            (
                :scan_id,
                :scan_mode,
                :trigger_source,
                'running',
                :since_modified_at
            )
            """
        )

        try:
            with self._engine.begin() as conn:
                conn.execute(
                    stmt,
                    {
                        "scan_id": str(scan_id),
                        "scan_mode": scan_mode,
                        "trigger_source": trigger_source,
                        "since_modified_at": since_modified_at,
                    },
                )
        except SQLAlchemyError as exc:
            logger.error("Failed to create costing scan", exc_info=exc)
            raise DatabaseError("Unable to create costing scan") from exc
        return scan_id

    def complete_scan(
        self,
        *,
        scan_id: UUID,
        status: str,
        until_modified_at: Optional[dt.datetime],
        routing_headers_count: int,
        bom_headers_count: int,
        routing_lines_count: int,
        bom_lines_count: int,
        error_message: Optional[str] = None,
    ) -> None:
        if not self._engine:
            raise DatabaseError("Cedule database not configured")

        stmt = text(
            """
            UPDATE [Cedule].[dbo].[30_COMPTABILITÉ ET FINANCES_COST_SHARE_SCANS]
            SET
                scan_finished_at = SYSUTCDATETIME(),
                status = :status,
                until_modified_at = :until_modified_at,
                routing_headers_count = :routing_headers_count,
                bom_headers_count = :bom_headers_count,
                routing_lines_count = :routing_lines_count,
                bom_lines_count = :bom_lines_count,
                error_message = :error_message
            WHERE scan_id = :scan_id
            """
        )

        try:
            with self._engine.begin() as conn:
                conn.execute(
                    stmt,
                    {
                        "scan_id": str(scan_id),
                        "status": status,
                        "until_modified_at": until_modified_at,
                        "routing_headers_count": int(routing_headers_count),
                        "bom_headers_count": int(bom_headers_count),
                        "routing_lines_count": int(routing_lines_count),
                        "bom_lines_count": int(bom_lines_count),
                        "error_message": error_message,
                    },
                )
        except SQLAlchemyError as exc:
            logger.error("Failed to complete costing scan", exc_info=exc)
            raise DatabaseError("Unable to finalize costing scan") from exc

    def get_scan(self, scan_id: UUID) -> Optional[dict[str, Any]]:
        if not self._engine:
            raise DatabaseError("Cedule database not configured")

        stmt = text(
            """
            SELECT
                scan_id,
                scan_started_at,
                scan_finished_at,
                scan_mode,
                trigger_source,
                status,
                since_modified_at,
                until_modified_at,
                routing_headers_count,
                bom_headers_count,
                routing_lines_count,
                bom_lines_count,
                error_message
            FROM [Cedule].[dbo].[30_COMPTABILITÉ ET FINANCES_COST_SHARE_SCANS]
            WHERE scan_id = :scan_id
            """
        )

        try:
            with self._engine.connect() as conn:
                row = conn.execute(stmt, {"scan_id": str(scan_id)}).mappings().first()
        except SQLAlchemyError as exc:
            logger.error("Failed to fetch costing scan", exc_info=exc)
            raise DatabaseError("Unable to fetch costing scan") from exc

        return dict(row) if row else None

    def get_source_last_modified(self, source_type: str) -> Optional[dt.datetime]:
        if not self._engine:
            raise DatabaseError("Cedule database not configured")

        stmt = text(
            """
            SELECT last_successful_modified_at
            FROM [Cedule].[dbo].[30_COMPTABILITÉ ET FINANCES_COST_SHARE_STATE]
            WHERE source_type = :source_type
            """
        )

        try:
            with self._engine.connect() as conn:
                row = conn.execute(stmt, {"source_type": source_type}).mappings().first()
        except SQLAlchemyError as exc:
            logger.error("Failed to fetch costing source state", exc_info=exc)
            raise DatabaseError("Unable to fetch costing source state") from exc

        if not row:
            return None
        return row.get("last_successful_modified_at")

    def upsert_source_state(
        self,
        *,
        source_type: str,
        last_successful_modified_at: Optional[dt.datetime],
        last_scan_id: UUID,
    ) -> None:
        if not self._engine:
            raise DatabaseError("Cedule database not configured")

        stmt = text(
            """
            MERGE [Cedule].[dbo].[30_COMPTABILITÉ ET FINANCES_COST_SHARE_STATE] AS target
            USING (SELECT :source_type AS source_type) AS source
                ON target.source_type = source.source_type
            WHEN MATCHED THEN
                UPDATE SET
                    target.last_successful_modified_at = :last_successful_modified_at,
                    target.last_scan_id = :last_scan_id,
                    target.updated_at = SYSUTCDATETIME()
            WHEN NOT MATCHED THEN
                INSERT (source_type, last_successful_modified_at, last_scan_id)
                VALUES (:source_type, :last_successful_modified_at, :last_scan_id);
            """
        )

        try:
            with self._engine.begin() as conn:
                conn.execute(
                    stmt,
                    {
                        "source_type": source_type,
                        "last_successful_modified_at": last_successful_modified_at,
                        "last_scan_id": str(last_scan_id),
                    },
                )
        except SQLAlchemyError as exc:
            logger.error("Failed to upsert costing source state", exc_info=exc)
            raise DatabaseError("Unable to persist costing source state") from exc

    def insert_line_snapshots(self, rows: list[dict[str, Any]]) -> int:
        if not rows:
            return 0
        if not self._engine:
            raise DatabaseError("Cedule database not configured")

        stmt = text(
            """
            INSERT INTO [Cedule].[dbo].[30_COMPTABILITÉ ET FINANCES_COST_SHARE_SNAPSHOT]
            (
                scan_id,
                source_type,
                source_no,
                source_base_item_no,
                header_last_modified_at,
                line_key,
                row_json
            )
            VALUES
            (
                :scan_id,
                :source_type,
                :source_no,
                :source_base_item_no,
                :header_last_modified_at,
                :line_key,
                :row_json
            )
            """
        )

        try:
            with self._engine.begin() as conn:
                conn.execute(stmt, rows)
        except SQLAlchemyError as exc:
            logger.error("Failed to insert costing line snapshots", exc_info=exc)
            raise DatabaseError("Unable to persist costing line snapshots") from exc
        return len(rows)

    def list_item_snapshot_rows(
        self,
        *,
        base_item_no: str,
        latest_only: bool,
        include_lines: bool,
    ) -> list[dict[str, Any]]:
        if not self._engine:
            raise DatabaseError("Cedule database not configured")

        row_json_select = "ls.row_json" if include_lines else "CAST(NULL AS NVARCHAR(MAX)) AS row_json"
        if latest_only:
            stmt = text(
                f"""
                WITH ranked AS (
                    SELECT
                        ls.snapshot_id,
                        ls.scan_id,
                        ls.source_type,
                        ls.source_no,
                        ls.source_base_item_no,
                        ls.header_last_modified_at,
                        ls.line_key,
                        {row_json_select},
                        sc.scan_started_at,
                        sc.scan_finished_at,
                        DENSE_RANK() OVER (
                            PARTITION BY ls.source_type, ls.source_no
                            ORDER BY sc.scan_started_at DESC, ls.scan_id DESC
                        ) AS scan_rank
                    FROM [Cedule].[dbo].[30_COMPTABILITÉ ET FINANCES_COST_SHARE_SNAPSHOT] ls
                    INNER JOIN [Cedule].[dbo].[30_COMPTABILITÉ ET FINANCES_COST_SHARE_SCANS] sc
                        ON sc.scan_id = ls.scan_id
                    WHERE ls.source_base_item_no = :base_item_no
                      AND sc.status = 'success'
                )
                SELECT
                    snapshot_id,
                    scan_id,
                    source_type,
                    source_no,
                    source_base_item_no,
                    header_last_modified_at,
                    line_key,
                    row_json,
                    scan_started_at,
                    scan_finished_at
                FROM ranked
                WHERE scan_rank = 1
                ORDER BY source_type ASC, source_no ASC, snapshot_id ASC
                """
            )
        else:
            stmt = text(
                f"""
                SELECT
                    ls.snapshot_id,
                    ls.scan_id,
                    ls.source_type,
                    ls.source_no,
                    ls.source_base_item_no,
                    ls.header_last_modified_at,
                    ls.line_key,
                    {row_json_select},
                    sc.scan_started_at,
                    sc.scan_finished_at
                FROM [Cedule].[dbo].[30_COMPTABILITÉ ET FINANCES_COST_SHARE_SNAPSHOT] ls
                INNER JOIN [Cedule].[dbo].[30_COMPTABILITÉ ET FINANCES_COST_SHARE_SCANS] sc
                    ON sc.scan_id = ls.scan_id
                WHERE ls.source_base_item_no = :base_item_no
                  AND sc.status = 'success'
                ORDER BY sc.scan_started_at DESC, ls.source_type ASC, ls.source_no ASC, ls.snapshot_id ASC
                """
            )

        try:
            with self._engine.connect() as conn:
                rows = conn.execute(stmt, {"base_item_no": base_item_no}).mappings().all()
        except SQLAlchemyError as exc:
            logger.error("Failed to query grouped costing snapshots", exc_info=exc)
            raise DatabaseError("Unable to query grouped costing snapshots") from exc

        return [dict(row) for row in rows]

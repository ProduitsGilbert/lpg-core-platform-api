from __future__ import annotations

import json
import logging
import os
import sqlite3
from contextlib import suppress
from datetime import datetime, timezone
from typing import Any

from app.settings import settings

logger = logging.getLogger(__name__)


class ToolingFutureNeedsCache:
    """SQLite-backed cache for daily tooling future-needs snapshots."""

    def __init__(self, db_path: str | None = None) -> None:
        self._db_path = db_path or settings.tooling_future_needs_cache_db_path
        self._enabled = True
        if not self._db_path:
            self._enabled = False
            return
        try:
            os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
            self._init_schema()
        except (OSError, sqlite3.OperationalError) as exc:
            logger.warning("Failed to initialize tooling future-needs cache storage: %s", exc)
            self._enabled = False

    @property
    def is_configured(self) -> bool:
        return self._enabled

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path, timeout=30)
        wal_enabled = False
        with suppress(sqlite3.OperationalError):
            conn.execute("PRAGMA journal_mode=WAL")
            wal_enabled = True
        if not wal_enabled:
            with suppress(sqlite3.OperationalError):
                conn.execute("PRAGMA journal_mode=DELETE")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS tooling_future_needs_snapshot (
                    work_center_no TEXT NOT NULL,
                    snapshot_date TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (work_center_no, snapshot_date)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS tooling_future_needs_registry (
                    work_center_no TEXT PRIMARY KEY,
                    last_requested_at TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def register_work_center(self, work_center_no: str) -> None:
        if not self._enabled or not work_center_no:
            return
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO tooling_future_needs_registry (work_center_no, last_requested_at)
                VALUES (?, ?)
                ON CONFLICT(work_center_no) DO UPDATE SET
                    last_requested_at = excluded.last_requested_at
                """,
                (work_center_no, datetime.now(timezone.utc).isoformat()),
            )
            conn.commit()

    def list_registered_work_centers(self) -> list[str]:
        if not self._enabled:
            return []
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT work_center_no
                FROM tooling_future_needs_registry
                ORDER BY work_center_no
                """
            ).fetchall()
        return [str(row[0]) for row in rows if row and row[0] is not None]

    def get_snapshot(self, work_center_no: str, snapshot_date: str) -> dict[str, Any] | None:
        if not self._enabled:
            return None
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT payload_json
                FROM tooling_future_needs_snapshot
                WHERE work_center_no = ? AND snapshot_date = ?
                """,
                (work_center_no, snapshot_date),
            ).fetchone()
        if not row or not row[0]:
            return None
        try:
            payload = json.loads(row[0])
            return payload if isinstance(payload, dict) else None
        except json.JSONDecodeError:
            return None

    def upsert_snapshot(self, work_center_no: str, snapshot_date: str, payload: dict[str, Any]) -> datetime:
        if not self._enabled:
            raise ValueError("Tooling future-needs cache storage not configured")
        updated_at = datetime.now(timezone.utc)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO tooling_future_needs_snapshot (work_center_no, snapshot_date, payload_json, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(work_center_no, snapshot_date) DO UPDATE SET
                    payload_json = excluded.payload_json,
                    updated_at = excluded.updated_at
                """,
                (work_center_no, snapshot_date, json.dumps(payload), updated_at.isoformat()),
            )
            conn.commit()
        return updated_at

    def prune_before(self, snapshot_date_iso: str) -> None:
        if not self._enabled:
            return
        with self._connect() as conn:
            conn.execute(
                "DELETE FROM tooling_future_needs_snapshot WHERE snapshot_date < ?",
                (snapshot_date_iso,),
            )
            conn.commit()


tooling_future_needs_cache = ToolingFutureNeedsCache()

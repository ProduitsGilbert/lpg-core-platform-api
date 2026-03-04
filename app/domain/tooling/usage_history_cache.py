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


class ToolingUsageHistoryCache:
    """SQLite-backed cache for tooling usage history snapshots."""

    def __init__(self, db_path: str | None = None) -> None:
        self._db_path = db_path or settings.tooling_usage_history_cache_db_path
        self._enabled = True
        if not self._db_path:
            self._enabled = False
            return
        try:
            os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
            self._init_schema()
        except (OSError, sqlite3.OperationalError) as exc:
            logger.warning("Failed to initialize tooling usage-history cache storage: %s", exc)
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
                CREATE TABLE IF NOT EXISTS tooling_usage_history_snapshot (
                    cache_key TEXT PRIMARY KEY,
                    work_center_no TEXT NOT NULL,
                    machine_center TEXT NOT NULL,
                    start_date TEXT NOT NULL,
                    end_date TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS tooling_usage_history_registry (
                    work_center_no TEXT NOT NULL,
                    machine_center TEXT NOT NULL,
                    last_requested_at TEXT NOT NULL,
                    PRIMARY KEY (work_center_no, machine_center)
                )
                """
            )
            conn.commit()

    def register_pair(self, work_center_no: str, machine_center: str) -> None:
        if not self._enabled or not work_center_no or not machine_center:
            return
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO tooling_usage_history_registry (work_center_no, machine_center, last_requested_at)
                VALUES (?, ?, ?)
                ON CONFLICT(work_center_no, machine_center) DO UPDATE SET
                    last_requested_at = excluded.last_requested_at
                """,
                (work_center_no, machine_center, datetime.now(timezone.utc).isoformat()),
            )
            conn.commit()

    def list_registered_pairs(self) -> list[tuple[str, str]]:
        if not self._enabled:
            return []
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT work_center_no, machine_center
                FROM tooling_usage_history_registry
                ORDER BY work_center_no, machine_center
                """
            ).fetchall()
        pairs: list[tuple[str, str]] = []
        for row in rows:
            if not row:
                continue
            wc = str(row[0] or "").strip()
            mc = str(row[1] or "").strip()
            if wc and mc:
                pairs.append((wc, mc))
        return pairs

    def get_snapshot(self, cache_key: str) -> dict[str, Any] | None:
        if not self._enabled:
            return None
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT payload_json
                FROM tooling_usage_history_snapshot
                WHERE cache_key = ?
                """,
                (cache_key,),
            ).fetchone()
        if not row or not row[0]:
            return None
        try:
            payload = json.loads(row[0])
            return payload if isinstance(payload, dict) else None
        except json.JSONDecodeError:
            return None

    def upsert_snapshot(
        self,
        *,
        cache_key: str,
        work_center_no: str,
        machine_center: str,
        start_date: str,
        end_date: str,
        payload: dict[str, Any],
    ) -> datetime:
        if not self._enabled:
            raise ValueError("Tooling usage-history cache storage not configured")
        updated_at = datetime.now(timezone.utc)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO tooling_usage_history_snapshot (
                    cache_key, work_center_no, machine_center, start_date, end_date, payload_json, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(cache_key) DO UPDATE SET
                    work_center_no = excluded.work_center_no,
                    machine_center = excluded.machine_center,
                    start_date = excluded.start_date,
                    end_date = excluded.end_date,
                    payload_json = excluded.payload_json,
                    updated_at = excluded.updated_at
                """,
                (
                    cache_key,
                    work_center_no,
                    machine_center,
                    start_date,
                    end_date,
                    json.dumps(payload),
                    updated_at.isoformat(),
                ),
            )
            conn.commit()
        return updated_at

    def prune_before(self, updated_before_iso: str) -> None:
        if not self._enabled:
            return
        with self._connect() as conn:
            conn.execute(
                "DELETE FROM tooling_usage_history_snapshot WHERE updated_at < ?",
                (updated_before_iso,),
            )
            conn.commit()


tooling_usage_history_cache = ToolingUsageHistoryCache()

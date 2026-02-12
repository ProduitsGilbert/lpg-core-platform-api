from __future__ import annotations

import json
import logging
import os
import sqlite3
from datetime import datetime
from typing import Any, Dict, Optional

from app.settings import settings

logger = logging.getLogger(__name__)


class PayablesInvoiceStatsCache:
    """SQLite-backed daily snapshots for KPI payables invoice stats."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        self._db_path = db_path or settings.payables_stats_cache_db_path
        self._enabled = True
        if not self._db_path:
            self._enabled = False
            return
        try:
            os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
            self._init_schema()
        except (OSError, sqlite3.OperationalError) as exc:
            logger.warning("Failed to initialize payables stats cache storage: %s", exc)
            self._enabled = False

    @property
    def is_configured(self) -> bool:
        return self._enabled

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path, timeout=30)
        try:
            conn.execute("PRAGMA journal_mode=WAL")
        except sqlite3.OperationalError:
            try:
                conn.execute("PRAGMA journal_mode=DELETE")
            except sqlite3.OperationalError:
                pass
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS kpi_payables_invoice_stats_snapshot (
                    snapshot_date TEXT PRIMARY KEY,
                    payload_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def get_snapshot(self, snapshot_date: str) -> Optional[Dict[str, Any]]:
        if not self._enabled:
            return None
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT payload_json
                FROM kpi_payables_invoice_stats_snapshot
                WHERE snapshot_date = ?
                """,
                (snapshot_date,),
            ).fetchone()
        if not row or not row[0]:
            return None
        try:
            payload = json.loads(row[0])
            return payload if isinstance(payload, dict) else None
        except json.JSONDecodeError:
            return None

    def get_latest_snapshot(self) -> Optional[Dict[str, Any]]:
        if not self._enabled:
            return None
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT payload_json
                FROM kpi_payables_invoice_stats_snapshot
                ORDER BY snapshot_date DESC
                LIMIT 1
                """
            ).fetchone()
        if not row or not row[0]:
            return None
        try:
            payload = json.loads(row[0])
            return payload if isinstance(payload, dict) else None
        except json.JSONDecodeError:
            return None

    def upsert_snapshot(self, snapshot_date: str, payload: Dict[str, Any]) -> datetime:
        if not self._enabled:
            raise ValueError("Payables stats cache storage not configured")
        updated_at = datetime.utcnow()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO kpi_payables_invoice_stats_snapshot (snapshot_date, payload_json, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(snapshot_date) DO UPDATE SET
                    payload_json = excluded.payload_json,
                    updated_at = excluded.updated_at
                """,
                (snapshot_date, json.dumps(payload), updated_at.isoformat()),
            )
            conn.commit()
        return updated_at

    def prune_before(self, snapshot_date: str) -> None:
        if not self._enabled:
            return
        with self._connect() as conn:
            conn.execute(
                "DELETE FROM kpi_payables_invoice_stats_snapshot WHERE snapshot_date < ?",
                (snapshot_date,),
            )
            conn.commit()


payables_invoice_stats_cache = PayablesInvoiceStatsCache()

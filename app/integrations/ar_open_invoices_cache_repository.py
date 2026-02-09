from __future__ import annotations

import json
import logging
import os
import sqlite3
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from app.settings import settings

logger = logging.getLogger(__name__)


class ArOpenInvoicesCacheRepository:
    """SQLite-backed cache for open AR invoices."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        self._db_path = db_path or settings.ar_open_invoices_cache_path
        self._enabled = True
        if not self._db_path:
            self._enabled = False
            return
        try:
            os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
            self._init_schema()
        except (OSError, sqlite3.OperationalError) as exc:
            logger.warning("Failed to initialize AR cache storage: %s", exc)
            self._enabled = False

    @property
    def is_configured(self) -> bool:
        return self._enabled

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path, timeout=30)
        try:
            conn.execute("PRAGMA journal_mode=WAL")
        except sqlite3.OperationalError as exc:
            logger.warning("AR cache WAL mode unavailable; using DELETE journal: %s", exc)
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
                CREATE TABLE IF NOT EXISTS ar_open_invoices_cache (
                    cache_key TEXT PRIMARY KEY,
                    payload_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def get_cache(self, cache_key: str) -> Optional[Tuple[datetime, list[Dict[str, Any]]]]:
        if not self._enabled:
            return None
        with self._connect() as conn:
            row = conn.execute(
                "SELECT payload_json, updated_at FROM ar_open_invoices_cache WHERE cache_key = ?",
                (cache_key,),
            ).fetchone()
        if not row:
            return None
        payload_json, updated_at_raw = row
        if not payload_json:
            return None
        try:
            payload = json.loads(payload_json)
        except json.JSONDecodeError:
            return None
        if not isinstance(payload, list):
            return None
        try:
            updated_at = datetime.fromisoformat(updated_at_raw)
        except ValueError:
            updated_at = datetime.utcnow()
        return updated_at, payload

    def upsert_cache(self, cache_key: str, payload: list[Dict[str, Any]]) -> datetime:
        if not self._enabled:
            raise ValueError("Cache storage not configured")
        updated_at = datetime.utcnow()
        payload_json = json.dumps(payload)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO ar_open_invoices_cache (cache_key, payload_json, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(cache_key) DO UPDATE SET
                    payload_json = excluded.payload_json,
                    updated_at = excluded.updated_at
                """,
                (cache_key, payload_json, updated_at.isoformat()),
            )
            conn.commit()
        return updated_at

from __future__ import annotations

import asyncio
import datetime as dt
import json
import logging
import sqlite3
from typing import Dict, Iterable, List, Optional, Tuple

from app.settings import settings

logger = logging.getLogger(__name__)


class PlannerKpiCache:
    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._init_lock = asyncio.Lock()
        self._initialized = False

    async def _ensure_initialized(self) -> None:
        if self._initialized:
            return
        async with self._init_lock:
            if self._initialized:
                return
            await asyncio.to_thread(self._init_schema_sync)
            self._initialized = True

    def _init_schema_sync(self) -> None:
        try:
            conn = sqlite3.connect(self._db_path)
            try:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS planner_kpi_history (
                        work_center_no TEXT NOT NULL,
                        date TEXT NOT NULL,
                        mo_done INTEGER NOT NULL,
                        mo_remaining INTEGER NOT NULL,
                        updated_at TEXT NOT NULL,
                        PRIMARY KEY (work_center_no, date)
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS planner_daily_report_cache (
                        cache_key TEXT PRIMARY KEY,
                        posting_date TEXT NOT NULL,
                        payload TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS planner_daily_workcenter_snapshot (
                        work_center_no TEXT NOT NULL,
                        date TEXT NOT NULL,
                        mo_done INTEGER NOT NULL,
                        mo_remaining INTEGER NOT NULL,
                        updated_at TEXT NOT NULL,
                        PRIMARY KEY (work_center_no, date)
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS planner_kpi_registry (
                        work_center_no TEXT PRIMARY KEY,
                        last_requested_at TEXT NOT NULL
                    )
                    """
                )
                conn.commit()
            finally:
                conn.close()
        except Exception as exc:
            logger.warning("Failed to initialize planner KPI cache: %s", exc)

    async def register_workcenter(self, work_center_no: str) -> None:
        await self._ensure_initialized()
        timestamp = dt.datetime.utcnow().isoformat()
        await asyncio.to_thread(self._register_workcenter_sync, work_center_no, timestamp)

    def _register_workcenter_sync(self, work_center_no: str, timestamp: str) -> None:
        try:
            conn = sqlite3.connect(self._db_path)
            try:
                conn.execute(
                    """
                    INSERT INTO planner_kpi_registry (work_center_no, last_requested_at)
                    VALUES (?, ?)
                    ON CONFLICT(work_center_no) DO UPDATE SET last_requested_at = excluded.last_requested_at
                    """,
                    (work_center_no, timestamp),
                )
                conn.commit()
            finally:
                conn.close()
        except Exception as exc:
            logger.warning("Failed to register work center for KPI cache: %s", exc)

    async def list_registered_workcenters(self) -> List[str]:
        await self._ensure_initialized()
        return await asyncio.to_thread(self._list_registered_workcenters_sync)

    def _list_registered_workcenters_sync(self) -> List[str]:
        try:
            conn = sqlite3.connect(self._db_path)
            try:
                rows = conn.execute("SELECT work_center_no FROM planner_kpi_registry").fetchall()
            finally:
                conn.close()
            return [row[0] for row in rows]
        except Exception as exc:
            logger.warning("Failed to list registered work centers: %s", exc)
            return []

    async def get_points(
        self,
        work_center_no: str,
        start_date: dt.date,
        end_date: dt.date,
    ) -> Dict[str, Tuple[int, int]]:
        await self._ensure_initialized()
        return await asyncio.to_thread(
            self._get_points_sync, work_center_no, start_date.isoformat(), end_date.isoformat()
        )

    def _get_points_sync(
        self,
        work_center_no: str,
        start_date: str,
        end_date: str,
    ) -> Dict[str, Tuple[int, int]]:
        try:
            conn = sqlite3.connect(self._db_path)
            try:
                rows = conn.execute(
                    """
                    SELECT date, mo_done, mo_remaining
                    FROM planner_kpi_history
                    WHERE work_center_no = ? AND date BETWEEN ? AND ?
                    """,
                    (work_center_no, start_date, end_date),
                ).fetchall()
            finally:
                conn.close()
            return {row[0]: (int(row[1]), int(row[2])) for row in rows}
        except Exception as exc:
            logger.warning("Failed to read planner KPI cache: %s", exc)
            return {}

    async def upsert_points(
        self,
        work_center_no: str,
        points: Iterable[Tuple[str, int, int]],
    ) -> None:
        await self._ensure_initialized()
        payload = [(work_center_no, date, mo_done, mo_remaining, dt.datetime.utcnow().isoformat()) for date, mo_done, mo_remaining in points]
        await asyncio.to_thread(self._upsert_points_sync, payload)

    def _upsert_points_sync(self, payload: List[Tuple[str, str, int, int, str]]) -> None:
        if not payload:
            return
        try:
            conn = sqlite3.connect(self._db_path)
            try:
                conn.executemany(
                    """
                    INSERT INTO planner_kpi_history (work_center_no, date, mo_done, mo_remaining, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(work_center_no, date) DO UPDATE SET
                        mo_done = excluded.mo_done,
                        mo_remaining = excluded.mo_remaining,
                        updated_at = excluded.updated_at
                    """,
                    payload,
                )
                conn.commit()
            finally:
                conn.close()
        except Exception as exc:
            logger.warning("Failed to persist planner KPI cache: %s", exc)

    async def prune_older_than(self, cutoff_date: dt.date) -> None:
        await self._ensure_initialized()
        await asyncio.to_thread(self._prune_older_than_sync, cutoff_date.isoformat())

    def _prune_older_than_sync(self, cutoff_iso: str) -> None:
        try:
            conn = sqlite3.connect(self._db_path)
            try:
                conn.execute(
                    "DELETE FROM planner_kpi_history WHERE date < ?",
                    (cutoff_iso,),
                )
                conn.execute(
                    "DELETE FROM planner_daily_report_cache WHERE posting_date < ?",
                    (cutoff_iso,),
                )
                conn.execute(
                    "DELETE FROM planner_daily_workcenter_snapshot WHERE date < ?",
                    (cutoff_iso,),
                )
                conn.commit()
            finally:
                conn.close()
        except Exception as exc:
            logger.warning("Failed to prune planner KPI cache: %s", exc)

    async def get_daily_report(
        self,
        cache_key: str,
    ) -> Optional[Dict[str, object]]:
        await self._ensure_initialized()
        return await asyncio.to_thread(self._get_daily_report_sync, cache_key)

    def _get_daily_report_sync(self, cache_key: str) -> Optional[Dict[str, object]]:
        try:
            conn = sqlite3.connect(self._db_path)
            try:
                row = conn.execute(
                    """
                    SELECT payload
                    FROM planner_daily_report_cache
                    WHERE cache_key = ?
                    """,
                    (cache_key,),
                ).fetchone()
            finally:
                conn.close()
            if not row:
                return None
            return json.loads(row[0])
        except Exception as exc:
            logger.warning("Failed to read planner daily report cache: %s", exc)
            return None

    async def set_daily_report(
        self,
        cache_key: str,
        posting_date: str,
        payload: Dict[str, object],
    ) -> None:
        await self._ensure_initialized()
        serialized = json.dumps(payload, ensure_ascii=False)
        await asyncio.to_thread(self._set_daily_report_sync, cache_key, posting_date, serialized)

    def _set_daily_report_sync(
        self,
        cache_key: str,
        posting_date: str,
        payload: str,
    ) -> None:
        try:
            conn = sqlite3.connect(self._db_path)
            try:
                conn.execute(
                    """
                    INSERT INTO planner_daily_report_cache (cache_key, posting_date, payload, updated_at)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(cache_key) DO UPDATE SET
                        posting_date = excluded.posting_date,
                        payload = excluded.payload,
                        updated_at = excluded.updated_at
                    """,
                    (cache_key, posting_date, payload, dt.datetime.utcnow().isoformat()),
                )
                conn.commit()
            finally:
                conn.close()
        except Exception as exc:
            logger.warning("Failed to write planner daily report cache: %s", exc)

    async def get_workcenter_snapshots(
        self,
        work_center_no: str,
        start_date: dt.date,
        end_date: dt.date,
    ) -> Dict[str, Tuple[int, int]]:
        await self._ensure_initialized()
        return await asyncio.to_thread(
            self._get_workcenter_snapshots_sync,
            work_center_no,
            start_date.isoformat(),
            end_date.isoformat(),
        )

    def _get_workcenter_snapshots_sync(
        self,
        work_center_no: str,
        start_date: str,
        end_date: str,
    ) -> Dict[str, Tuple[int, int]]:
        try:
            conn = sqlite3.connect(self._db_path)
            try:
                rows = conn.execute(
                    """
                    SELECT date, mo_done, mo_remaining
                    FROM planner_daily_workcenter_snapshot
                    WHERE work_center_no = ? AND date BETWEEN ? AND ?
                    """,
                    (work_center_no, start_date, end_date),
                ).fetchall()
            finally:
                conn.close()
            return {row[0]: (int(row[1]), int(row[2])) for row in rows}
        except Exception as exc:
            logger.warning("Failed to read planner workcenter snapshots: %s", exc)
            return {}

    async def upsert_workcenter_snapshots(
        self,
        points: Iterable[Tuple[str, str, int, int]],
    ) -> None:
        await self._ensure_initialized()
        payload = [
            (work_center_no, date, mo_done, mo_remaining, dt.datetime.utcnow().isoformat())
            for work_center_no, date, mo_done, mo_remaining in points
        ]
        await asyncio.to_thread(self._upsert_workcenter_snapshots_sync, payload)

    def _upsert_workcenter_snapshots_sync(
        self,
        payload: List[Tuple[str, str, int, int, str]],
    ) -> None:
        if not payload:
            return
        try:
            conn = sqlite3.connect(self._db_path)
            try:
                conn.executemany(
                    """
                    INSERT INTO planner_daily_workcenter_snapshot (work_center_no, date, mo_done, mo_remaining, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(work_center_no, date) DO UPDATE SET
                        mo_done = excluded.mo_done,
                        mo_remaining = excluded.mo_remaining,
                        updated_at = excluded.updated_at
                    """,
                    payload,
                )
                conn.commit()
            finally:
                conn.close()
        except Exception as exc:
            logger.warning("Failed to write planner workcenter snapshots: %s", exc)


planner_kpi_cache = PlannerKpiCache(settings.planner_kpi_cache_db_path)


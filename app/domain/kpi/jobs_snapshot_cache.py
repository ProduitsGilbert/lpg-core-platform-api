from __future__ import annotations

import logging
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from app.settings import settings

logger = logging.getLogger(__name__)


@dataclass
class JobSnapshotRow:
    snapshot_date: str
    job_no: str
    job_name: Optional[str]
    job_status: Optional[str]
    avancement_bom_percent: float
    division: Optional[str]
    region: Optional[str]


class JobsSnapshotCache:
    """SQLite-backed daily snapshots for jobs KPI progress."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        self._db_path = db_path or settings.jobs_snapshot_cache_db_path
        self._enabled = True
        if not self._db_path:
            self._enabled = False
            return
        try:
            os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
            self._init_schema()
        except (OSError, sqlite3.OperationalError) as exc:
            logger.warning("Failed to initialize jobs snapshot cache storage: %s", exc)
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
                CREATE TABLE IF NOT EXISTS kpi_job_status_snapshot (
                    snapshot_date TEXT NOT NULL,
                    job_no TEXT NOT NULL,
                    job_name TEXT,
                    job_status TEXT,
                    avancement_bom_percent REAL NOT NULL,
                    division TEXT,
                    region TEXT,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (snapshot_date, job_no)
                )
                """
            )
            conn.commit()

    def get_latest_snapshot_date(self) -> Optional[str]:
        if not self._enabled:
            return None
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT snapshot_date
                FROM kpi_job_status_snapshot
                ORDER BY snapshot_date DESC
                LIMIT 1
                """
            ).fetchone()
        return str(row[0]) if row and row[0] else None

    def list_snapshot_rows(
        self,
        *,
        snapshot_date: str,
        division: Optional[str] = None,
        region: Optional[str] = None,
        job_no: Optional[str] = None,
        job_status: Optional[str] = None,
    ) -> List[JobSnapshotRow]:
        if not self._enabled:
            return []
        query = (
            "SELECT snapshot_date, job_no, job_name, job_status, avancement_bom_percent, division, region "
            "FROM kpi_job_status_snapshot WHERE snapshot_date = ?"
        )
        params: list[object] = [snapshot_date]
        if division:
            query += " AND division = ?"
            params.append(division)
        if region:
            query += " AND region = ?"
            params.append(region)
        if job_no:
            query += " AND job_no = ?"
            params.append(job_no)
        if job_status:
            query += " AND job_status = ?"
            params.append(job_status)
        query += " ORDER BY job_no ASC"

        with self._connect() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
        return [
            JobSnapshotRow(
                snapshot_date=str(row[0]),
                job_no=str(row[1]),
                job_name=str(row[2]) if row[2] is not None else None,
                job_status=str(row[3]) if row[3] is not None else None,
                avancement_bom_percent=float(row[4] if row[4] is not None else 0.0),
                division=str(row[5]) if row[5] is not None else None,
                region=str(row[6]) if row[6] is not None else None,
            )
            for row in rows
        ]

    def list_history_rows(
        self,
        *,
        start_date: str,
        end_date: str,
        division: Optional[str] = None,
        region: Optional[str] = None,
        job_no: Optional[str] = None,
        job_status: Optional[str] = None,
    ) -> List[JobSnapshotRow]:
        if not self._enabled:
            return []
        query = (
            "SELECT snapshot_date, job_no, job_name, job_status, avancement_bom_percent, division, region "
            "FROM kpi_job_status_snapshot WHERE snapshot_date BETWEEN ? AND ?"
        )
        params: list[object] = [start_date, end_date]
        if division:
            query += " AND division = ?"
            params.append(division)
        if region:
            query += " AND region = ?"
            params.append(region)
        if job_no:
            query += " AND job_no = ?"
            params.append(job_no)
        if job_status:
            query += " AND job_status = ?"
            params.append(job_status)
        query += " ORDER BY snapshot_date ASC, job_no ASC"

        with self._connect() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
        return [
            JobSnapshotRow(
                snapshot_date=str(row[0]),
                job_no=str(row[1]),
                job_name=str(row[2]) if row[2] is not None else None,
                job_status=str(row[3]) if row[3] is not None else None,
                avancement_bom_percent=float(row[4] if row[4] is not None else 0.0),
                division=str(row[5]) if row[5] is not None else None,
                region=str(row[6]) if row[6] is not None else None,
            )
            for row in rows
        ]

    def upsert_snapshot_rows(
        self,
        snapshot_date: str,
        rows: List[JobSnapshotRow],
        *,
        replace_snapshot: bool = True,
    ) -> datetime:
        if not self._enabled:
            raise ValueError("Jobs snapshot cache storage not configured")
        updated_at = datetime.utcnow().isoformat()
        with self._connect() as conn:
            if replace_snapshot:
                conn.execute(
                    "DELETE FROM kpi_job_status_snapshot WHERE snapshot_date = ?",
                    (snapshot_date,),
                )
            conn.executemany(
                """
                INSERT INTO kpi_job_status_snapshot (
                    snapshot_date,
                    job_no,
                    job_name,
                    job_status,
                    avancement_bom_percent,
                    division,
                    region,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(snapshot_date, job_no) DO UPDATE SET
                    job_name = excluded.job_name,
                    job_status = excluded.job_status,
                    avancement_bom_percent = excluded.avancement_bom_percent,
                    division = excluded.division,
                    region = excluded.region,
                    updated_at = excluded.updated_at
                """,
                [
                    (
                        row.snapshot_date,
                        row.job_no,
                        row.job_name,
                        row.job_status,
                        float(row.avancement_bom_percent),
                        row.division,
                        row.region,
                        updated_at,
                    )
                    for row in rows
                ],
            )
            conn.commit()
        return datetime.fromisoformat(updated_at)

    def prune_before(self, snapshot_date: str) -> None:
        if not self._enabled:
            return
        with self._connect() as conn:
            conn.execute(
                "DELETE FROM kpi_job_status_snapshot WHERE snapshot_date < ?",
                (snapshot_date,),
            )
            conn.commit()


jobs_snapshot_cache = JobsSnapshotCache()

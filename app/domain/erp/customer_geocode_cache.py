"""Customer geocoding cache backed by Google Geocoding API."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import sqlite3
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, Optional

import httpx

from app.domain.erp.business_central_data_service import BusinessCentralODataService
from app.domain.erp.models import GeocodedLocation
from app.settings import settings

logger = logging.getLogger(__name__)


@dataclass
class _CacheEntry:
    address_hash: str
    updated_at: datetime
    geocode: Optional[GeocodedLocation]


class CustomerGeocodeCache:
    """In-memory cache for customer address geocoding."""

    def __init__(
        self,
        ttl: timedelta | None = None,
        max_concurrency: int = 5,
        persist_enabled: bool = False,
        db_path: Optional[str] = None,
    ) -> None:
        self._ttl = ttl or timedelta(days=7)
        self._max_concurrency = max_concurrency
        self._cache: Dict[str, _CacheEntry] = {}
        self._lock = asyncio.Lock()
        self._in_flight: Dict[str, asyncio.Task[Optional[GeocodedLocation]]] = {}
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._persist_enabled = persist_enabled
        self._db_path = db_path
        self._cache_source = settings.google_geocode_cache_source
        if self._persist_enabled and self._db_path:
            try:
                os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
                self._init_storage()
            except (OSError, sqlite3.OperationalError) as exc:
                logger.warning(
                    "Failed to initialize geocode cache storage at %s: %s",
                    self._db_path,
                    exc,
                )
                self._persist_enabled = False

    @staticmethod
    def _hash_address(address: str) -> str:
        return hashlib.sha256(address.encode("utf-8")).hexdigest()

    @staticmethod
    def build_address(record: Dict[str, Any]) -> str:
        """Build a single-line address from a Business Central customer record."""
        parts = [
            record.get("Address"),
            record.get("Address_2") or record.get("Address2"),
            record.get("Address_3") or record.get("Address3"),
            record.get("Address_4") or record.get("Address4"),
            record.get("City"),
            record.get("County"),
            record.get("Post_Code") or record.get("PostCode"),
            record.get("Country_Region_Code")
            or record.get("CountryRegionCode")
            or record.get("Country"),
        ]
        cleaned = [str(part).strip() for part in parts if part]
        return ", ".join(cleaned)

    @staticmethod
    def build_address_from_ship_to(record: Dict[str, Any]) -> str:
        """Build a single-line address from a Business Central ship-to record."""
        parts = [
            record.get("Address"),
            record.get("Address_2") or record.get("Address2"),
            record.get("Address_3") or record.get("Address3"),
            record.get("Address_4") or record.get("Address4"),
            record.get("City"),
            record.get("County"),
            record.get("Post_Code") or record.get("PostCode"),
            record.get("Country_Region_Code")
            or record.get("CountryRegionCode")
            or record.get("Country"),
        ]
        cleaned = [str(part).strip() for part in parts if part]
        return ", ".join(cleaned)

    def _is_stale(self, entry: _CacheEntry) -> bool:
        return datetime.now(timezone.utc) - entry.updated_at > self._ttl

    def get_cached(self, customer_no: str, address: str) -> Optional[GeocodedLocation]:
        """Return cached geocode without blocking on refresh."""
        if not customer_no or not address:
            return None
        address_hash = self._hash_address(address)
        cache_key = f"{customer_no}:{address_hash}"
        entry = self._cache.get(cache_key)
        if entry and entry.address_hash == address_hash:
            return entry.geocode
        if self._persist_enabled and self._db_path:
            entry = self._load_entry_from_storage_sync(cache_key)
            if entry:
                self._cache[cache_key] = entry
                if entry.address_hash == address_hash:
                    return entry.geocode
        return None

    def _init_storage(self) -> None:
        if not self._db_path:
            return
        with sqlite3.connect(self._db_path, timeout=30) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            cursor = conn.execute("PRAGMA table_info(geocode_cache)")
            columns = {row[1] for row in cursor.fetchall()}
            if columns and "cache_key" not in columns:
                conn.execute("DROP TABLE geocode_cache")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS geocode_cache (
                    cache_key TEXT PRIMARY KEY,
                    customer_no TEXT NOT NULL,
                    address_hash TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    geocode_json TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS geocode_cache_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )
            cursor = conn.execute(
                "SELECT value FROM geocode_cache_meta WHERE key = 'source'"
            )
            row = cursor.fetchone()
            if not row or row[0] != self._cache_source:
                conn.execute("DELETE FROM geocode_cache")
                conn.execute(
                    """
                    INSERT INTO geocode_cache_meta (key, value)
                    VALUES ('source', ?)
                    ON CONFLICT(key) DO UPDATE SET value=excluded.value
                    """,
                    (self._cache_source,),
                )
            conn.commit()

    def _load_from_storage_sync(self) -> None:
        if not self._db_path:
            return
        with sqlite3.connect(self._db_path, timeout=30) as conn:
            cursor = conn.execute(
                "SELECT cache_key, customer_no, address_hash, updated_at, geocode_json FROM geocode_cache"
            )
            rows = cursor.fetchall()

        for cache_key, customer_no, address_hash, updated_at, geocode_json in rows:
            geocode = None
            if geocode_json:
                try:
                    geocode = GeocodedLocation(**json.loads(geocode_json))
                except (TypeError, ValueError):
                    geocode = None
            try:
                updated_dt = datetime.fromisoformat(updated_at)
            except ValueError:
                updated_dt = datetime.now(timezone.utc)
            self._cache[cache_key] = _CacheEntry(
                address_hash=address_hash,
                updated_at=updated_dt,
                geocode=geocode,
            )

    def _load_entry_from_storage_sync(self, cache_key: str) -> Optional[_CacheEntry]:
        if not self._db_path:
            return None
        with sqlite3.connect(self._db_path, timeout=30) as conn:
            cursor = conn.execute(
                "SELECT address_hash, updated_at, geocode_json FROM geocode_cache WHERE cache_key = ?",
                (cache_key,),
            )
            row = cursor.fetchone()
        if not row:
            return None
        address_hash, updated_at, geocode_json = row
        geocode = None
        if geocode_json:
            try:
                geocode = GeocodedLocation(**json.loads(geocode_json))
            except (TypeError, ValueError):
                geocode = None
        try:
            updated_dt = datetime.fromisoformat(updated_at)
        except ValueError:
            updated_dt = datetime.now(timezone.utc)
        return _CacheEntry(
            address_hash=address_hash,
            updated_at=updated_dt,
            geocode=geocode,
        )

    async def load_from_storage(self) -> None:
        """Load cached geocodes from disk into memory."""
        if not (self._persist_enabled and self._db_path):
            return
        await asyncio.to_thread(self._load_from_storage_sync)

    def _persist_entry_sync(self, customer_no: str, cache_key: str, entry: _CacheEntry) -> None:
        if not self._db_path:
            return
        geocode_json = None
        if entry.geocode is not None:
            geocode_json = json.dumps(entry.geocode.model_dump())
        for attempt in range(3):
            try:
                with sqlite3.connect(self._db_path, timeout=30) as conn:
                    conn.execute("PRAGMA journal_mode=WAL")
                    conn.execute(
                        """
                        INSERT INTO geocode_cache (cache_key, customer_no, address_hash, updated_at, geocode_json)
                        VALUES (?, ?, ?, ?, ?)
                        ON CONFLICT(cache_key) DO UPDATE SET
                            address_hash=excluded.address_hash,
                            updated_at=excluded.updated_at,
                            geocode_json=excluded.geocode_json
                        """,
                        (
                            cache_key,
                            customer_no,
                            entry.address_hash,
                            entry.updated_at.isoformat(),
                            geocode_json,
                        ),
                    )
                    conn.commit()
                return
            except sqlite3.OperationalError as exc:
                if attempt == 2:
                    logger.warning("Failed to persist geocode cache entry: %s", exc)
                    return
                time.sleep(0.2)

    async def _geocode_address(self, address: str) -> Optional[GeocodedLocation]:
        if not settings.google_api_key:
            logger.warning("GOOGLE_API_KEY is not configured; skipping geocoding")
            return None

        params = {
            "address": address,
            "key": settings.google_api_key,
        }
        try:
            async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
                response = await client.get(
                    "https://maps.googleapis.com/maps/api/geocode/json",
                    params=params,
                )
                response.raise_for_status()
                payload = response.json()
        except httpx.HTTPError as exc:
            logger.warning("Google geocoding request failed: %s", exc)
            return GeocodedLocation(status="REQUEST_FAILED")

        status = payload.get("status")
        results = payload.get("results") or []
        if status != "OK" or not results:
            return GeocodedLocation(status=status)

        result = results[0]
        location = (result.get("geometry") or {}).get("location") or {}
        location_type = (result.get("geometry") or {}).get("location_type")

        return GeocodedLocation(
            latitude=location.get("lat"),
            longitude=location.get("lng"),
            formatted_address=result.get("formatted_address"),
            place_id=result.get("place_id"),
            location_type=location_type,
            status=status,
        )

    async def get_or_fetch(self, customer_no: str, address: str) -> Optional[GeocodedLocation]:
        """Return cached geocode, refreshing if missing or stale."""
        if not address:
            return None

        address_hash = self._hash_address(address)
        cache_key = f"{customer_no}:{address_hash}"

        async with self._lock:
            entry = self._cache.get(cache_key)
            if entry and entry.address_hash == address_hash and not self._is_stale(entry):
                return entry.geocode

            in_flight = self._in_flight.get(cache_key)
            if in_flight:
                return await in_flight

            task = asyncio.create_task(
                self._refresh(customer_no, address, address_hash, cache_key)
            )
            self._in_flight[cache_key] = task

        return await task

    async def schedule_refresh(self, customer_no: str, address: str) -> None:
        """Schedule a refresh in the background if cache is missing or stale."""
        if not customer_no or not address:
            return
        address_hash = self._hash_address(address)
        cache_key = f"{customer_no}:{address_hash}"
        async with self._lock:
            entry = self._cache.get(cache_key)
            if entry and entry.address_hash == address_hash and not self._is_stale(entry):
                return
            if cache_key in self._in_flight:
                return
            self._in_flight[cache_key] = asyncio.create_task(
                self._refresh(customer_no, address, address_hash, cache_key)
            )

    async def _refresh(
        self,
        customer_no: str,
        address: str,
        address_hash: str,
        cache_key: str,
    ) -> Optional[GeocodedLocation]:
        try:
            async with self._semaphore:
                geocode = await self._geocode_address(address)

            async with self._lock:
                entry = _CacheEntry(
                    address_hash=address_hash,
                    updated_at=datetime.now(timezone.utc),
                    geocode=geocode,
                )
                self._cache[cache_key] = entry

            if self._persist_enabled and self._db_path:
                await asyncio.to_thread(self._persist_entry_sync, customer_no, cache_key, entry)
            return geocode
        finally:
            async with self._lock:
                self._in_flight.pop(cache_key, None)

    async def warm_from_records(self, records: Iterable[Dict[str, Any]]) -> None:
        """Populate the cache from Business Central customer records."""
        tasks = []
        for record in records:
            customer_no = str(record.get("No") or "")
            if not customer_no:
                continue
            address = self.build_address(record)
            if not address:
                continue
            tasks.append(self.get_or_fetch(customer_no, address))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def warm_from_bc(self) -> None:
        """Fetch customers from Business Central and warm the geocode cache."""
        logger.info("Starting geocode warm-up from Business Central")
        try:
            service = BusinessCentralODataService()
        except Exception as exc:  # pragma: no cover - startup safeguard
            logger.warning("Failed to initialize Business Central service: %s", exc)
            return

        try:
            records = await service.fetch_collection_paged("Customers")
        except Exception as exc:
            logger.warning("Failed to load customers for geocode warm-up: %s", exc)
            return

        ship_to_records: list[Dict[str, Any]] = []
        for resource in ("ShipToAddress", "ShipToAddresses", "Ship_to_Address", "Ship_to_Addresses"):
            try:
                ship_to_records = await service.fetch_collection_paged(resource)
                if ship_to_records:
                    break
            except Exception:
                continue

        logger.info(
            "Geocode warm-up fetched %s customers and %s ship-to addresses",
            len(records),
            len(ship_to_records),
        )

        ship_to_by_customer: Dict[str, list[Dict[str, Any]]] = {}
        for ship_to in ship_to_records:
            customer_no = (
                ship_to.get("Customer_No")
                or ship_to.get("CustomerNo")
                or ship_to.get("Customer_No_")
                or ship_to.get("CustomerNumber")
            )
            if not customer_no:
                continue
            ship_to_by_customer.setdefault(str(customer_no), []).append(ship_to)

        tasks = []
        for ship_to in ship_to_records:
            customer_no = (
                ship_to.get("Customer_No")
                or ship_to.get("CustomerNo")
                or ship_to.get("Customer_No_")
                or ship_to.get("CustomerNumber")
            )
            if not customer_no:
                continue
            address = self.build_address_from_ship_to(ship_to)
            if not address:
                continue
            tasks.append(self.get_or_fetch(str(customer_no), address))

        for record in records:
            customer_no = str(record.get("No") or "")
            if not customer_no:
                continue
            if customer_no in ship_to_by_customer:
                continue
            address = self.build_address(record)
            if not address:
                continue
            tasks.append(self.get_or_fetch(customer_no, address))

        if tasks:
            logger.info("Geocode warm-up scheduling %s address lookups", len(tasks))
            await asyncio.gather(*tasks, return_exceptions=True)


customer_geocode_cache = CustomerGeocodeCache(
    ttl=timedelta(days=settings.google_geocode_cache_ttl_days),
    max_concurrency=settings.google_geocode_max_concurrency,
    persist_enabled=settings.google_geocode_persist_enabled,
    db_path=settings.google_geocode_cache_db_path,
)


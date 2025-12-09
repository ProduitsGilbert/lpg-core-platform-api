"""Item availability aggregation service."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.parse import quote
import logging

import httpx
import logfire

from app.adapters.erp_client import ERPClient
from app.domain.erp.models import ItemAvailabilityResponse, ItemAvailabilityTimelineEntry
from app.errors import PlanningServiceError
from app.settings import settings

logger = logging.getLogger(__name__)
DecimalZero = Decimal("0")


class ItemAvailabilityService:
    """Aggregate inventory, inbound, and outbound data per item."""

    def __init__(self, erp_client: ERPClient | None = None) -> None:
        self.erp_client = erp_client or ERPClient()
        self._toolkit_base_url = (settings.toolkit_base_url or "").rstrip("/")
        self._timeout = settings.request_timeout
        self._headers = {"accept": "*/*"}

    async def get_availability(
        self,
        item_id: str,
        include_details: bool = False,
        *,
        exclude_minimum_stock: bool = False,
    ) -> ItemAvailabilityResponse:
        """
        Build availability summary for an item.
        """
        if not self._toolkit_base_url:
            raise PlanningServiceError("Toolkit base URL is not configured", status_code=500)

        today = date.today()

        with logfire.span(
            "item_availability",
            item_id=item_id,
            include_details=include_details,
        ):
            inventory_task = asyncio.create_task(self._get_current_inventory(item_id))
            inbound_task = asyncio.create_task(self._fetch_basic_mrp_direction("In", item_id))
            outbound_task = asyncio.create_task(self._fetch_basic_mrp_direction("Out", item_id))

            inbound_rows: List[Dict[str, Any]]
            outbound_rows: List[Dict[str, Any]]
            current_inventory, inbound_rows, outbound_rows = await asyncio.gather(
                inventory_task,
                inbound_task,
                outbound_task,
            )

        inbound_events = self._build_inbound_events(inbound_rows)
        outbound_events = self._build_outbound_events(outbound_rows, exclude_minimum_stock=exclude_minimum_stock)

        total_incoming = sum((qty for _, qty, _ in inbound_events), DecimalZero)
        total_outgoing = sum((qty for _, qty, _ in outbound_events), DecimalZero)
        projected_available = current_inventory + total_incoming - total_outgoing

        timeline: List[ItemAvailabilityTimelineEntry] | None = None
        if include_details:
            timeline = self._build_timeline(
                inbound_events,
                outbound_events,
                current_inventory,
                today,
            )

        return ItemAvailabilityResponse(
            item_id=item_id,
            as_of_date=today,
            current_inventory=current_inventory,
            total_incoming=total_incoming,
            total_outgoing=total_outgoing,
            projected_available=projected_available,
            details_included=bool(include_details),
            timeline=timeline,
        )

    async def _get_current_inventory(self, item_id: str) -> Decimal:
        """Fetch on-hand quantity in fixed bins for the item."""
        with logfire.span("item_availability.inventory", item_id=item_id):
            return await self.erp_client.get_fixed_bin_quantity(item_id, location_code="GIL")

    async def _fetch_basic_mrp_direction(self, direction: str, item_id: str) -> List[Dict[str, Any]]:
        """Call the Basic MRP In/Out endpoints for a specific item."""
        encoded_item = quote(item_id, safe="")
        url = f"{self._toolkit_base_url}/api/mrp/BasicMRP/{direction}({encoded_item})"
        span_name = f"basic_mrp.{direction.lower()}"

        try:
            with logfire.span(span_name, url=url, item_id=item_id):
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    response = await client.get(url, headers=self._headers)
                response.raise_for_status()
                payload = response.json()
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code if exc.response else None
            body = exc.response.text[:500] if exc.response and exc.response.text else ""
            logger.error(
                "Basic MRP %s endpoint returned HTTP error",
                direction,
                extra={"status_code": status_code, "body": body, "item_id": item_id},
            )
            raise PlanningServiceError(
                f"MRP {direction} endpoint returned {status_code or 'unknown status'}",
                context={"direction": direction, "status_code": status_code},
            ) from exc
        except httpx.RequestError as exc:
            logger.error(
                "Failed to reach Basic MRP %s endpoint",
                direction,
                extra={"error": str(exc), "item_id": item_id},
            )
            raise PlanningServiceError(
                "MRP service is unreachable",
                context={"direction": direction},
            ) from exc
        except ValueError as exc:
            logger.error("Invalid JSON returned from MRP %s endpoint", direction, exc_info=True)
            raise PlanningServiceError("MRP service returned invalid payload") from exc

        values = payload.get("values") or payload.get("value") or []
        if not isinstance(values, list):
            logger.warning(
                "Unexpected payload format from MRP %s endpoint",
                direction,
                extra={"item_id": item_id, "payload_type": type(values)},
            )
            return []
        return values

    def _build_inbound_events(
        self,
        rows: List[Dict[str, Any]],
    ) -> List[Tuple[date, Decimal, Optional[str]]]:
        events: List[Tuple[date, Decimal, Optional[str]]] = []
        for row in rows:
            event_date = self._parse_iso_date(
                row.get("expectedReceiptDate")
                or row.get("earliestRequired")
                or row.get("dateGet")
                or row.get("orderDate")
            )
            if not event_date:
                continue

            if row.get("quantityToReceive") is None:
                continue

            quantity = self._extract_decimal(row, ["quantityToReceive"])
            if quantity <= DecimalZero:
                continue
            job = self._extract_job_reference(row)
            events.append((event_date, quantity, job))
        return events

    def _build_outbound_events(
        self,
        rows: List[Dict[str, Any]],
        *,
        exclude_minimum_stock: bool,
    ) -> List[Tuple[date, Decimal, Optional[str]]]:
        events: List[Tuple[date, Decimal, Optional[str]]] = []
        for row in rows:
            event_date = self._parse_iso_date(row.get("needDate") or row.get("orderDate"))
            if not event_date:
                continue

            job = self._extract_job_reference(row)
            if exclude_minimum_stock and job and job.strip().upper() == "MINIMUM STOCK":
                continue

            quantity = self._extract_decimal(row, ["qtyFilled"])
            if quantity <= DecimalZero:
                continue
            events.append((event_date, quantity, job))
        return events

    def _build_timeline(
        self,
        inbound_events: List[Tuple[date, Decimal, Optional[str]]],
        outbound_events: List[Tuple[date, Decimal, Optional[str]]],
        starting_inventory: Decimal,
        today: date,
    ) -> List[ItemAvailabilityTimelineEntry]:
        buckets: Dict[date, Dict[str, Any]] = defaultdict(
            lambda: {
                "incoming": DecimalZero,
                "outgoing": DecimalZero,
                "incoming_jobs": [],
                "outgoing_jobs": [],
            }
        )

        for event_date, qty, job in inbound_events:
            period = self._month_start(event_date)
            bucket = buckets[period]
            bucket["incoming"] += qty
            if job:
                bucket["incoming_jobs"].append(job)

        for event_date, qty, job in outbound_events:
            period = self._month_start(event_date)
            bucket = buckets[period]
            bucket["outgoing"] += qty
            if job:
                bucket["outgoing_jobs"].append(job)

        current_period = self._month_start(today)
        periods = sorted({current_period, *buckets.keys()})

        projected = starting_inventory
        timeline: List[ItemAvailabilityTimelineEntry] = []
        for period in periods:
            bucket = buckets.get(period)
            incoming = bucket["incoming"] if bucket else DecimalZero
            outgoing = bucket["outgoing"] if bucket else DecimalZero
            incoming_jobs = list(bucket["incoming_jobs"]) if bucket else []
            outgoing_jobs = list(bucket["outgoing_jobs"]) if bucket else []
            projected = projected + incoming - outgoing
            timeline.append(
                ItemAvailabilityTimelineEntry(
                    period_start=period,
                    incoming_qty=incoming,
                    outgoing_qty=outgoing,
                    projected_available=projected,
                    incoming_jobs=incoming_jobs,
                    outgoing_jobs=outgoing_jobs,
                )
            )
        return timeline

    @staticmethod
    def _parse_iso_date(value: Any) -> date | None:
        if not value:
            return None

        if isinstance(value, date):
            return value

        text = str(value)
        if text.startswith(("0001-01-01", "1753-01-01")):
            return None

        # Handle trailing Z to comply with datetime.fromisoformat
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"

        try:
            return datetime.fromisoformat(text).date()
        except ValueError:
            return None

    @staticmethod
    def _extract_decimal(payload: Dict[str, Any], fields: Iterable[str]) -> Decimal:
        for field in fields:
            raw_value = payload.get(field)
            if raw_value in (None, "", []):
                continue
            try:
                value = Decimal(str(raw_value))
            except (ArithmeticError, ValueError, TypeError):
                continue
            if value != DecimalZero:
                return value
        return DecimalZero

    @staticmethod
    def _month_start(day: date) -> date:
        return date(day.year, day.month, 1)

    @staticmethod
    def _extract_job_reference(row: Dict[str, Any]) -> Optional[str]:
        for field in ("jobNo", "job", "jobNoRef", "jobNumber"):
            value = row.get(field)
            if value:
                text = str(value).strip()
                if text:
                    return text
        return None

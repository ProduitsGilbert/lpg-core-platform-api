"""Service helpers for interacting with the Advanced MRP monitoring endpoint."""

from __future__ import annotations

import io
import logging
from typing import List, Optional

import httpx
import logfire
from openpyxl import Workbook

from app.settings import settings
from .models import ProductionOrder, ProductionOrderCollection, ProductionOrderResult

logger = logging.getLogger(__name__)


class AdvancedMRPService:
    """Fetch and transform production order monitoring data."""

    def __init__(self) -> None:
        self._base_url = settings.toolkit_base_url.rstrip("/")
        self._resource_path = "/api/mrp/AdvancedMRP/GetMonitoring_ProductionOrder"
        self._headers = {"accept": "*/*"}

    async def fetch_production_orders(
        self,
        *,
        critical: Optional[bool] = None,
        prod_order_no: Optional[str] = None,
        job_no: Optional[str] = None,
    ) -> ProductionOrderResult:
        """
        Retrieve production orders from the upstream Advanced MRP service.

        Args:
            critical: Optional flag to forward to the upstream API.
            prod_order_no: Optional substring filter applied locally.
            job_no: Optional substring filter applied locally.

        Returns:
            ProductionOrderResult with the original upstream count and locally filtered orders.
        """
        params: dict[str, str] = {}
        if critical is not None:
            params["critical"] = str(critical).lower()

        url = f"{self._base_url}{self._resource_path}"
        span_kwargs = {
            "url": url,
            "critical": params.get("critical"),
            "prod_order_no": prod_order_no,
            "job_no": job_no,
        }

        try:
            with logfire.span("advanced_mrp.fetch_orders", **span_kwargs):
                async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
                    response = await client.get(
                        url,
                        headers=self._headers,
                        params=params or None,
                    )
                response.raise_for_status()
                payload = ProductionOrderCollection.model_validate(response.json())
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code if exc.response else "unknown"
            body = exc.response.text[:500] if exc.response and exc.response.text else ""
            logger.error(
                "Advanced MRP API returned HTTP error",
                extra={"status_code": status, "body": body, **span_kwargs},
            )
            raise
        except httpx.RequestError as exc:
            logger.error(
                "Failed to reach Advanced MRP API",
                extra={"error": str(exc), **span_kwargs},
            )
            raise

        filtered_orders = self._apply_filters(
            payload.values,
            prod_order_no=prod_order_no,
            job_no=job_no,
        )

        return ProductionOrderResult(
            total_count=payload.count,
            orders=filtered_orders,
        )

    def build_excel(self, orders: List[ProductionOrder]) -> bytes:
        """
        Create an Excel workbook containing the provided production orders.

        Args:
            orders: List of production orders to include.

        Returns:
            Workbook serialized as bytes.
        """
        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = "Production Orders"

        headers = [
            "Production Order",
            "Job No",
            "Description",
            "Quantity",
            "Remaining Quantity",
            "Pct Done",
            "Critical",
            "Routing",
            "Start Date",
            "End Date",
            "Date Retrieved",
            "Qty Disponible",
            "Qty Unused",
        ]
        worksheet.append(headers)

        for order in orders:
            worksheet.append(
                [
                    order.prod_order_no,
                    order.job_no,
                    order.description,
                    order.quantity,
                    order.remaining_quantity,
                    order.pct_done,
                    "Yes" if order.critical else "No",
                    order.routing_no,
                    order.starting_date,
                    order.ending_date,
                    order.date_get,
                    order.qty_disponible,
                    order.qty_unused,
                ]
            )

        # Autosize columns based on header/values lengths
        for column_cells in worksheet.columns:
            max_length = max(len(str(cell.value)) if cell.value is not None else 0 for cell in column_cells)
            worksheet.column_dimensions[column_cells[0].column_letter].width = min(max_length + 2, 60)

        buffer = io.BytesIO()
        workbook.save(buffer)
        buffer.seek(0)
        return buffer.read()

    @staticmethod
    def _apply_filters(
        orders: List[ProductionOrder],
        *,
        prod_order_no: Optional[str],
        job_no: Optional[str],
    ) -> List[ProductionOrder]:
        filtered = orders

        if prod_order_no:
            needle = prod_order_no.strip().lower()
            filtered = [
                order
                for order in filtered
                if order.prod_order_no and needle in order.prod_order_no.lower()
            ]

        if job_no:
            needle = job_no.strip().lower()
            filtered = [
                order
                for order in filtered
                if AdvancedMRPService._matches_job(order, needle)
            ]

        return filtered

    @staticmethod
    def _matches_job(order: ProductionOrder, needle: str) -> bool:
        """Check if the order or its attributions match the requested job."""
        if order.job_no and needle in order.job_no.lower():
            return True

        for entry in order.attribution_to_out:
            if isinstance(entry, dict):
                job_value = str(entry.get("job", "")).lower()
            else:
                job_value = str(entry).lower()

            if job_value and needle in job_value:
                return True

        return False

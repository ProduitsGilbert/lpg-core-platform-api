"""
Production-focused service for retrieving BOM cost shares and routing costs.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Dict, Iterable, List, Optional, Set

import logfire

from app.adapters.erp_client import ERPClient
from app.domain.erp.models import (
    ProductionBomCostShareLine,
    ProductionBomCostShareResponse,
    ProductionItemInfo,
    ProductionRoutingCostResponse,
    ProductionRoutingLineCost,
)
from app.errors import ERPError, ERPNotFound


def _to_decimal(value) -> Decimal:
    try:
        return Decimal(str(value or "0"))
    except (InvalidOperation, ValueError, TypeError):
        return Decimal("0")


class ProductionService:
    """Service orchestrating Business Central production data retrieval."""

    def __init__(self, *, erp_client: Optional[ERPClient] = None) -> None:
        self._client = erp_client or ERPClient()
        self._work_center_cache: Dict[str, Dict[str, object]] = {}
        self._item_cache: Dict[str, Dict[str, object]] = {}

    async def get_item_info(self, item_no: str) -> ProductionItemInfo:
        """Return minimal production-facing item info (routing + BOM)."""
        item = await self._client.get_item(item_no)
        if not item:
            raise ERPNotFound("Item", item_no)

        return ProductionItemInfo(
            item_no=item_no,
            description=item.get("Description"),
            routing_no=(item.get("Routing_No") or "").strip() or None,
            production_bom_no=(item.get("Production_BOM_No") or "").strip() or None,
            base_unit_of_measure=item.get("Base_Unit_of_Measure"),
            unit_cost=_to_decimal(item.get("Unit_Cost")),
            unit_price=_to_decimal(item.get("Unit_Price")),
        )

    async def get_bom_cost_shares(self, item_no: str) -> ProductionBomCostShareResponse:
        """
        Return cost share using BOM component lines only (do not call BOM_CostShares).
        This avoids long-running/unsupported BC worksheet calculations.
        """
        item_info = await self.get_item_info(item_no)

        if not item_info.production_bom_no:
            raise ERPError(
                "Item is not linked to a production BOM",
                context={"item_id": item_no},
            )

        mapped = await self._build_cost_share_from_components(item_info.production_bom_no)

        return ProductionBomCostShareResponse(
            item_no=item_info.item_no,
            routing_no=item_info.routing_no,
            production_bom_no=item_info.production_bom_no,
            lines=mapped,
        )

    def _map_cost_share_row(self, raw: Dict[str, object]) -> ProductionBomCostShareLine:
        return ProductionBomCostShareLine(
            type=(raw.get("Type") or "").strip(),
            no=(raw.get("No") or "").strip(),
            description=raw.get("Description"),
            qty_per_parent=_to_decimal(raw.get("Qty_per_Parent")),
            qty_per_top_item=_to_decimal(raw.get("Qty_per_Top_Item")),
            qty_per_bom_line=_to_decimal(raw.get("Qty_per_BOM_Line")),
            unit_of_measure_code=raw.get("Unit_of_Measure_Code"),
            bom_unit_of_measure_code=raw.get("BOM_Unit_of_Measure_Code"),
            replenishment_system=raw.get("Replenishment_System"),
            unit_cost=_to_decimal(raw.get("Unit_Cost")),
            rolled_up_material_cost=_to_decimal(raw.get("Rolled_up_Material_Cost")),
            rolled_up_capacity_cost=_to_decimal(raw.get("Rolled_up_Capacity_Cost")),
            rolled_up_subcontracted_cost=_to_decimal(raw.get("Rolled_up_Subcontracted_Cost")),
            rolled_up_mfg_ovhd_cost=_to_decimal(raw.get("Rolled_up_Mfg_Ovhd_Cost")),
            rolled_up_capacity_ovhd_cost=_to_decimal(raw.get("Rolled_up_Capacity_Ovhd_Cost")),
            rolled_up_scrap_cost=_to_decimal(raw.get("Rolled_up_Scrap_Cost")),
            total_cost=_to_decimal(raw.get("Total_Cost")),
        )

    async def _build_cost_share_from_components(
        self, production_bom_no: str
    ) -> List[ProductionBomCostShareLine]:
        """Fallback: derive material costs from BOM component lines."""
        raw_lines = await self._client.get_bom_component_lines(production_bom_no)
        mapped: List[ProductionBomCostShareLine] = []
        for raw in raw_lines or []:
            line_type = (raw.get("Type") or "").strip().lower()
            if line_type != "item":
                continue
            item_no = (raw.get("No") or "").strip()
            if not item_no:
                continue
            qty = _to_decimal(raw.get("Quantity_per"))
            item_payload = await self._get_item_cached(item_no)
            unit_cost = _to_decimal(item_payload.get("Unit_Cost")) if item_payload else Decimal("0")
            total_cost = (unit_cost * qty).quantize(Decimal("0.0001"))

            mapped.append(
                ProductionBomCostShareLine(
                    type=raw.get("Type"),
                    no=item_no,
                    description=raw.get("Description"),
                    qty_per_parent=qty,
                    qty_per_top_item=qty,
                    qty_per_bom_line=qty,
                    unit_of_measure_code=raw.get("Unit_of_Measure_Code"),
                    bom_unit_of_measure_code=raw.get("BOM_Unit_of_Measure_Code"),
                    replenishment_system=raw.get("Replenishment_System"),
                    unit_cost=unit_cost,
                    rolled_up_material_cost=total_cost,
                    rolled_up_capacity_cost=Decimal("0"),
                    rolled_up_subcontracted_cost=Decimal("0"),
                    rolled_up_mfg_ovhd_cost=Decimal("0"),
                    rolled_up_capacity_ovhd_cost=Decimal("0"),
                    rolled_up_scrap_cost=Decimal("0"),
                    total_cost=total_cost,
                )
            )
        return mapped

    async def get_routing_costs(self, item_no: str) -> ProductionRoutingCostResponse:
        """
        Retrieve routing lines for an item and cost them using work center rates.
        """
        item_info = await self.get_item_info(item_no)
        routing_no = item_info.routing_no
        if not routing_no:
            raise ERPError(
                "Item is missing Routing_No",
                context={"item_no": item_no},
            )

        raw_lines = await self._client.get_bom_routing_lines(routing_no)
        if not raw_lines:
            raise ERPError(
                "No routing lines returned for routing",
                context={"routing_no": routing_no},
            )

        work_centers_needed: Set[str] = set()
        for line in raw_lines:
            type_val = (line.get("Type") or "").lower()
            if "work" in type_val and "center" in type_val:
                no_val = (
                    line.get("WorkCenterNo")
                    or line.get("Work_Center_No")
                    or line.get("No")
                    or ""
                ).strip()
                if no_val:
                    work_centers_needed.add(no_val)

        work_center_rates = await self._load_work_center_rates(work_centers_needed)

        mapped_lines: List[ProductionRoutingLineCost] = []
        total_setup = Decimal("0")
        total_run = Decimal("0")

        for raw in raw_lines:
            type_val = (raw.get("Type") or "").strip()
            work_center_no = (
                (
                    raw.get("WorkCenterNo")
                    or raw.get("Work_Center_No")
                    or raw.get("No")
                    or ""
                )
                .strip()
                or None
            )

            setup_minutes = _to_decimal(raw.get("SetupTime") or raw.get("Setup_Time"))
            run_minutes = _to_decimal(raw.get("RunTime") or raw.get("Run_Time"))

            rate_per_minute = Decimal("0")
            if work_center_no and work_center_no in work_center_rates:
                rate_per_minute = work_center_rates[work_center_no]

            setup_cost = (setup_minutes * rate_per_minute).quantize(Decimal("0.0001"))
            run_cost = (run_minutes * rate_per_minute).quantize(Decimal("0.0001"))

            total_setup += setup_cost
            total_run += run_cost

            mapped_lines.append(
                ProductionRoutingLineCost(
                    routing_no=routing_no,
                    operation_no=(raw.get("Operation_No") or raw.get("OperationNo") or "").strip() or None,
                    sequence_no=raw.get("Sequence"),
                    type=type_val,
                    work_center_no=work_center_no,
                    work_center_description=raw.get("Work_Center_Name")
                    or raw.get("Work_Center_Description")
                    or raw.get("WorkCenterDescription")
                    or raw.get("Description"),
                    description=raw.get("Description"),
                    quantity_per=_to_decimal(raw.get("Quantity_per") or raw.get("QuantityPer")),
                    unit_of_measure_code=raw.get("Unit_of_Measure_Code"),
                    setup_time_minutes=setup_minutes,
                    run_time_minutes=run_minutes,
                    cost_per_minute=rate_per_minute,
                    setup_cost=setup_cost,
                    run_cost=run_cost,
                    total_cost=setup_cost + run_cost,
                )
            )

        return ProductionRoutingCostResponse(
            item_no=item_info.item_no,
            routing_no=routing_no,
            production_bom_no=item_info.production_bom_no,
            lines=mapped_lines,
            total_setup_cost=total_setup,
            total_run_cost=total_run,
            total_cost=total_setup + total_run,
        )

    async def _load_work_center_rates(self, work_center_nos: Iterable[str]) -> Dict[str, Decimal]:
        """Return per-minute cost rates for the provided work centers."""
        rates: Dict[str, Decimal] = {}
        for wc_no in work_center_nos:
            if not wc_no:
                continue
            if wc_no in self._work_center_cache:
                record = self._work_center_cache[wc_no]
            else:
                record = await self._client.get_work_center(wc_no)
                if record:
                    self._work_center_cache[wc_no] = record
            if not record:
                continue
            unit_cost = _to_decimal(record.get("Unit_Cost"))
            if unit_cost <= 0:
                continue
            # Business Central Work Center Unit Cost is typically per hour; convert to per-minute.
            rate_per_minute = (unit_cost / Decimal("60")).quantize(Decimal("0.0001"))
            rates[wc_no] = rate_per_minute
        return rates

    async def _get_item_cached(self, item_no: str) -> Dict[str, object]:
        if item_no in self._item_cache:
            return self._item_cache[item_no]
        payload = await self._client.get_item(item_no)
        if payload:
            self._item_cache[item_no] = payload
        return payload or {}

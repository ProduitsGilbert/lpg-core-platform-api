"""
High-level service that wires Business Central BOM data into the tariff calculator.
"""

from __future__ import annotations

import logging
from typing import Dict, Iterable, List, Optional, Sequence, Set

from fastapi.concurrency import run_in_threadpool

from migration.tariff_calculator_lib import (
    BOMLine,
    CountryInfo,
    TariffCalculationResult,
    TariffCalculator,
    format_tariff_report,
)

from app.adapters.erp_client import ERPClient
from app.domain.erp.models import (
    TariffCalculationResponse,
    TariffMaterialResponse,
    TariffSummaryResponse,
)
from app.errors import ERPError, ERPNotFound, DatabaseError
from app.integrations.cedule_repository import (
    MillTestCertificate,
    MillTestCertificateRepository,
)

logger = logging.getLogger(__name__)


class TariffCalculationService:
    """Fetch BOM data, run the tariff calculator, and format the API payload."""

    def __init__(
        self,
        *,
        erp_client: Optional[ERPClient] = None,
        certificate_repo: Optional[MillTestCertificateRepository] = None,
    ) -> None:
        self._erp_client = erp_client or ERPClient()
        self._certificate_repo = certificate_repo or MillTestCertificateRepository()
        self._item_cache: Dict[str, Dict[str, object]] = {}
        self._bom_cache: Dict[str, List[Dict[str, object]]] = {}

    async def calculate(self, item_id: str) -> TariffCalculationResponse:
        """Run the tariff calculator for the provided item."""
        item = await self._erp_client.get_item(item_id)
        if not item:
            raise ERPNotFound("Item", item_id)
        self._item_cache[item_id] = item

        production_bom_no = (item.get("Production_BOM_No") or "").strip()
        if not production_bom_no:
            raise ERPError(
                "Item is not linked to a production BOM",
                context={"item_id": item_id},
            )

        flattened_lines = await self._expand_bom(production_bom_no, 1.0, set())
        if not flattened_lines:
            raise ERPError(
                "No BOM component lines were returned from Business Central",
                context={"item_id": item_id, "bom_no": production_bom_no},
            )

        component_numbers = sorted(
            {(line.get("No") or "").strip() for line in flattened_lines if line.get("No")}
        )
        component_items: Dict[str, Dict[str, object]] = {}
        for item_no in component_numbers:
            component_items[item_no] = await self._get_item_cached(item_no) or {}

        bom_lines = self._build_bom_lines(flattened_lines, component_items)
        if not bom_lines:
            raise ERPError(
                "No BOM entries were eligible for tariff calculation",
                context={"item_id": item_id, "bom_no": production_bom_no},
            )

        cost_map = self._build_cost_map(component_items)
        certificates = await self._fetch_certificates(component_numbers + [item_id])
        country_map = {
            part: CountryInfo(
                melt_and_pour=cert.country_of_melt_and_pour,
                manufacture=cert.country_of_manufacture,
            )
            for part, cert in certificates.items()
        }

        calculator = TariffCalculator(
            cost_provider=lambda part: cost_map.get(part, 0.0),
            country_provider=lambda part: country_map.get(part),
        )
        result = calculator.calculate(item_id, bom_lines)
        if result.error:
            raise ERPError(result.error, context={"item_id": item_id})
        if result.summary is None:
            raise ERPError(
                "Tariff calculator did not produce a summary",
                context={"item_id": item_id},
            )

        parent_certificate = certificates.get(item_id)
        return self._build_response(
            item_id=item_id,
            production_bom_no=production_bom_no,
            result=result,
            parent_certificate=parent_certificate,
        )

    async def _expand_bom(
        self,
        production_bom_no: str,
        multiplier: float,
        visited: Set[str],
    ) -> List[Dict[str, object]]:
        """Recursively expand nested BOMs into leaf component lines."""
        if production_bom_no in visited:
            logger.warning(
                "Detected recursive BOM reference; skipping nested expansion",
                extra={"bom_no": production_bom_no},
            )
            return []

        visited.add(production_bom_no)
        raw_lines = await self._get_bom_lines_cached(production_bom_no)
        component_lines = self._filter_component_lines(raw_lines)
        collected: List[Dict[str, object]] = []

        for line in component_lines:
            item_no = (line.get("No") or "").strip()
            if not item_no:
                continue

            quantity = _to_float(line.get("Quantity_per")) * multiplier
            if quantity <= 0:
                continue

            line_copy = dict(line)
            line_copy["Quantity_per"] = quantity

            item_payload = await self._get_item_cached(item_no)
            nested_bom = (
                (item_payload.get("Production_BOM_No") or "").strip() if item_payload else ""
            )

            if nested_bom:
                collected.extend(await self._expand_bom(nested_bom, quantity, visited))
            else:
                collected.append(line_copy)

        visited.remove(production_bom_no)
        return collected

    async def _get_bom_lines_cached(self, bom_no: str) -> List[Dict[str, object]]:
        if bom_no in self._bom_cache:
            return self._bom_cache[bom_no]
        lines = await self._erp_client.get_bom_component_lines(bom_no)
        self._bom_cache[bom_no] = lines
        return lines

    @staticmethod
    def _filter_component_lines(raw_lines: Optional[List[Dict[str, object]]]) -> List[Dict[str, object]]:
        """Keep only inventory component lines with a valid item number."""
        filtered: List[Dict[str, object]] = []
        if not raw_lines:
            return filtered
        for line in raw_lines:
            line_type = (line.get("Type") or "").strip().lower()
            item_no = (line.get("No") or "").strip()
            if line_type != "item" or not item_no:
                continue
            filtered.append(line)
        return filtered

    async def _get_item_cached(self, item_no: str) -> Optional[Dict[str, object]]:
        if item_no in self._item_cache:
            return self._item_cache[item_no]
        try:
            item = await self._erp_client.get_item(item_no)
        except ERPError:
            raise
        except Exception as exc:  # pragma: no cover - defensive logging path
            logger.warning(
                "Failed to load item details during tariff calculation",
                extra={"item_no": item_no, "error": str(exc)},
            )
            item = None
        if item:
            self._item_cache[item_no] = item
        return item

    def _build_bom_lines(
        self,
        component_lines: Sequence[Dict[str, object]],
        component_items: Dict[str, Dict[str, object]],
    ) -> List[BOMLine]:
        """Convert raw BOM rows into tariff calculator BOMLine objects."""
        bom_lines: List[BOMLine] = []
        for line in component_lines:
            item_no = (line.get("No") or "").strip()
            component = component_items.get(item_no, {})
            description = (
                (line.get("Description") or "")
                or (component.get("Description") or "")
            ).strip()
            quantity = _to_float(line.get("Quantity_per"))
            if quantity <= 0:
                continue
            bom_lines.append(
                BOMLine(
                    item_no=item_no,
                    description=description,
                    quantity=quantity,
                    scrap_percent=_to_float(line.get("Scrap_Percent")),
                    calculation_formula=(line.get("Calculation_Formula") or "").strip(),
                    length=_to_float(line.get("Length")),
                    width=_to_float(line.get("Width")),
                    depth=_to_float(line.get("Depth")),
                    vendor_no=(component.get("Vendor_No") or "") or None,
                    vendor_item_no=(component.get("Vendor_Item_No") or "") or None,
                )
            )
        return bom_lines

    @staticmethod
    def _build_cost_map(component_items: Dict[str, Dict[str, object]]) -> Dict[str, float]:
        cost_map: Dict[str, float] = {}
        for item_no, payload in component_items.items():
            cost_map[item_no] = _to_float(payload.get("Standard_Cost"))
        return cost_map

    async def _fetch_certificates(self, part_numbers: Iterable[str]) -> Dict[str, MillTestCertificate]:
        """Load mill test certificate data (if configured)."""
        certificates: Dict[str, MillTestCertificate] = {}
        if not self._certificate_repo or not self._certificate_repo.is_configured:
            return certificates

        unique_parts = sorted({part for part in part_numbers if part})
        for part in unique_parts:
            try:
                certificate = await run_in_threadpool(
                    self._certificate_repo.get_latest_certificate,
                    part,
                )
            except DatabaseError as exc:
                logger.warning(
                    "Cedule mill test lookup failed; continuing without melt/pour data",
                    extra={"error": str(exc)},
                )
                break
            else:
                if certificate:
                    certificates[part] = certificate
        return certificates

    def _build_response(
        self,
        *,
        item_id: str,
        production_bom_no: str,
        result: TariffCalculationResult,
        parent_certificate: Optional[MillTestCertificate],
    ) -> TariffCalculationResponse:
        summary = result.summary
        assert summary is not None  # nosec: validated earlier

        materials = [
            TariffMaterialResponse(
                item_no=material.item_no,
                description=material.description,
                material_type=material.material_type,
                quantity=material.quantity,
                scrap_percent=material.scrap_percent,
                dimensions=dict(material.dimensions),
                weight_per_piece_lbs=material.weight_per_piece_lbs,
                weight_per_piece_kg=material.weight_per_piece_kg,
                total_weight_lbs=material.total_weight_lbs,
                total_weight_kg=material.total_weight_kg,
                total_with_scrap_lbs=material.total_with_scrap_lbs,
                total_with_scrap_kg=material.total_with_scrap_kg,
                standard_cost_cad=material.standard_cost_cad,
                total_cost_cad=material.total_cost_cad,
                total_cost_usd=material.total_cost_usd,
                vendor_no=material.vendor_no,
                vendor_item_no=material.vendor_item_no,
                country_of_melt_and_pour=material.country_of_melt_and_pour,
                country_of_manufacture=material.country_of_manufacture,
                note=material.note,
            )
            for material in result.materials
        ]

        summary_model = TariffSummaryResponse(
            total_materials=summary.total_materials,
            calculated_materials=summary.calculated_materials,
            total_weight_kg=summary.total_weight_kg,
            total_weight_with_scrap_kg=summary.total_weight_with_scrap_kg,
            total_cost_cad=summary.total_cost_cad,
            total_cost_usd=summary.total_cost_usd,
            exchange_rate=summary.exchange_rate,
        )

        report = format_tariff_report(result)
        return TariffCalculationResponse(
            item_id=item_id,
            production_bom_no=production_bom_no,
            summary=summary_model,
            materials=materials,
            parent_country_of_melt_and_pour=(
                parent_certificate.country_of_melt_and_pour if parent_certificate else None
            ),
            parent_country_of_manufacture=(
                parent_certificate.country_of_manufacture if parent_certificate else None
            ),
            report=report or None,
        )


def _to_float(value: Optional[object]) -> float:
    if value is None:
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0

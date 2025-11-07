"""Self-contained tariff and steel weight calculator helper.

This module mirrors the key behaviour of ``data.tariff_calculator`` but removes
its runtime dependencies (pandas, logfire, Business Central helpers, SQL
helpers, etc.) so it can be dropped into another API service as-is.

Highlights
----------
* Pure Python (only depends on the standard library)
* Typed dataclasses that make integration into a FastAPI/Flask service easier
* Dependency injection hooks so callers can provide their own cost/country data
* Reusable text report formatter for quickly returning a human readable summary

Usage Example
-------------
>>> from tariff_calculator_lib import TariffCalculator, BOMLine
>>> calculator = TariffCalculator()
>>> bom_lines = [
...     BOMLine(item_no="123", description="ROUND BAR 2\" DIA", quantity=2,
...             calculation_formula="Length", length=18, scrap_percent=5.0),
... ]
>>> result = calculator.calculate("7001234", bom_lines)
>>> print(result.summary.total_weight_kg)
"""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Tuple

# ---------------------------------------------------------------------------
# Domain constants
# ---------------------------------------------------------------------------
# Steel density in pounds per cubic inch (490 lb/ft^3)
STEEL_DENSITY_LBS_PER_CU_IN = 0.2836

# Currency conversion (CAD -> USD). Make runtime configurable when integrating
# into a real API so that this rate can be refreshed automatically.
CAD_TO_USD_RATE = 0.74


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------
@dataclass(slots=True)
class CountryInfo:
    """Represents provenance fields required for customs paperwork."""

    melt_and_pour: Optional[str] = None
    manufacture: Optional[str] = None


@dataclass(slots=True)
class BOMLine:
    """Lean representation of a Bill Of Materials row used by the calculator."""

    item_no: str
    description: str = ""
    quantity: float = 1.0
    scrap_percent: float = 0.0
    calculation_formula: str = ""
    length: float = 0.0  # Inches when calculation_formula == "Length"
    width: float = 0.0
    depth: float = 0.0
    vendor_no: Optional[str] = None
    vendor_item_no: Optional[str] = None


@dataclass(slots=True)
class MaterialBreakdown:
    """Full weight/cost calculation for an individual BOM component."""

    item_no: str
    description: str
    material_type: str
    quantity: float
    scrap_percent: float
    dimensions: Dict[str, float]
    weight_per_piece_lbs: float
    weight_per_piece_kg: float
    total_weight_lbs: float
    total_weight_kg: float
    total_with_scrap_lbs: float
    total_with_scrap_kg: float
    standard_cost_cad: float
    total_cost_cad: float
    total_cost_usd: float
    vendor_no: Optional[str] = None
    vendor_item_no: Optional[str] = None
    country_of_melt_and_pour: Optional[str] = None
    country_of_manufacture: Optional[str] = None
    note: Optional[str] = None

    def to_dict(self) -> Dict[str, object]:
        """Serialize into a dict (handy for JSON responses)."""

        return {
            "Item No": self.item_no,
            "Description": self.description,
            "Type": self.material_type,
            "Quantity": self.quantity,
            "Scrap %": self.scrap_percent,
            "Dimensions": self.dimensions,
            "Weight/Piece (lbs)": round(self.weight_per_piece_lbs, 3),
            "Weight/Piece (kg)": round(self.weight_per_piece_kg, 3),
            "Total Weight (lbs)": round(self.total_weight_lbs, 3),
            "Total Weight (kg)": round(self.total_weight_kg, 3),
            "Total with Scrap (lbs)": round(self.total_with_scrap_lbs, 3),
            "Total with Scrap (kg)": round(self.total_with_scrap_kg, 3),
            "Standard Cost (CAD)": round(self.standard_cost_cad, 2),
            "Total Cost (CAD)": round(self.total_cost_cad, 2),
            "Total Cost (USD)": round(self.total_cost_usd, 2),
            "Vendor": self.vendor_no,
            "Vendor Item": self.vendor_item_no,
            "Country of Melt and Pour": self.country_of_melt_and_pour,
            "Country of Manufacture": self.country_of_manufacture,
            "Note": self.note,
        }


@dataclass(slots=True)
class TariffSummary:
    parent_item: str
    total_materials: int
    calculated_materials: int
    total_weight_kg: float
    total_weight_with_scrap_kg: float
    total_cost_cad: float
    total_cost_usd: float
    exchange_rate: float = CAD_TO_USD_RATE


@dataclass(slots=True)
class TariffCalculationResult:
    parent_item: str
    materials: List[MaterialBreakdown] = field(default_factory=list)
    summary: Optional[TariffSummary] = None
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Helper type aliases for dependency injection
# ---------------------------------------------------------------------------
CostProvider = Callable[[str], float]
CountryProvider = Callable[[str], Optional[CountryInfo]]


def _default_cost_provider(_: str) -> float:
    return 0.0


def _default_country_provider(_: str) -> Optional[CountryInfo]:
    return None


# ---------------------------------------------------------------------------
# Tariff calculator implementation
# ---------------------------------------------------------------------------
class TariffCalculator:
    """Computes steel weights/costs for a set of BOM lines."""

    def __init__(
        self,
        *,
        steel_density_lbs_per_cu_in: float = STEEL_DENSITY_LBS_PER_CU_IN,
        cad_to_usd_rate: float = CAD_TO_USD_RATE,
        cost_provider: CostProvider = _default_cost_provider,
        country_provider: CountryProvider = _default_country_provider,
    ) -> None:
        self.density = steel_density_lbs_per_cu_in
        self.cad_to_usd_rate = cad_to_usd_rate
        self.cost_provider = cost_provider
        self.country_provider = country_provider

    # -- public API ---------------------------------------------------------
    def calculate(self, parent_item: str, bom_lines: Sequence[BOMLine]) -> TariffCalculationResult:
        """Return tariff info for every BOM component."""

        normalized_parent = parent_item.strip()
        if not normalized_parent:
            return TariffCalculationResult(parent_item=parent_item, error="Parent item cannot be blank")

        if not bom_lines:
            return TariffCalculationResult(
                parent_item=normalized_parent,
                error="No BOM data supplied",
            )

        materials: List[MaterialBreakdown] = []
        total_weight_kg = 0.0
        total_weight_with_scrap_kg = 0.0
        total_cost_cad = 0.0
        total_cost_usd = 0.0

        for line in bom_lines:
            breakdown = self._calculate_material(line)
            if breakdown:
                materials.append(breakdown)
                total_weight_kg += breakdown.total_weight_kg
                total_weight_with_scrap_kg += breakdown.total_with_scrap_kg
                total_cost_cad += breakdown.total_cost_cad
                total_cost_usd += breakdown.total_cost_usd
            else:
                placeholder = self._build_placeholder(line)
                materials.append(placeholder)
                total_cost_cad += placeholder.total_cost_cad
                total_cost_usd += placeholder.total_cost_usd

        summary = TariffSummary(
            parent_item=normalized_parent,
            total_materials=len(materials),
            calculated_materials=sum(1 for m in materials if m.weight_per_piece_kg > 0),
            total_weight_kg=round(total_weight_kg, 3),
            total_weight_with_scrap_kg=round(total_weight_with_scrap_kg, 3),
            total_cost_cad=round(total_cost_cad, 2),
            total_cost_usd=round(total_cost_usd, 2),
            exchange_rate=self.cad_to_usd_rate,
        )

        return TariffCalculationResult(parent_item=normalized_parent, materials=materials, summary=summary)

    # -- internal helpers ---------------------------------------------------
    def _calculate_material(self, line: BOMLine) -> Optional[MaterialBreakdown]:
        material_type, dimensions = parse_material_description(line.description)

        calculation_formula = line.calculation_formula or ""
        quantity = float(line.quantity or 0)
        scrap_percent = float(line.scrap_percent or 0)
        scrap_multiplier = 1 + (scrap_percent / 100)

        length_from_bom = line.length if calculation_formula == "Length" else 0.0

        weight_per_piece_lbs = 0.0
        dims = dict(dimensions)  # copy so we can mutate safely

        if material_type == "round_bar" and "diameter" in dims:
            length = length_from_bom if length_from_bom > 0 else 1
            dims.setdefault("length", length)
            weight_per_piece_lbs = calculate_round_bar_weight(dims["diameter"], length, self.density)
        elif material_type == "plate":
            if line.width > 0:
                dims["width"] = line.width
            if line.length > 0:
                dims["length"] = line.length
            if line.depth > 0 and "thickness" not in dims:
                dims["thickness"] = line.depth
            if all(k in dims for k in ("thickness", "width", "length")):
                weight_per_piece_lbs = calculate_plate_weight(
                    dims["thickness"], dims["width"], dims["length"], self.density
                )
            else:
                return None
        elif material_type == "tube" and all(k in dims for k in ("outer_diameter", "wall_thickness")):
            length = length_from_bom if length_from_bom > 0 else 1
            dims.setdefault("length", length)
            weight_per_piece_lbs = calculate_tube_weight(
                dims["outer_diameter"], dims["wall_thickness"], length, self.density
            )
        elif material_type == "square_bar" and all(k in dims for k in ("width", "height")):
            length = length_from_bom if length_from_bom > 0 else 1
            dims.setdefault("length", length)
            weight_per_piece_lbs = calculate_square_bar_weight(dims["width"], dims["height"], length, self.density)

        if weight_per_piece_lbs <= 0:
            return None

        total_weight_lbs = weight_per_piece_lbs * quantity
        total_with_scrap_lbs = total_weight_lbs * scrap_multiplier

        weight_per_piece_kg = weight_per_piece_lbs * 0.453592
        total_weight_kg = total_weight_lbs * 0.453592
        total_with_scrap_kg = total_with_scrap_lbs * 0.453592

        standard_cost_cad = self.cost_provider(line.item_no)
        total_cost_cad = self._calculate_cost_cad(
            standard_cost_cad, quantity, scrap_multiplier, calculation_formula, length_from_bom
        )
        total_cost_usd = total_cost_cad * self.cad_to_usd_rate

        country_info = self.country_provider(line.item_no)

        return MaterialBreakdown(
            item_no=line.item_no,
            description=line.description,
            material_type=material_type,
            quantity=quantity,
            scrap_percent=scrap_percent,
            dimensions=dims,
            weight_per_piece_lbs=weight_per_piece_lbs,
            weight_per_piece_kg=weight_per_piece_kg,
            total_weight_lbs=total_weight_lbs,
            total_weight_kg=total_weight_kg,
            total_with_scrap_lbs=total_with_scrap_lbs,
            total_with_scrap_kg=total_with_scrap_kg,
            standard_cost_cad=standard_cost_cad,
            total_cost_cad=total_cost_cad,
            total_cost_usd=total_cost_usd,
            vendor_no=line.vendor_no,
            vendor_item_no=line.vendor_item_no,
            country_of_melt_and_pour=country_info.melt_and_pour if country_info else None,
            country_of_manufacture=country_info.manufacture if country_info else None,
        )

    def _calculate_cost_cad(
        self,
        standard_cost_cad: float,
        quantity: float,
        scrap_multiplier: float,
        calculation_formula: str,
        length_from_bom: float,
    ) -> float:
        if calculation_formula == "Length" and length_from_bom > 0:
            material_needed = length_from_bom * quantity * scrap_multiplier
            return standard_cost_cad * material_needed
        if calculation_formula == "Fixed Quantity":
            return standard_cost_cad * quantity
        return standard_cost_cad * quantity

    def _build_placeholder(self, line: BOMLine) -> MaterialBreakdown:
        standard_cost_cad = self.cost_provider(line.item_no)
        calculation_formula = line.calculation_formula or ""
        scrap_percent = float(line.scrap_percent or 0)
        scrap_multiplier = 1 + (scrap_percent / 100)
        length_from_bom = line.length if calculation_formula == "Length" else 0.0

        total_cost_cad = self._calculate_cost_cad(
            standard_cost_cad,
            float(line.quantity or 0),
            scrap_multiplier,
            calculation_formula,
            length_from_bom,
        )
        total_cost_usd = total_cost_cad * self.cad_to_usd_rate
        country_info = self.country_provider(line.item_no)

        return MaterialBreakdown(
            item_no=line.item_no,
            description=line.description,
            material_type="unknown",
            quantity=float(line.quantity or 0),
            scrap_percent=scrap_percent,
            dimensions={},
            weight_per_piece_lbs=0.0,
            weight_per_piece_kg=0.0,
            total_weight_lbs=0.0,
            total_weight_kg=0.0,
            total_with_scrap_lbs=0.0,
            total_with_scrap_kg=0.0,
            standard_cost_cad=standard_cost_cad,
            total_cost_cad=total_cost_cad,
            total_cost_usd=total_cost_usd,
            vendor_no=line.vendor_no,
            vendor_item_no=line.vendor_item_no,
            country_of_melt_and_pour=country_info.melt_and_pour if country_info else None,
            country_of_manufacture=country_info.manufacture if country_info else None,
            note="Weight calculation not available",
        )


# ---------------------------------------------------------------------------
# Weight calculation primitives
# ---------------------------------------------------------------------------
def calculate_round_bar_weight(diameter: float, length: float, density: float) -> float:
    radius = diameter / 2
    volume = 3.14159 * radius * radius * length
    return volume * density


def calculate_plate_weight(thickness: float, width: float, length: float, density: float) -> float:
    volume = thickness * width * length
    return volume * density


def calculate_tube_weight(outer_diameter: float, wall_thickness: float, length: float, density: float) -> float:
    outer_radius = outer_diameter / 2
    inner_radius = max(outer_radius - wall_thickness, 0)
    outer_volume = 3.14159 * outer_radius * outer_radius * length
    inner_volume = 3.14159 * inner_radius * inner_radius * length
    return (outer_volume - inner_volume) * density


def calculate_square_bar_weight(width: float, height: float, length: float, density: float) -> float:
    volume = width * height * length
    return volume * density


# ---------------------------------------------------------------------------
# Description parsing helpers
# ---------------------------------------------------------------------------
ROUND_BAR_TOKENS = ("BARRE RONDE", "ROUND BAR", "ROD")
PLATE_TOKENS = ("PLAQUE", "PLATE")
TUBE_TOKENS = ("TUBE", "PIPE")
SQUARE_BAR_TOKENS = ("CARRE", "SQUARE")


def parse_material_description(description: str) -> Tuple[str, Dict[str, float]]:
    """Guess material taxonomy + key dimensions from a free-form description."""

    text = _normalize_material_text(description.upper())
    dims: Dict[str, float] = {}
    material_type = "unknown"

    if any(token in text for token in ROUND_BAR_TOKENS):
        material_type = "round_bar"
        dims.update(_extract_round_bar_dims(text))
    elif any(token in text for token in PLATE_TOKENS):
        material_type = "plate"
        dims.update(_extract_plate_dims(text))
    elif any(token in text for token in TUBE_TOKENS):
        material_type = "tube"
        dims.update(_extract_tube_dims(text))
    elif any(token in text for token in SQUARE_BAR_TOKENS):
        material_type = "square_bar"
        dims.update(_extract_square_bar_dims(text))

    return material_type, {k: v for k, v in dims.items() if v > 0}


def _extract_round_bar_dims(text: str) -> Dict[str, float]:
    dims: Dict[str, float] = {}
    frac_match = re.search(r"(\d+)-(\d+)/(\d+)", text)
    if frac_match:
        whole, num, den = frac_match.groups()
        dims["diameter"] = _parse_numeric_token(f"{whole}-{num}/{den}") or 0.0
        return dims

    dec_match = re.search(r"([0-9./-]+)\s*(?:DIA|OD)", text)
    if dec_match:
        value = _parse_numeric_token(dec_match.group(1))
        if value:
            dims["diameter"] = value

    return dims


def _extract_plate_dims(text: str) -> Dict[str, float]:
    dims: Dict[str, float] = {}
    combo = re.search(r"([0-9./-]+)\s*[xX]\s*([0-9./-]+)\s*[xX]\s*([0-9./-]+)", text)
    if combo:
        values = [_parse_numeric_token(group) for group in combo.groups()]
        if all(values):
            dims["thickness"], dims["width"], dims["length"] = values  # type: ignore
        return dims

    thickness = re.search(r"(?:PLAQUE|PLATE)\s+([0-9./-]+)", text)
    if thickness:
        value = _parse_numeric_token(thickness.group(1))
        if value:
            dims["thickness"] = value
    else:
        thickness = re.search(r"([0-9./-]+)\s*\"?\s*(?:THICK|EPAIS)", text)
        if thickness:
            value = _parse_numeric_token(thickness.group(1))
            if value:
                dims["thickness"] = value

    combo_two = re.search(r"([0-9./-]+)\s*[xX]\s*([0-9./-]+)", text)
    if combo_two and "thickness" in dims:
        first = _parse_numeric_token(combo_two.group(1))
        second = _parse_numeric_token(combo_two.group(2))
        if first and second:
            dims.setdefault("width", first)
            dims.setdefault("length", second)

    width = re.search(r"([0-9./-]+)\s*\"?\s*(?:WIDE|LARGE)", text)
    if width:
        value = _parse_numeric_token(width.group(1))
        if value:
            dims["width"] = value
    length = re.search(r"([0-9./-]+)\s*\"?\s*(?:LONG|LENGTH)", text)
    if length:
        value = _parse_numeric_token(length.group(1))
        if value:
            dims["length"] = value

    return dims


def _extract_tube_dims(text: str) -> Dict[str, float]:
    dims: Dict[str, float] = {}
    od = re.search(r"([0-9./-]+)\s*(?:OD|DIA)", text)
    if od:
        value = _parse_numeric_token(od.group(1))
        if value:
            dims["outer_diameter"] = value
    wall = re.search(r"([0-9./-]+)\s*(?:WALL|EPAIS)", text)
    if wall:
        value = _parse_numeric_token(wall.group(1))
        if value:
            dims["wall_thickness"] = value
    return dims


def _extract_square_bar_dims(text: str) -> Dict[str, float]:
    dims: Dict[str, float] = {}
    combo = re.search(r"([0-9./-]+)\s*[xX]\s*([0-9./-]+)", text)
    if combo:
        first = _parse_numeric_token(combo.group(1))
        second = _parse_numeric_token(combo.group(2))
        if first and second:
            dims["width"] = first
            dims["height"] = second
        return dims

    single = re.search(r"([0-9./-]+)", text)
    if single:
        value = _parse_numeric_token(single.group(1))
        if value is None:
            return dims
        dims["width"] = value
        dims["height"] = value
    return dims


# ---------------------------------------------------------------------------
# Reporting helpers
# ---------------------------------------------------------------------------
def format_tariff_report(result: TariffCalculationResult) -> str:
    """Render a fixed-width table similar to the existing API's output."""

    if result.error:
        return f"Error: {result.error}"
    if not result.summary:
        return "No summary available"

    summary = result.summary
    lines: List[str] = []

    lines.append("TARIFF/WEIGHT CALCULATION REPORT")
    lines.append(f"Parent Item: {summary.parent_item}")
    lines.append(f"Exchange Rate: 1 CAD = {summary.exchange_rate} USD")
    lines.append("=" * 120)
    lines.append("")

    header = f"{'Item No':<10} {'Description':<35} {'Qty':<6} {'Weight/Pc (kg)':<15} {'Total (kg)':<12} {'Cost CAD':<10} {'Cost USD':<10}"
    lines.append(header)
    lines.append("-" * len(header))

    for material in result.materials:
        lines.append(
            f"{material.item_no[:10]:<10} {material.description[:35]:<35} {material.quantity:<6.1f} "
            f"{material.weight_per_piece_kg:<15.3f} {material.total_weight_kg:<12.3f} "
            f"${material.total_cost_cad:<9.2f} ${material.total_cost_usd:<9.2f}"
        )
        if material.scrap_percent > 0 and material.total_with_scrap_kg != material.total_weight_kg:
            lines.append(
                f"{'':10} Scrap +{material.scrap_percent:.0f}% => {material.total_with_scrap_kg:.3f} kg"
            )
        if material.country_of_melt_and_pour:
            lines.append(f"{'':10} Country of Melt & Pour: {material.country_of_melt_and_pour}")
        if material.country_of_manufacture:
            lines.append(f"{'':10} Country of Manufacture: {material.country_of_manufacture}")
        if material.note:
            lines.append(f"{'':10} Note: {material.note}")

    lines.append("-" * len(header))
    lines.append(
        f"TOTALS{'':6}{summary.total_weight_kg:>15.3f} kg   ${summary.total_cost_cad:>9.2f} CAD   ${summary.total_cost_usd:>9.2f} USD"
    )
    if summary.total_weight_with_scrap_kg != summary.total_weight_kg:
        lines.append(f"WITH SCRAP{'':2}{summary.total_weight_with_scrap_kg:>15.3f} kg")

    lines.append("=" * 120)
    lines.append("SUMMARY:")
    lines.append(f"  Total materials: {summary.total_materials}")
    lines.append(f"  Materials with calculated weights: {summary.calculated_materials}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Minimal smoke test when module is executed directly
# ---------------------------------------------------------------------------
def _demo() -> None:
    """Provide a quick sanity check without touching external systems."""

    sample_bom = [
        BOMLine(
            item_no="7354001",
            description="ROUND BAR 6\" DIA",
            quantity=1,
            calculation_formula="Length",
            length=12,
            scrap_percent=5,
        ),
        BOMLine(
            item_no="7354002",
            description="PLATE 0.5 X 24 X 36",
            quantity=2,
        ),
        BOMLine(
            item_no="7354003",
            description="TUBE 4\" OD X 0.5\" WALL",
            quantity=1,
            calculation_formula="Length",
            length=24,
        ),
        BOMLine(
            item_no="7354999",
            description="CUSTOM SENSOR",
            quantity=1,
        ),
    ]

    def cost_provider(item_no: str) -> float:
        return {
            "7354001": 4.25,
            "7354002": 9.99,
            "7354003": 12.5,
        }.get(item_no, 0)

    def country_provider(item_no: str) -> Optional[CountryInfo]:
        return {
            "7354001": CountryInfo("Canada", "Canada"),
            "7354003": CountryInfo("USA", "Mexico"),
        }.get(item_no)

    calculator = TariffCalculator(cost_provider=cost_provider, country_provider=country_provider)
    result = calculator.calculate("7354028", sample_bom)

    print(format_tariff_report(result))


if __name__ == "__main__":
    _demo()


def _normalize_material_text(description: str) -> str:
    """Convert mixed inch/foot tokens into a consistent format for parsing."""

    def replace_mixed_fraction(match: re.Match[str]) -> str:
        whole, num, den = match.groups()
        return f"{whole}-{num}/{den}"

    text = description.replace("'", " ")
    text = re.sub(r'(\d+)"(\d+)/(\d+)', replace_mixed_fraction, text)
    return text


def _parse_numeric_token(token: str) -> Optional[float]:
    token = token.strip()
    if not token:
        return None
    token = token.replace(",", ".")
    if "-" in token and "/" in token:
        whole, frac = token.split("-", 1)
        try:
            return float(whole) + (_parse_numeric_token(frac) or 0.0)
        except ValueError:
            return None
    if "/" in token:
        try:
            num, den = token.split("/", 1)
            return float(num) / float(den)
        except (ValueError, ZeroDivisionError):
            return None
    try:
        return float(token)
    except ValueError:
        return None

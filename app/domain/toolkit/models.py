"""Data models for the toolkit domain."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class ProductionOrder(BaseModel):
    """Representation of an advanced MRP production order."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    pct_done: float = Field(alias="pctDone")
    prod_order_no: str = Field(alias="prodOrderNo")
    quantity: float
    remaining_quantity: float = Field(alias="remainingQuantity")
    planning_level_code: int | None = Field(default=None, alias="planningLevelCode")
    starting_date: str = Field(alias="startingDate")
    ending_date: str = Field(alias="endingDate")
    child_prod_order_no: List[str] = Field(default_factory=list, alias="childProdOrderNo")
    line_no: int = Field(alias="lineNo")
    earliest_required: Optional[str] = Field(default=None, alias="earliestRequired")
    system_id: Optional[str] = Field(default=None, alias="systemID")
    too_late: bool = Field(alias="tooLate")
    safety_lead_time: Optional[str] = Field(default=None, alias="safetyLeadTime")
    lead_time_calculation: Optional[str] = Field(default=None, alias="leadTimeCalculation")
    critical: bool
    item_category_code: Optional[str] = Field(default=None, alias="itemCategoryCode")
    routing_no: Optional[str] = Field(default=None, alias="routingNo")
    qty_can_apply: float = Field(alias="qtyCanApply")
    qty_applied: float = Field(alias="qtyApplied")
    item_no: str = Field(alias="itemNo")
    description: Optional[str] = None
    description_item_card: Optional[str] = Field(default=None, alias="descriptionItemCard")
    job_no: Optional[str] = Field(default=None, alias="jobNo")
    unit_of_measure_code: Optional[str] = Field(default=None, alias="unitofMeasureCode")
    lot_size: float = Field(alias="lotSize")
    qty_per_unit_of_measure: float = Field(alias="qtyperUnitofMeasure")
    date_get: str = Field(alias="dateGet")
    qty_disponible: float = Field(alias="qtyDisponible")
    qty_unused: float = Field(alias="qtyUnused")
    name: Optional[str] = None
    type: Optional[str] = None
    type_of_in: Optional[int] = Field(default=None, alias="typeOfIn")
    attribution_to_out: List[Any] = Field(default_factory=list, alias="attributionToOut")
    qty_attributed_to_minimums: float = Field(alias="qty_AttibutedToMinimums")
    substitutes_exist: bool = Field(alias="substitutesExist")
    number_of_substitutes: int = Field(alias="noofSubstitutes")
    safety_stock_quantity: float = Field(alias="safetyStockQuantity")
    mrp_comment: List[str] = Field(default_factory=list, alias="mrpComment")
    mrp_item_comment: List[str] = Field(default_factory=list, alias="mrpItemComment")


class ProductionOrderCollection(BaseModel):
    """Collection wrapper used by the upstream MRP service."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    count: int
    values: List[ProductionOrder]


@dataclass(slots=True)
class ProductionOrderResult:
    """Result bundle including original and filtered counts."""

    total_count: int
    orders: List[ProductionOrder]

    @property
    def filtered_count(self) -> int:
        """Number of orders after local filtering."""
        return len(self.orders)


class SampleAIRequest(BaseModel):
    """Request payload for generating a sample OpenAI response."""

    model_config = ConfigDict(populate_by_name=True)

    preset: Literal["small", "large", "reasoning"]
    instructions: str = Field(
        default="Talk like a pirate.",
        description="Instruction set provided to the language model.",
    )
    input_text: str = Field(
        alias="input",
        default="Are semicolons optional in JavaScript?",
        description="User input forwarded to the language model.",
    )


class SampleAIResponse(BaseModel):
    """Structured response returned to API consumers for sample AI calls."""

    model_config = ConfigDict(populate_by_name=True)

    preset: Literal["small", "large", "reasoning"]
    model: str
    reasoning: Optional[Dict[str, str]] = None
    instructions: str
    input_text: str = Field(alias="input")
    output_text: str = Field(alias="output")
    stubbed: bool = Field(
        default=False,
        description="Indicates that the response was generated locally for testing.",
    )

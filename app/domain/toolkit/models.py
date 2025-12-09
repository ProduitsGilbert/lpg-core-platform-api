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


class TypingSuggestionRequest(BaseModel):
    """Request payload for rapid typing/code completion suggestions."""

    prefix: str = Field(
        ...,
        description="Text immediately preceding the cursor.",
        min_length=1,
    )
    suffix: str = Field(
        default="",
        description="Text immediately following the cursor.",
    )
    language: Optional[str] = Field(
        default=None,
        description="Optional hint about the programming or natural language.",
        max_length=64,
    )
    instructions: Optional[str] = Field(
        default=None,
        description="Optional custom instructions overriding the default typing helper persona.",
    )
    temperature: float = Field(
        default=0.2,
        ge=0.0,
        le=2.0,
        description="Sampling temperature forwarded to the language model.",
    )


class TypingSuggestionResponse(BaseModel):
    """Response payload for typing suggestions."""

    model: str
    suggestion: str
    stubbed: bool = Field(
        default=False,
        description="Indicates the suggestion was generated locally because OpenAI is not configured.",
    )


class DeepReasoningRequest(BaseModel):
    """Request payload for complex problem solving with high reasoning effort."""

    question: str = Field(
        ...,
        description="Primary question or problem statement to solve.",
    )
    context: Optional[str] = Field(
        default=None,
        description="Supplementary context, facts, or background information.",
    )
    expected_format: Optional[str] = Field(
        default=None,
        description="Optional guidance for the desired answer structure (e.g., bullet list, JSON).",
    )


class DeepReasoningResponse(BaseModel):
    """Response payload for complex reasoning queries."""

    model: str
    effort: Literal["high"] = Field(default="high")
    answer: str
    stubbed: bool = Field(
        default=False,
        description="Indicates the response was generated locally because OpenAI is not configured.",
    )


class StandardAIRequest(BaseModel):
    """Request payload for standard assistant-style generations."""

    prompt: str = Field(
        ...,
        description="User prompt or instruction for the assistant.",
    )
    instructions: Optional[str] = Field(
        default=None,
        description="Optional system-level instructions to steer the assistant.",
    )
    temperature: float = Field(
        default=0.5,
        ge=0.0,
        le=2.0,
        description="Sampling temperature forwarded to the language model.",
    )


class StandardAIResponse(BaseModel):
    """Response payload for standard assistant generations."""

    model: str
    output: str
    stubbed: bool = Field(
        default=False,
        description="Indicates the response was generated locally because OpenAI is not configured.",
    )


class StreamingAIRequest(BaseModel):
    """Request payload for streaming assistant responses."""

    prompt: str = Field(
        ...,
        description="User prompt or instruction to stream.",
    )
    instructions: Optional[str] = Field(
        default=None,
        description="Optional system prompt to guide the model behaviour.",
    )
    temperature: float = Field(
        default=0.5,
        ge=0.0,
        le=2.0,
        description="Sampling temperature for the streamed response.",
    )


class OpenRouterRequest(BaseModel):
    """Request payload for invoking OpenRouter supported models."""

    prompt: str = Field(..., description="User prompt forwarded to the selected model(s).")
    models: Optional[List[str]] = Field(
        default=None,
        description="Preferred model ordering drawn from the allowed leaderboard list.",
    )
    instructions: Optional[str] = Field(
        default=None,
        description="Optional system instructions or persona guidance.",
    )
    temperature: float = Field(
        default=0.5,
        ge=0.0,
        le=2.0,
        description="Sampling temperature for the completion.",
    )


class OpenRouterResponse(BaseModel):
    """Response payload returned from OpenRouter completions."""

    requested_models: List[str]
    selected_model: Optional[str] = Field(
        default=None,
        description="Actual model that generated the output (if known).",
    )
    output: str
    stubbed: bool = Field(
        default=False,
        description="Indicates the response was generated locally because OpenRouter is not configured.",
    )

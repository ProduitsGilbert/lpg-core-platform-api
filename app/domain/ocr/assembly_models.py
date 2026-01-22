"""
Models for mechanical assembly component (BOM) extraction from technical drawings.
"""

from __future__ import annotations

from typing import Optional, Literal, List

from pydantic import BaseModel, Field
from pydantic_settings import SettingsConfigDict


class AssemblyComponentsRequest(BaseModel):
    itemNo: str = Field(..., description="Assembly item number (root item)")
    revision: Optional[str] = Field(default=None, description="Optional revision identifier (e.g., '08')")
    type: Literal["Assembly"] = Field(default="Assembly", description="Requested OCR extraction type")
    includePdfPosition: bool = Field(
        default=False,
        description="When true, attempts to locate bubble label coordinates in the PDF (page/top/left).",
    )


class PdfPosition(BaseModel):
    page: int = Field(..., ge=1, description="1-based page number")
    top: int = Field(..., ge=0, description="Y coordinate from top (PDF points)")
    left: int = Field(..., ge=0, description="X coordinate from left (PDF points)")


class AssemblyComponent(BaseModel):
    model_config = SettingsConfigDict(populate_by_name=True)

    itemNo: str = Field(..., description="Component item number")
    qty: int = Field(..., ge=1, description="Required quantity")
    position: str = Field(..., description="BOM position (string because some positions can include letters)")
    pdf_position: Optional[PdfPosition] = Field(
        default=None,
        alias="PdfPosition",
        description="Best-effort bubble label location in the PDF (only present when requested and found).",
    )


class AssemblyComponentsResponse(BaseModel):
    itemNo: str = Field(..., description="Assembly item number (root item)")
    revision: Optional[str] = Field(default=None, description="Revision identifier if provided/available")
    type: str = Field(..., description="Extraction type")
    components: List[AssemblyComponent] = Field(default_factory=list, description="Extracted BOM components")



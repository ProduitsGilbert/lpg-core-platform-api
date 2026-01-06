"""
Models for mechanical assembly component (BOM) extraction from technical drawings.
"""

from __future__ import annotations

from typing import Optional, Literal, List

from pydantic import BaseModel, Field


class AssemblyComponentsRequest(BaseModel):
    itemNo: str = Field(..., description="Assembly item number (root item)")
    revision: Optional[str] = Field(default=None, description="Optional revision identifier (e.g., '08')")
    type: Literal["Assembly"] = Field(default="Assembly", description="Requested OCR extraction type")


class AssemblyComponent(BaseModel):
    itemNo: str = Field(..., description="Component item number")
    qty: int = Field(..., ge=1, description="Required quantity")
    position: str = Field(..., description="BOM position (string because some positions can include letters)")


class AssemblyComponentsResponse(BaseModel):
    itemNo: str = Field(..., description="Assembly item number (root item)")
    revision: Optional[str] = Field(default=None, description="Revision identifier if provided/available")
    type: str = Field(..., description="Extraction type")
    components: List[AssemblyComponent] = Field(default_factory=list, description="Extracted BOM components")



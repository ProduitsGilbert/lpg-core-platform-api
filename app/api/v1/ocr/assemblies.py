"""
OCR endpoints for mechanical assembly drawings (BOM/component lists).
"""

from __future__ import annotations

import logfire
from fastapi import APIRouter, Depends, HTTPException

from app.domain.documents.file_share_service import FileShareService
from app.domain.ocr.assembly_components_service import AssemblyComponentsService
from app.domain.ocr.assembly_models import AssemblyComponentsRequest, AssemblyComponentsResponse


router = APIRouter(prefix="/ocr/assemblies", tags=["OCR"])


def get_assembly_components_service() -> AssemblyComponentsService:
    return AssemblyComponentsService(file_share_service=FileShareService())


@router.post(
    "/components",
    response_model=AssemblyComponentsResponse,
    response_model_exclude_none=True,
    summary="Extract assembly component list (BOM) from an item technical drawing",
)
async def extract_assembly_components(
    body: AssemblyComponentsRequest,
    service: AssemblyComponentsService = Depends(get_assembly_components_service),
) -> AssemblyComponentsResponse:
    """
    Given an assembly item number (and optional revision), returns the BOM component list.
    """
    with logfire.span("api_extract_assembly_components", item_no=body.itemNo, revision=body.revision):
        try:
            return await service.extract_components_for_item(
                item_no=body.itemNo,
                revision=body.revision,
                extraction_type=body.type,
                include_pdf_position=body.includePdfPosition,
            )
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail=f"PDF file not found for item '{body.itemNo}'")
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Failed to extract assembly components: {exc}")



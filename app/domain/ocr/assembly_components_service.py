"""
Service for extracting mechanical assembly component lists from technical drawings.
"""

from __future__ import annotations

from app.domain.documents.file_share_service import FileShareService
from app.domain.ocr.assembly_bom_extractor import AssemblyBOMExtractor
from app.domain.ocr.assembly_models import AssemblyComponentsResponse, AssemblyComponent


class AssemblyComponentsService:
    def __init__(self, *, file_share_service: FileShareService):
        self._file_share_service = file_share_service
        self._extractor = AssemblyBOMExtractor()

    async def extract_components_for_item(
        self,
        *,
        item_no: str,
        revision: str | None,
        extraction_type: str,
    ) -> AssemblyComponentsResponse:
        pdf_data = await self._file_share_service.get_item_pdf(item_no)
        if not pdf_data:
            # Let the API layer translate this into 404
            raise FileNotFoundError(f"PDF not found for item {item_no}")

        pdf_bytes = pdf_data["content"]
        parsed = self._extractor.extract_components_from_pdf(pdf_bytes, root_item_no=item_no)

        return AssemblyComponentsResponse(
            itemNo=item_no,
            revision=revision,
            type=extraction_type,
            components=[
                AssemblyComponent(itemNo=c.item_no, qty=c.qty, position=c.position)
                for c in parsed
            ],
        )



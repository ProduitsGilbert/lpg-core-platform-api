from __future__ import annotations

import io
import json
import base64
from functools import lru_cache
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
import fitz
from pypdf import PdfReader

from app.domain.ventes_sous_traitance.models import (
    CustomerCreateRequest,
    CustomerSummary,
    CustomerUpdateRequest,
    JobStatusResponse,
    MachineCapabilityCatalogItem,
    MachineCapabilityOption,
    MachineCapabilityOptionCreateRequest,
    MachineCapabilityOptionEntry,
    MachineCapabilityOptionUpdateRequest,
    MachineCreateRequest,
    MachineGroupCreateRequest,
    MachineGroupSummary,
    MachineGroupUpdateRequest,
    MachineResponse,
    MachineUpdateRequest,
    QuoteAnalysisStartResponse,
    QuoteCreateRequest,
    QuoteStatusUpdateRequest,
    QuoteSummary,
    QuoteUpdateRequest,
    RoutingCreateRequest,
    RoutingResponse,
    RoutingStepCreateRequest,
    RoutingStepResponse,
    RoutingStepUpdateRequest,
    RoutingUpdateRequest,
)
from app.domain.ventes_sous_traitance.service import VentesSousTraitanceService
from app.errors import DatabaseError

router = APIRouter(tags=["Ventes - Sous-Traitance"])
MAX_ANALYZE_UPLOAD_BYTES = 50 * 1024 * 1024
MAX_ANALYZE_IMAGE_PAGES = 6
MAX_ANALYZE_IMAGE_DATA_URLS = 7  # includes 1 title-block crop from first page


@lru_cache(maxsize=1)
def _get_service() -> VentesSousTraitanceService:
    return VentesSousTraitanceService()


def get_service() -> VentesSousTraitanceService:
    service = _get_service()
    if not service.is_configured:
        raise DatabaseError("Cedule database not configured")
    return service


async def _read_and_validate_pdf_upload(file: UploadFile) -> bytes:
    filename = (file.filename or "").lower()
    if not filename.endswith(".pdf"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File must be a PDF")
    content = await file.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty")
    if len(content) > MAX_ANALYZE_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size must not exceed 50MB",
        )
    return content


def _extract_pdf_text_from_bytes(file_content: bytes) -> str:
    try:
        reader = PdfReader(io.BytesIO(file_content))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Invalid PDF: {exc}") from exc
    chunks: list[str] = []
    for idx, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        if text.strip():
            chunks.append(f"[Page {idx + 1}]\n{text.strip()}")
    return "\n\n".join(chunks).strip()


def _extract_pdf_image_data_urls(file_content: bytes) -> list[str]:
    """
    Render PDF pages to image data URLs for multimodal LLM extraction.
    Includes first page title-block crop to improve metadata extraction.
    """
    urls: list[str] = []
    try:
        doc = fitz.open(stream=file_content, filetype="pdf")
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Invalid PDF: {exc}") from exc

    try:
        for idx, page in enumerate(doc):
            if idx >= MAX_ANALYZE_IMAGE_PAGES:
                break
            pix = page.get_pixmap(matrix=fitz.Matrix(1.6, 1.6), alpha=False)
            png_bytes = pix.tobytes("png")
            urls.append(f"data:image/png;base64,{base64.b64encode(png_bytes).decode('ascii')}")

            if idx == 0 and len(urls) < MAX_ANALYZE_IMAGE_DATA_URLS:
                rect = page.rect
                clip = fitz.Rect(rect.width * 0.55, rect.height * 0.55, rect.width, rect.height)
                crop_pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0), clip=clip, alpha=False)
                crop_png = crop_pix.tobytes("png")
                urls.append(f"data:image/png;base64,{base64.b64encode(crop_png).decode('ascii')}")
    finally:
        doc.close()

    return urls[:MAX_ANALYZE_IMAGE_DATA_URLS]


def _parse_part_cues_json(part_cues_json: Optional[str]) -> list[dict]:
    if not part_cues_json:
        return []
    try:
        parsed = json.loads(part_cues_json)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid part_cues_json: {exc.msg}") from exc
    if not isinstance(parsed, list):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="part_cues_json must be a JSON array")
    normalized: list[dict] = []
    for idx, item in enumerate(parsed):
        if not isinstance(item, dict):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"part_cues_json[{idx}] must be an object",
            )
        normalized.append(item)
    return normalized


@router.post("/quotes", response_model=QuoteSummary, status_code=status.HTTP_201_CREATED)
async def create_quote(
    payload: QuoteCreateRequest,
    service: VentesSousTraitanceService = Depends(get_service),
) -> QuoteSummary:
    return service.create_quote(payload)


@router.get("/customers", response_model=list[CustomerSummary])
async def list_customers(
    search: Optional[str] = Query(default=None, alias="q"),
    limit: int = Query(default=200, ge=1, le=1000),
    service: VentesSousTraitanceService = Depends(get_service),
) -> list[CustomerSummary]:
    return service.list_customers(search=search, limit=limit)


@router.post("/customers", response_model=CustomerSummary, status_code=status.HTTP_201_CREATED)
async def create_customer(
    payload: CustomerCreateRequest,
    service: VentesSousTraitanceService = Depends(get_service),
) -> CustomerSummary:
    return service.create_customer(payload)


@router.patch("/customers/{customer_id}", response_model=CustomerSummary)
async def update_customer(
    customer_id: UUID,
    payload: CustomerUpdateRequest,
    service: VentesSousTraitanceService = Depends(get_service),
) -> CustomerSummary:
    customer = service.update_customer(customer_id, payload)
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    return customer


@router.delete("/customers/{customer_id}", response_model=dict[str, bool])
async def delete_customer(
    customer_id: UUID,
    service: VentesSousTraitanceService = Depends(get_service),
) -> dict[str, bool]:
    deleted = service.delete_customer(customer_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    return {"deleted": True}


@router.get("/machine-groups", response_model=list[MachineGroupSummary])
async def list_machine_groups(
    search: Optional[str] = Query(default=None, alias="q"),
    limit: int = Query(default=200, ge=1, le=1000),
    service: VentesSousTraitanceService = Depends(get_service),
) -> list[MachineGroupSummary]:
    return service.list_machine_groups(search=search, limit=limit)


@router.post("/machine-groups", response_model=MachineGroupSummary, status_code=status.HTTP_201_CREATED)
async def create_machine_group(
    payload: MachineGroupCreateRequest,
    service: VentesSousTraitanceService = Depends(get_service),
) -> MachineGroupSummary:
    return service.create_machine_group(payload)


@router.patch("/machine-groups/{machine_group_id}", response_model=MachineGroupSummary)
async def update_machine_group(
    machine_group_id: str,
    payload: MachineGroupUpdateRequest,
    service: VentesSousTraitanceService = Depends(get_service),
) -> MachineGroupSummary:
    machine_group = service.update_machine_group(machine_group_id, payload)
    if not machine_group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Machine group not found")
    return machine_group


@router.delete("/machine-groups/{machine_group_id}", response_model=dict[str, bool])
async def delete_machine_group(
    machine_group_id: str,
    service: VentesSousTraitanceService = Depends(get_service),
) -> dict[str, bool]:
    deleted = service.delete_machine_group(machine_group_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Machine group not found")
    return {"deleted": True}


@router.get("/machine-capabilities/options", response_model=list[MachineCapabilityOption])
async def list_machine_capability_options(
    search: Optional[str] = Query(default=None, alias="q"),
    capability_code: Optional[str] = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
    service: VentesSousTraitanceService = Depends(get_service),
) -> list[MachineCapabilityOption]:
    return service.list_machine_capability_options(
        search=search,
        capability_code=capability_code,
        limit=limit,
    )


@router.post("/machine-capabilities/options", response_model=MachineCapabilityOptionEntry, status_code=status.HTTP_201_CREATED)
async def create_machine_capability_option(
    payload: MachineCapabilityOptionCreateRequest,
    service: VentesSousTraitanceService = Depends(get_service),
) -> MachineCapabilityOptionEntry:
    return service.create_machine_capability_option(payload)


@router.patch("/machine-capabilities/options/{option_id}", response_model=MachineCapabilityOptionEntry)
async def update_machine_capability_option(
    option_id: UUID,
    payload: MachineCapabilityOptionUpdateRequest,
    service: VentesSousTraitanceService = Depends(get_service),
) -> MachineCapabilityOptionEntry:
    option = service.update_machine_capability_option(option_id, payload)
    if not option:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Machine capability option not found")
    return option


@router.get("/machine-capabilities/catalog", response_model=list[MachineCapabilityCatalogItem])
async def list_machine_capability_catalog(
    search: Optional[str] = Query(default=None, alias="q"),
    limit: int = Query(default=200, ge=1, le=1000),
    service: VentesSousTraitanceService = Depends(get_service),
) -> list[MachineCapabilityCatalogItem]:
    return service.list_machine_capability_catalog(search=search, limit=limit)


@router.get("/machines", response_model=list[MachineResponse])
async def list_machines(
    search: Optional[str] = Query(default=None, alias="q"),
    machine_group_id: Optional[str] = Query(default=None),
    active_only: bool = Query(default=True),
    limit: int = Query(default=200, ge=1, le=1000),
    service: VentesSousTraitanceService = Depends(get_service),
) -> list[MachineResponse]:
    return service.list_machines(
        search=search,
        machine_group_id=machine_group_id,
        active_only=active_only,
        limit=limit,
    )


@router.get("/machines/{machine_id}", response_model=MachineResponse)
async def get_machine(
    machine_id: UUID,
    service: VentesSousTraitanceService = Depends(get_service),
) -> MachineResponse:
    machine = service.get_machine(machine_id)
    if not machine:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Machine not found")
    return machine


@router.post("/machines", response_model=MachineResponse, status_code=status.HTTP_201_CREATED)
async def create_machine(
    payload: MachineCreateRequest,
    service: VentesSousTraitanceService = Depends(get_service),
) -> MachineResponse:
    return service.create_machine(payload)


@router.patch("/machines/{machine_id}", response_model=MachineResponse)
async def update_machine(
    machine_id: UUID,
    payload: MachineUpdateRequest,
    service: VentesSousTraitanceService = Depends(get_service),
) -> MachineResponse:
    machine = service.update_machine(machine_id, payload)
    if not machine:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Machine not found")
    return machine


@router.delete("/machines/{machine_id}", response_model=dict[str, bool])
async def delete_machine(
    machine_id: UUID,
    service: VentesSousTraitanceService = Depends(get_service),
) -> dict[str, bool]:
    deleted = service.delete_machine(machine_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Machine not found")
    return {"deleted": True}


@router.get("/quotes", response_model=list[QuoteSummary])
async def list_quotes(
    status_filter: Optional[str] = Query(default=None, alias="status"),
    customer: Optional[UUID] = Query(default=None),
    service: VentesSousTraitanceService = Depends(get_service),
) -> list[QuoteSummary]:
    return service.list_quotes(status=status_filter, customer_id=customer)


@router.get("/quotes/{quote_id}", response_model=QuoteSummary)
async def get_quote(
    quote_id: UUID,
    service: VentesSousTraitanceService = Depends(get_service),
) -> QuoteSummary:
    quote = service.get_quote(quote_id)
    if not quote:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quote not found")
    return quote


@router.patch("/quotes/{quote_id}", response_model=QuoteSummary)
async def update_quote(
    quote_id: UUID,
    payload: QuoteUpdateRequest,
    service: VentesSousTraitanceService = Depends(get_service),
) -> QuoteSummary:
    quote = service.update_quote(quote_id, payload)
    if not quote:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quote not found")
    return quote


@router.delete("/quotes/{quote_id}", response_model=dict[str, bool])
async def delete_quote(
    quote_id: UUID,
    service: VentesSousTraitanceService = Depends(get_service),
) -> dict[str, bool]:
    deleted = service.delete_quote(quote_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quote not found")
    return {"deleted": True}


@router.patch("/quotes/{quote_id}/status", response_model=QuoteSummary)
async def update_quote_status(
    quote_id: UUID,
    payload: QuoteStatusUpdateRequest,
    service: VentesSousTraitanceService = Depends(get_service),
) -> QuoteSummary:
    quote = service.update_quote_status(quote_id, payload)
    if not quote:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quote not found")
    return quote


@router.post("/quotes/{quote_id}/analyze", response_model=QuoteAnalysisStartResponse)
async def analyze_quote(
    quote_id: UUID,
    service: VentesSousTraitanceService = Depends(get_service),
) -> QuoteAnalysisStartResponse:
    if not service.get_quote(quote_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quote not found")
    job_id = service.start_analysis(quote_id)
    return QuoteAnalysisStartResponse(job_id=job_id, quote_id=quote_id, status="scheduled")


@router.post("/quotes/{quote_id}/analyze-upload", response_model=QuoteAnalysisStartResponse)
async def analyze_quote_upload(
    quote_id: UUID,
    file: UploadFile = File(..., description="Technical drawing PDF to analyze"),
    user_cue: Optional[str] = Form(default=None, description="Estimator guidance text for the model"),
    part_cues_json: Optional[str] = Form(
        default=None,
        description="JSON array of per-part cues, e.g. [{\"part_ref\":\"A\",\"cue\":\"lathe first\"}]",
    ),
    service: VentesSousTraitanceService = Depends(get_service),
) -> QuoteAnalysisStartResponse:
    if not service.get_quote(quote_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quote not found")

    file_content = await _read_and_validate_pdf_upload(file)
    extracted_text = _extract_pdf_text_from_bytes(file_content)
    image_data_urls = _extract_pdf_image_data_urls(file_content)
    has_user_cue = bool(user_cue and user_cue.strip())
    if not extracted_text and not image_data_urls and not has_user_cue:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No text or visual content could be extracted from PDF. Provide user_cue or upload a valid PDF.",
        )
    part_cues = _parse_part_cues_json(part_cues_json)
    job_id = service.start_analysis_from_text(
        quote_id,
        source_text=extracted_text,
        user_cue=user_cue,
        part_cues=part_cues,
        page_image_data_urls=image_data_urls,
    )
    return QuoteAnalysisStartResponse(job_id=job_id, quote_id=quote_id, status="scheduled")


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(
    job_id: UUID,
    service: VentesSousTraitanceService = Depends(get_service),
) -> JobStatusResponse:
    job = service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return job


@router.post("/parts/{part_id}/generate-routings", response_model=list[RoutingResponse])
async def generate_routings(
    part_id: UUID,
    service: VentesSousTraitanceService = Depends(get_service),
) -> list[RoutingResponse]:
    routings = service.list_routings(part_id)
    if routings:
        return routings
    created = service.create_routing(part_id, RoutingCreateRequest(scenario_name="Generated Baseline", selected=True))
    return [created]


@router.get("/parts/{part_id}/routings", response_model=list[RoutingResponse])
async def list_routings(
    part_id: UUID,
    service: VentesSousTraitanceService = Depends(get_service),
) -> list[RoutingResponse]:
    return service.list_routings(part_id)


@router.post("/parts/{part_id}/routings", response_model=RoutingResponse, status_code=status.HTTP_201_CREATED)
async def create_routing(
    part_id: UUID,
    payload: RoutingCreateRequest,
    service: VentesSousTraitanceService = Depends(get_service),
) -> RoutingResponse:
    return service.create_routing(part_id, payload)


@router.get("/routings/{routing_id}", response_model=RoutingResponse)
async def get_routing(
    routing_id: UUID,
    service: VentesSousTraitanceService = Depends(get_service),
) -> RoutingResponse:
    routing = service.get_routing(routing_id)
    if not routing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Routing not found")
    return routing


@router.patch("/routings/{routing_id}", response_model=RoutingResponse)
async def update_routing(
    routing_id: UUID,
    payload: RoutingUpdateRequest,
    service: VentesSousTraitanceService = Depends(get_service),
) -> RoutingResponse:
    routing = service.update_routing(routing_id, payload)
    if not routing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Routing not found")
    return routing


@router.delete("/routings/{routing_id}", response_model=dict[str, bool])
async def delete_routing(
    routing_id: UUID,
    service: VentesSousTraitanceService = Depends(get_service),
) -> dict[str, bool]:
    deleted = service.delete_routing(routing_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Routing not found")
    return {"deleted": True}


@router.get("/routings/{routing_id}/steps", response_model=list[RoutingStepResponse])
async def list_routing_steps(
    routing_id: UUID,
    service: VentesSousTraitanceService = Depends(get_service),
) -> list[RoutingStepResponse]:
    return service.list_routing_steps(routing_id)


@router.post("/routings/{routing_id}/steps", response_model=RoutingStepResponse, status_code=status.HTTP_201_CREATED)
async def create_routing_step(
    routing_id: UUID,
    payload: RoutingStepCreateRequest,
    service: VentesSousTraitanceService = Depends(get_service),
) -> RoutingStepResponse:
    return service.create_routing_step(routing_id, payload)


@router.patch("/routing_steps/{step_id}", response_model=RoutingStepResponse)
async def update_routing_step(
    step_id: UUID,
    payload: RoutingStepUpdateRequest,
    service: VentesSousTraitanceService = Depends(get_service),
) -> RoutingStepResponse:
    step = service.update_routing_step(step_id, payload)
    if not step:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Routing step not found")
    return step


@router.delete("/routing_steps/{step_id}", response_model=dict[str, bool])
async def delete_routing_step(
    step_id: UUID,
    service: VentesSousTraitanceService = Depends(get_service),
) -> dict[str, bool]:
    deleted = service.delete_routing_step(step_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Routing step not found")
    return {"deleted": True}

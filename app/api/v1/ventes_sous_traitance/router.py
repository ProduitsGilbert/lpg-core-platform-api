from __future__ import annotations

from functools import lru_cache
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.domain.ventes_sous_traitance.models import (
    JobStatusResponse,
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


@lru_cache(maxsize=1)
def _get_service() -> VentesSousTraitanceService:
    return VentesSousTraitanceService()


def get_service() -> VentesSousTraitanceService:
    service = _get_service()
    if not service.is_configured:
        raise DatabaseError("Cedule database not configured")
    return service


@router.post("/quotes", response_model=QuoteSummary, status_code=status.HTTP_201_CREATED)
async def create_quote(
    payload: QuoteCreateRequest,
    service: VentesSousTraitanceService = Depends(get_service),
) -> QuoteSummary:
    return service.create_quote(payload)


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

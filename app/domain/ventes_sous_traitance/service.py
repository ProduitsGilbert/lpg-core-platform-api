from __future__ import annotations

from typing import Optional
from uuid import UUID

from app.domain.ventes_sous_traitance.models import (
    JobStatusResponse,
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
from app.integrations.cedule_ventes_sous_traitance_repository import CeduleVentesSousTraitanceRepository


class VentesSousTraitanceService:
    def __init__(self, repository: Optional[CeduleVentesSousTraitanceRepository] = None) -> None:
        self._repository = repository or CeduleVentesSousTraitanceRepository()

    @property
    def is_configured(self) -> bool:
        return self._repository.is_configured

    def list_quotes(self, *, status: Optional[str], customer_id: Optional[UUID]) -> list[QuoteSummary]:
        return self._repository.list_quotes(status=status, customer_id=customer_id)

    def get_quote(self, quote_id: UUID) -> Optional[QuoteSummary]:
        return self._repository.get_quote(quote_id)

    def create_quote(self, payload: QuoteCreateRequest) -> QuoteSummary:
        return self._repository.create_quote(payload)

    def update_quote(self, quote_id: UUID, payload: QuoteUpdateRequest) -> Optional[QuoteSummary]:
        return self._repository.update_quote(quote_id, payload)

    def update_quote_status(self, quote_id: UUID, payload: QuoteStatusUpdateRequest) -> Optional[QuoteSummary]:
        return self._repository.update_quote_status(quote_id, payload)

    def delete_quote(self, quote_id: UUID) -> bool:
        return self._repository.delete_quote(quote_id)

    def list_routings(self, part_id: UUID) -> list[RoutingResponse]:
        return self._repository.list_routings(part_id)

    def get_routing(self, routing_id: UUID) -> Optional[RoutingResponse]:
        return self._repository.get_routing(routing_id)

    def create_routing(self, part_id: UUID, payload: RoutingCreateRequest) -> RoutingResponse:
        return self._repository.create_routing(part_id, payload)

    def update_routing(self, routing_id: UUID, payload: RoutingUpdateRequest) -> Optional[RoutingResponse]:
        return self._repository.update_routing(routing_id, payload)

    def delete_routing(self, routing_id: UUID) -> bool:
        return self._repository.delete_routing(routing_id)

    def list_routing_steps(self, routing_id: UUID) -> list[RoutingStepResponse]:
        return self._repository.list_routing_steps(routing_id)

    def create_routing_step(self, routing_id: UUID, payload: RoutingStepCreateRequest) -> RoutingStepResponse:
        return self._repository.create_routing_step(routing_id, payload)

    def update_routing_step(self, step_id: UUID, payload: RoutingStepUpdateRequest) -> Optional[RoutingStepResponse]:
        return self._repository.update_routing_step(step_id, payload)

    def delete_routing_step(self, step_id: UUID) -> bool:
        return self._repository.delete_routing_step(step_id)

    def start_analysis(self, quote_id: UUID) -> UUID:
        return self._repository.start_analysis(quote_id)

    def get_job(self, job_id: UUID) -> Optional[JobStatusResponse]:
        return self._repository.get_job(job_id)

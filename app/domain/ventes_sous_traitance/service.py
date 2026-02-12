from __future__ import annotations

from typing import Optional
from uuid import UUID

from app.domain.ventes_sous_traitance.analysis_pipeline import VentesSousTraitanceAnalysisPipeline
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
from app.settings import settings


class VentesSousTraitanceService:
    def __init__(
        self,
        repository: Optional[CeduleVentesSousTraitanceRepository] = None,
        analysis_pipeline: Optional[VentesSousTraitanceAnalysisPipeline] = None,
    ) -> None:
        self._repository = repository or CeduleVentesSousTraitanceRepository()
        self._analysis_pipeline = analysis_pipeline or VentesSousTraitanceAnalysisPipeline()

    @staticmethod
    def _analysis_model_name() -> str:
        if settings.grok_api_key:
            return settings.xai_model
        return settings.openai_model or "manual-trigger"

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
        run_id = self._repository.create_analysis_run(
            quote_id,
            model_name=self._analysis_model_name(),
            stage="routing",
        )
        try:
            source_text = self._repository.get_quote_source_text(quote_id)
            result = self._analysis_pipeline.run(source_text=source_text)
            metadata = result.get("step1_metadata", {})
            classification = result.get("step2_classification", {})
            complexity = result.get("step3_complexity", {})
            routings = result.get("step4_routings", {})

            part_id = self._repository.upsert_part_from_analysis(
                quote_id=quote_id,
                metadata=metadata if isinstance(metadata, dict) else {},
                classification=classification if isinstance(classification, dict) else {},
                complexity=complexity if isinstance(complexity, dict) else {},
            )

            self._repository.save_part_extraction(
                part_id=part_id,
                model_name=self._analysis_model_name(),
                prompt_version="step1_metadata_v1",
                payload=metadata if isinstance(metadata, dict) else {},
                confidence=(metadata.get("confidence") if isinstance(metadata, dict) else None),
            )
            self._repository.save_part_extraction(
                part_id=part_id,
                model_name=self._analysis_model_name(),
                prompt_version="step2_classification_v1",
                payload=classification if isinstance(classification, dict) else {},
                confidence=(classification.get("confidence") if isinstance(classification, dict) else None),
            )
            self._repository.save_part_extraction(
                part_id=part_id,
                model_name=self._analysis_model_name(),
                prompt_version="step3_complexity_v1",
                payload=complexity if isinstance(complexity, dict) else {},
                confidence=(complexity.get("confidence") if isinstance(complexity, dict) else None),
            )

            created_routings = self._repository.save_generated_routings(
                part_id=part_id,
                scenarios_payload=routings if isinstance(routings, dict) else {},
            )
            result["created_part_id"] = str(part_id)
            result["created_routing_ids"] = [str(r.routing_id) for r in created_routings]
            self._repository.complete_analysis_run(run_id, output=result)
        except Exception as exc:
            self._repository.fail_analysis_run(run_id, str(exc))
        return run_id

    def get_job(self, job_id: UUID) -> Optional[JobStatusResponse]:
        return self._repository.get_job(job_id)

from __future__ import annotations

import json
from typing import Any, Optional
from uuid import UUID

from app.domain.ventes_sous_traitance.analysis_pipeline import VentesSousTraitanceAnalysisPipeline
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
    PartFeatureCreateRequest,
    PartFeatureResponse,
    PartFeatureSetResponse,
    PartFeatureSetUpsertRequest,
    PartFeatureUpdateRequest,
    QuotePartSummary,
    QuotePartUpdateRequest,
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

    def list_customers(self, *, search: Optional[str], limit: int = 200) -> list[CustomerSummary]:
        return self._repository.list_customers(search=search, limit=limit)

    def create_customer(self, payload: CustomerCreateRequest) -> CustomerSummary:
        return self._repository.create_customer(payload)

    def update_customer(self, customer_id: UUID, payload: CustomerUpdateRequest) -> Optional[CustomerSummary]:
        return self._repository.update_customer(customer_id, payload)

    def delete_customer(self, customer_id: UUID) -> bool:
        return self._repository.delete_customer(customer_id)

    def list_machine_groups(self, *, search: Optional[str], limit: int = 200) -> list[MachineGroupSummary]:
        return self._repository.list_machine_groups(search=search, limit=limit)

    def create_machine_group(self, payload: MachineGroupCreateRequest) -> MachineGroupSummary:
        return self._repository.create_machine_group(payload)

    def update_machine_group(self, machine_group_id: str, payload: MachineGroupUpdateRequest) -> Optional[MachineGroupSummary]:
        return self._repository.update_machine_group(machine_group_id, payload)

    def delete_machine_group(self, machine_group_id: str) -> bool:
        return self._repository.delete_machine_group(machine_group_id)

    def list_machine_capability_options(
        self, *, search: Optional[str], capability_code: Optional[str], limit: int = 200
    ) -> list[MachineCapabilityOption]:
        return self._repository.list_machine_capability_options(
            search=search,
            capability_code=capability_code,
            limit=limit,
        )

    def list_machine_capability_catalog(
        self, *, search: Optional[str], limit: int = 200
    ) -> list[MachineCapabilityCatalogItem]:
        return self._repository.list_machine_capability_catalog(search=search, limit=limit)

    def create_machine_capability_option(
        self, payload: MachineCapabilityOptionCreateRequest
    ) -> MachineCapabilityOptionEntry:
        return self._repository.create_machine_capability_option(payload)

    def update_machine_capability_option(
        self, option_id: UUID, payload: MachineCapabilityOptionUpdateRequest
    ) -> Optional[MachineCapabilityOptionEntry]:
        return self._repository.update_machine_capability_option(option_id, payload)

    def list_machines(
        self,
        *,
        search: Optional[str],
        machine_group_id: Optional[str],
        active_only: bool,
        limit: int = 200,
    ) -> list[MachineResponse]:
        return self._repository.list_machines(
            search=search,
            machine_group_id=machine_group_id,
            active_only=active_only,
            limit=limit,
        )

    def get_machine(self, machine_id: UUID) -> Optional[MachineResponse]:
        return self._repository.get_machine(machine_id)

    def create_machine(self, payload: MachineCreateRequest) -> MachineResponse:
        return self._repository.create_machine(payload)

    def update_machine(self, machine_id: UUID, payload: MachineUpdateRequest) -> Optional[MachineResponse]:
        return self._repository.update_machine(machine_id, payload)

    def delete_machine(self, machine_id: UUID) -> bool:
        return self._repository.delete_machine(machine_id)

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

    def list_quote_parts(self, quote_id: UUID) -> list[QuotePartSummary]:
        return self._repository.list_quote_parts(quote_id)

    def get_quote_part(self, part_id: UUID) -> Optional[QuotePartSummary]:
        return self._repository.get_quote_part(part_id)

    def update_quote_part(self, part_id: UUID, payload: QuotePartUpdateRequest) -> Optional[QuotePartSummary]:
        return self._repository.update_quote_part(part_id, payload)

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

    def get_part_feature_set(self, part_id: UUID) -> PartFeatureSetResponse:
        return self._repository.get_part_feature_set(part_id)

    def replace_part_feature_set(self, part_id: UUID, payload: PartFeatureSetUpsertRequest) -> PartFeatureSetResponse:
        return self._repository.replace_part_feature_set(part_id, payload)

    def create_part_feature(self, part_id: UUID, payload: PartFeatureCreateRequest) -> PartFeatureResponse:
        return self._repository.create_part_feature(part_id, payload)

    def update_part_feature(self, feature_id: UUID, payload: PartFeatureUpdateRequest) -> Optional[PartFeatureResponse]:
        return self._repository.update_part_feature(feature_id, payload)

    def start_analysis(self, quote_id: UUID) -> UUID:
        source_text = self._repository.get_quote_source_text(quote_id)
        return self.start_analysis_from_text(quote_id, source_text=source_text)

    def start_analysis_from_text(
        self,
        quote_id: UUID,
        *,
        source_text: str,
        user_cue: Optional[str] = None,
        part_cues: Optional[list[dict[str, Any]]] = None,
        page_image_data_urls: Optional[list[str]] = None,
    ) -> UUID:
        run_id = self._repository.create_analysis_run(
            quote_id,
            model_name=self._analysis_model_name(),
            stage="routing",
        )
        try:
            analysis_text = self._build_analysis_text(
                source_text=source_text,
                user_cue=user_cue,
                part_cues=part_cues,
            )
            result = self._analysis_pipeline.run(
                source_text=analysis_text,
                page_image_data_urls=page_image_data_urls or [],
            )
            metadata = result.get("step1_metadata", {})
            classification = result.get("step2_classification", {})
            complexity = result.get("step3_complexity", {})
            feature_details = result.get("step4_feature_details", {})
            routings = result.get("step5_routings", result.get("step4_routings", {}))
            part_ref = self._resolve_target_part_ref(
                part_cues=part_cues,
                metadata=metadata if isinstance(metadata, dict) else {},
            )

            part_id = self._repository.upsert_part_from_analysis(
                quote_id=quote_id,
                metadata=metadata if isinstance(metadata, dict) else {},
                classification=classification if isinstance(classification, dict) else {},
                complexity=complexity if isinstance(complexity, dict) else {},
                target_part_ref=part_ref,
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
            self._repository.save_part_extraction(
                part_id=part_id,
                model_name=self._analysis_model_name(),
                prompt_version="step4_feature_details_v1",
                payload=feature_details if isinstance(feature_details, dict) else {},
                confidence=(feature_details.get("confidence") if isinstance(feature_details, dict) else None),
            )
            feature_set_id = self._repository.save_part_feature_set_from_llm(
                part_id=part_id,
                run_id=run_id,
                payload=feature_details if isinstance(feature_details, dict) else {},
            )

            created_routings = self._repository.save_generated_routings(
                part_id=part_id,
                scenarios_payload=routings if isinstance(routings, dict) else {},
                run_id=run_id,
            )
            result["analysis_input"] = {
                "user_cue": user_cue,
                "part_cues": part_cues or [],
                "target_part_ref": part_ref,
            }
            result["created_part_id"] = str(part_id)
            result["created_routing_ids"] = [str(r.routing_id) for r in created_routings]
            if feature_set_id:
                result["created_feature_set_id"] = str(feature_set_id)
            self._repository.complete_analysis_run(run_id, output=result)
        except Exception as exc:
            self._repository.fail_analysis_run(run_id, str(exc))
        return run_id

    @staticmethod
    def _build_analysis_text(
        *,
        source_text: str,
        user_cue: Optional[str],
        part_cues: Optional[list[dict[str, Any]]],
    ) -> str:
        sections: list[str] = []
        if source_text and source_text.strip():
            sections.append(source_text.strip())
        if user_cue and user_cue.strip():
            sections.append(f"[Estimator Cue]\n{user_cue.strip()}")
        if part_cues:
            sections.append("[Part Cues JSON]\n" + json.dumps(part_cues, ensure_ascii=True))
        return "\n\n".join(sections).strip()

    @staticmethod
    def _resolve_target_part_ref(
        *,
        part_cues: Optional[list[dict[str, Any]]],
        metadata: dict[str, Any],
    ) -> Optional[str]:
        if part_cues:
            for cue in part_cues:
                if not isinstance(cue, dict):
                    continue
                raw_ref = cue.get("part_ref")
                if raw_ref is None:
                    continue
                part_ref = str(raw_ref).strip()
                if part_ref:
                    return part_ref[:100]
        for key in ("customer_part_number", "internal_part_number"):
            raw_value = metadata.get(key)
            if raw_value is None:
                continue
            value = str(raw_value).strip()
            if value:
                return value[:100]
        return None

    def get_job(self, job_id: UUID) -> Optional[JobStatusResponse]:
        return self._repository.get_job(job_id)

    def list_quote_jobs(self, quote_id: UUID, *, status: Optional[str], limit: int = 200) -> list[JobStatusResponse]:
        return self._repository.list_quote_jobs(quote_id, status=status, limit=limit)

from __future__ import annotations

import asyncio
import json
import logging
import re
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError
from typing import Any, Optional
from uuid import UUID

from app.domain.erp.item_attribute_service import ItemAttributeService
from app.domain.erp.models import (
    ItemAttributeCatalogEntry,
    ItemAttributeCatalogValue,
    ItemAttributeSelection,
    ItemAttributeValueEntry,
)
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
    QuoteCreateRequest,
    QuotePartSummary,
    QuotePartUpdateRequest,
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
from app.integrations.cedule_ventes_sous_traitance_repository import (
    CeduleVentesSousTraitanceRepository,
)
from app.settings import settings

logger = logging.getLogger(__name__)

_TREATMENT_PATTERNS: tuple[tuple[re.Pattern[str], tuple[str, str]], ...] = (
    (re.compile(r"\b(heat[\s-]*treat(?:ment)?|hard(?:en|ening)|tempering|nitrid(?:e|ing)|carburiz(?:e|ing))\b", re.IGNORECASE), ("OP_HEAT_TREAT", "Heat treatment / hardening")),
    (re.compile(r"\b(plat(?:e|ing)|anodiz(?:e|ing)|passivat(?:e|ion)|black[\s-]*oxide|zinc|nickel|chrome)\b", re.IGNORECASE), ("OP_PLATING", "Plating / surface treatment")),
    (re.compile(r"\b(paint(?:ing)?|powder[\s-]*coat(?:ing)?)\b", re.IGNORECASE), ("OP_PAINT", "Paint / coating")),
    (re.compile(r"\b(threatment)\b", re.IGNORECASE), ("OP_HEAT_TREAT", "Heat treatment / hardening")),
)

_AXIS_REGEX = re.compile(r"\b(4(?:th)?[\s-]*axis|5(?:th)?[\s-]*axis|4x|5x|trunnion|rotary)\b", re.IGNORECASE)
_POST_CNC_SUPPORT_PATTERNS: tuple[tuple[re.Pattern[str], tuple[str, str]], ...] = (
    (re.compile(r"\b(deburr(?:ing)?|deburring|deburrage|edge[\s-]*break)\b", re.IGNORECASE), ("OP_DEBURR", "Deburring")),
    (re.compile(r"\b(quality[\s-]*control|quality[\s-]*check|final[\s-]*inspect(?:ion)?|inspection|dimensional[\s-]*check|cmm)\b", re.IGNORECASE), ("OP_QC", "Quality control")),
)
_CNC_STEP_REGEX = re.compile(
    r"\b(cnc|machin(?:e|ing)|mill(?:ing)?|drill(?:ing)?|bore|boring|ream(?:ing)?|tap(?:ping)?|thread(?:ing)?|face(?:ing)?|turn(?:ing)?|lathe|rough(?:ing)?|finish(?:ing)?)\b",
    re.IGNORECASE,
)
_MISSING_MATERIAL_MARKERS = {"", "unknown", "n/a", "n a", "na", "none", "null", "tbd", "to be defined"}


class VentesSousTraitanceService:
    def __init__(
        self,
        repository: Optional[CeduleVentesSousTraitanceRepository] = None,
        analysis_pipeline: Optional[VentesSousTraitanceAnalysisPipeline] = None,
        item_attribute_service: Optional[ItemAttributeService] = None,
    ) -> None:
        self._repository = repository or CeduleVentesSousTraitanceRepository()
        self._analysis_pipeline = analysis_pipeline or VentesSousTraitanceAnalysisPipeline()
        self._item_attribute_service = item_attribute_service

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
            metadata = result.get("step1_metadata")
            if not isinstance(metadata, dict):
                metadata = {}
                result["step1_metadata"] = metadata

            classification = result.get("step2_classification")
            if not isinstance(classification, dict):
                classification = {}
                result["step2_classification"] = classification

            complexity = result.get("step3_complexity")
            if not isinstance(complexity, dict):
                complexity = {}
                result["step3_complexity"] = complexity

            feature_details = result.get("step4_feature_details")
            if not isinstance(feature_details, dict):
                feature_details = {}
                result["step4_feature_details"] = feature_details

            self._normalize_feature_details(feature_details)
            resolved_material = self._resolve_missing_raw_material(
                source_text=analysis_text,
                metadata=metadata,
                classification=classification,
                feature_details=feature_details,
            )
            if resolved_material:
                result["resolved_raw_material"] = resolved_material

            raw_routings = result.get("step5_routings", result.get("step4_routings", {}))
            routings = self._normalize_routing_payload(
                raw_routings if isinstance(raw_routings, dict) else {},
                feature_details=feature_details,
            )
            result["step5_routings"] = routings
            result["step4_routings"] = routings
            part_ref = self._resolve_target_part_ref(
                part_cues=part_cues,
                metadata=metadata,
            )

            part_id = self._repository.upsert_part_from_analysis(
                quote_id=quote_id,
                metadata=metadata,
                classification=classification,
                complexity=complexity,
                target_part_ref=part_ref,
            )

            self._repository.save_part_extraction(
                part_id=part_id,
                model_name=self._analysis_model_name(),
                prompt_version="step1_metadata_v1",
                payload=metadata,
                confidence=metadata.get("confidence"),
            )
            self._repository.save_part_extraction(
                part_id=part_id,
                model_name=self._analysis_model_name(),
                prompt_version="step2_classification_v1",
                payload=classification,
                confidence=classification.get("confidence"),
            )
            self._repository.save_part_extraction(
                part_id=part_id,
                model_name=self._analysis_model_name(),
                prompt_version="step3_complexity_v1",
                payload=complexity,
                confidence=complexity.get("confidence"),
            )
            self._repository.save_part_extraction(
                part_id=part_id,
                model_name=self._analysis_model_name(),
                prompt_version="step4_feature_details_v1",
                payload=feature_details,
                confidence=feature_details.get("confidence"),
            )
            feature_set_id = self._repository.save_part_feature_set_from_llm(
                part_id=part_id,
                run_id=run_id,
                payload=feature_details,
            )

            created_routings = self._repository.save_generated_routings(
                part_id=part_id,
                scenarios_payload=routings,
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

    def _normalize_feature_details(self, feature_details: dict[str, Any]) -> None:
        part_summary = feature_details.get("part_summary")
        if not isinstance(part_summary, dict):
            part_summary = {}
            feature_details["part_summary"] = part_summary

        additional_operations = feature_details.get("additional_operations")
        if not isinstance(additional_operations, list):
            additional_operations = []
            feature_details["additional_operations"] = additional_operations
        feature_details["additional_operations"] = [str(v) for v in additional_operations if str(v).strip()]

        general_notes = feature_details.get("general_notes")
        if not isinstance(general_notes, list):
            general_notes = []
            feature_details["general_notes"] = general_notes
        feature_details["general_notes"] = [str(v) for v in general_notes if str(v).strip()]

        setups = part_summary.get("number_of_setups")
        if setups is not None:
            try:
                normalized_setups = min(3, max(1, int(str(setups))))
                part_summary["number_of_setups"] = normalized_setups
            except (TypeError, ValueError):
                part_summary["number_of_setups"] = None

        axis_flag = part_summary.get("requires_4th_or_5th_axis")
        if isinstance(axis_flag, str):
            lowered = axis_flag.strip().lower()
            if lowered in {"true", "yes", "1"}:
                part_summary["requires_4th_or_5th_axis"] = True
            elif lowered in {"false", "no", "0"}:
                part_summary["requires_4th_or_5th_axis"] = False

        detected_treatments = self._extract_post_machining_operations(feature_details)
        for _, operation_desc in detected_treatments:
            if not any(operation_desc.lower() in str(op).lower() for op in feature_details["additional_operations"]):
                feature_details["additional_operations"].append(operation_desc)

    def _normalize_routing_payload(
        self,
        scenarios_payload: dict[str, Any],
        *,
        feature_details: dict[str, Any],
    ) -> dict[str, Any]:
        scenarios = scenarios_payload.get("scenarios") if isinstance(scenarios_payload, dict) else None
        if not isinstance(scenarios, list):
            return {"scenarios": []}

        part_summary = feature_details.get("part_summary")
        part_summary = part_summary if isinstance(part_summary, dict) else {}
        max_setups_raw = part_summary.get("number_of_setups")
        max_setups: int | None = None
        if max_setups_raw is not None:
            try:
                max_setups = max(1, int(str(max_setups_raw)))
            except (TypeError, ValueError):
                max_setups = None

        requires_axis = part_summary.get("requires_4th_or_5th_axis")
        treatment_operations = self._extract_post_machining_operations(feature_details)

        normalized_scenarios: list[dict[str, Any]] = []
        for raw_scenario in scenarios[:3]:
            if not isinstance(raw_scenario, dict):
                continue
            scenario = dict(raw_scenario)
            assumptions = scenario.get("assumptions")
            if not isinstance(assumptions, list):
                assumptions = []
            assumptions = [str(v) for v in assumptions if v is not None]

            raw_steps = scenario.get("steps")
            steps: list[dict[str, Any]] = []
            if isinstance(raw_steps, list):
                for raw_step in raw_steps:
                    if isinstance(raw_step, dict):
                        steps.append(dict(raw_step))

            self._sanitize_axis_constraints(steps, requires_axis=requires_axis, assumptions=assumptions)
            steps = self._enforce_setup_limit(steps, max_setups=max_setups, assumptions=assumptions)
            steps = self._append_default_post_cnc_steps(steps)
            steps = self._append_missing_treatment_steps(steps, treatment_operations=treatment_operations)

            scenario["assumptions"] = assumptions
            scenario["steps"] = steps
            normalized_scenarios.append(scenario)
        return {"scenarios": normalized_scenarios}

    @staticmethod
    def _enforce_setup_limit(
        steps: list[dict[str, Any]],
        *,
        max_setups: int | None,
        assumptions: list[str],
    ) -> list[dict[str, Any]]:
        effective_max_setups = max_setups if max_setups is not None else 3
        cnc_steps = [step for step in steps if VentesSousTraitanceService._is_cnc_machining_step(step)]
        if len(cnc_steps) <= effective_max_setups:
            return steps

        overflow = cnc_steps[effective_max_setups:]
        overflow_text = "; ".join(
            str(step.get("description") or step.get("operation_code") or "operation").strip()
            for step in overflow
        ).strip()
        kept_cnc = 0
        normalized: list[dict[str, Any]] = []
        for step in steps:
            if not VentesSousTraitanceService._is_cnc_machining_step(step):
                normalized.append(step)
                continue
            kept_cnc += 1
            if kept_cnc > effective_max_setups:
                continue
            if kept_cnc == effective_max_setups and overflow_text:
                last_description = str(step.get("description") or "CNC setup").strip()
                step["description"] = f"{last_description} (includes: {overflow_text[:280]})"
            normalized.append(step)

        assumptions.append(
            f"Collapsed {len(overflow)} extra CNC setup steps to respect number_of_setups={effective_max_setups}."
        )
        return normalized

    @staticmethod
    def _append_default_post_cnc_steps(steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not any(VentesSousTraitanceService._is_cnc_machining_step(step) for step in steps):
            return steps

        existing_codes: set[str] = set()
        for step in steps:
            combined = f"{step.get('operation_code') or ''} {step.get('description') or ''}".strip()
            support_operation = VentesSousTraitanceService._classify_post_cnc_support_operation(combined)
            if support_operation:
                existing_codes.add(support_operation[0])

        inserts: list[dict[str, Any]] = []
        if "OP_DEBURR" not in existing_codes:
            inserts.append(
                {
                    "operation_code": "OP_DEBURR",
                    "description": "Deburring after CNC machining",
                    "machine_group_id": "BENCH_FINISHING",
                    "setup_time_min": 0,
                    "cycle_time_min": 0,
                    "handling_time_min": 0,
                    "inspection_time_min": 0,
                    "time_confidence": 0.45,
                }
            )
        if "OP_QC" not in existing_codes:
            inserts.append(
                {
                    "operation_code": "OP_QC",
                    "description": "Quality control after CNC machining",
                    "machine_group_id": "QUALITY_CONTROL",
                    "setup_time_min": 0,
                    "cycle_time_min": 0,
                    "handling_time_min": 0,
                    "inspection_time_min": 0,
                    "time_confidence": 0.45,
                }
            )
        if not inserts:
            return steps

        normalized = list(steps)
        insert_index = next(
            (idx for idx, step in enumerate(normalized) if VentesSousTraitanceService._is_treatment_step(step)),
            len(normalized),
        )
        normalized[insert_index:insert_index] = inserts
        return normalized

    @staticmethod
    def _append_missing_treatment_steps(
        steps: list[dict[str, Any]],
        *,
        treatment_operations: list[tuple[str, str]],
    ) -> list[dict[str, Any]]:
        if not treatment_operations:
            return steps

        existing_signatures: set[tuple[str, str]] = set()
        for step in steps:
            op_code = str(step.get("operation_code") or "").strip().upper()
            description = str(step.get("description") or "").strip().lower()
            existing_signatures.add((op_code, description))

        normalized = list(steps)
        for op_code, operation_desc in treatment_operations:
            key = (op_code.upper(), operation_desc.lower())
            if key in existing_signatures:
                continue
            already_present = any(
                op_code.upper() == str(step.get("operation_code") or "").strip().upper()
                or operation_desc.lower() in str(step.get("description") or "").lower()
                for step in normalized
            )
            if already_present:
                continue
            normalized.append(
                {
                    "operation_code": op_code,
                    "description": f"Post-machining {operation_desc}",
                    "machine_group_id": "SUBCON",
                    "setup_time_min": 0,
                    "cycle_time_min": 0,
                    "handling_time_min": 0,
                    "inspection_time_min": 0,
                    "time_confidence": 0.35,
                }
            )
        return normalized

    @staticmethod
    def _sanitize_axis_constraints(
        steps: list[dict[str, Any]],
        *,
        requires_axis: Any,
        assumptions: list[str],
    ) -> None:
        if requires_axis is not False:
            return
        changed = False
        for step in steps:
            operation_code = str(step.get("operation_code") or "")
            description = str(step.get("description") or "")
            machine_group = str(step.get("machine_group_id") or "")
            combined = f"{operation_code} {description} {machine_group}"
            if not _AXIS_REGEX.search(combined):
                continue
            changed = True
            if description:
                cleaned = _AXIS_REGEX.sub("", description)
                cleaned = re.sub(r"\s{2,}", " ", cleaned).strip(" -,;")
                step["description"] = cleaned or "Machining operation"
            if machine_group and _AXIS_REGEX.search(machine_group):
                step["machine_group_id"] = None
            if operation_code and _AXIS_REGEX.search(operation_code):
                step["operation_code"] = "OP_MACH"
        if changed:
            assumptions.append("Removed 4th/5th-axis wording to align with requires_4th_or_5th_axis=false.")

    def _resolve_missing_raw_material(
        self,
        *,
        source_text: str,
        metadata: dict[str, Any],
        classification: dict[str, Any],
        feature_details: dict[str, Any],
    ) -> dict[str, Any] | None:
        part_summary = feature_details.get("part_summary")
        if not isinstance(part_summary, dict):
            return None

        if not self._material_is_missing(metadata.get("material_spec")):
            return None
        if not self._material_is_missing(part_summary.get("material")):
            return None
        if part_summary.get("customer_provides_material") is True:
            return None

        attribute_service = self._get_item_attribute_service()
        if attribute_service is None:
            return None

        try:
            catalog = self._run_async_blocking(attribute_service.get_attribute_catalog(), timeout_seconds=45)
        except Exception as exc:  # pragma: no cover - safety fallback
            logger.warning("Failed to load item attribute catalog for raw material selection: %s", exc)
            return None

        selections = self._build_raw_material_selections(
            source_text=source_text,
            metadata=metadata,
            classification=classification,
            feature_details=feature_details,
            catalog_entries=list(catalog.attributes),
        )
        if not selections:
            return None

        lookup_result = None
        selected_subset: list[ItemAttributeSelection] = []
        for subset in self._selection_subsets(selections):
            try:
                lookup_result = self._run_async_blocking(
                    attribute_service.get_items_by_attributes(subset),
                    timeout_seconds=45,
                )
            except Exception as exc:  # pragma: no cover - safety fallback
                logger.warning("Item attribute lookup failed while selecting raw material: %s", exc)
                return None
            if lookup_result.item_ids:
                selected_subset = subset
                break

        if lookup_result is None or not lookup_result.item_ids:
            return None

        selected_item_id = lookup_result.item_ids[0]
        try:
            selected_item_attrs = self._run_async_blocking(
                attribute_service.get_item_attributes(selected_item_id),
                timeout_seconds=45,
            )
        except Exception as exc:  # pragma: no cover - safety fallback
            logger.warning("Failed to read selected item attributes for %s: %s", selected_item_id, exc)
            return None

        material_label = self._build_material_label(selected_item_attrs.attributes) or selected_item_id
        part_summary["material"] = material_label
        part_summary["material_item_id"] = selected_item_id
        part_summary["material_resolution"] = "erp_attribute_lookup"
        metadata["material_spec"] = material_label

        general_notes = feature_details.get("general_notes")
        if not isinstance(general_notes, list):
            general_notes = []
            feature_details["general_notes"] = general_notes
        note = f"Raw material auto-selected from ERP catalog: {material_label} (item {selected_item_id})."
        if note not in general_notes:
            general_notes.append(note)

        return {
            "item_id": selected_item_id,
            "material": material_label,
            "matched_item_count": len(lookup_result.item_ids),
            "selections": self._selection_display(selected_subset, catalog_entries=list(catalog.attributes)),
        }

    def _build_raw_material_selections(
        self,
        *,
        source_text: str,
        metadata: dict[str, Any],
        classification: dict[str, Any],
        feature_details: dict[str, Any],
        catalog_entries: list[ItemAttributeCatalogEntry],
    ) -> list[ItemAttributeSelection]:
        if not catalog_entries:
            return []

        context = self._material_context_text(
            source_text=source_text,
            metadata=metadata,
            feature_details=feature_details,
        )
        shape = self._normalize_text(classification.get("shape_class"))
        part_summary = feature_details.get("part_summary") if isinstance(feature_details.get("part_summary"), dict) else {}
        estimated_stock = (
            part_summary.get("estimated_raw_stock_size_mm")
            if isinstance(part_summary.get("estimated_raw_stock_size_mm"), dict)
            else {}
        )
        thickness_target = self._coerce_float(metadata.get("thickness_mm"))
        if thickness_target is None:
            thickness_target = self._coerce_float(estimated_stock.get("H"))
        diameter_target = None
        if "round" in shape:
            diameter_target = self._coerce_float(estimated_stock.get("W")) or self._coerce_float(estimated_stock.get("H"))

        material_attr = self._find_attribute(catalog_entries, include_terms=("mater",))
        subtype_attr = self._find_attribute(catalog_entries, include_terms=("sous", "type"))
        type_attr = self._find_attribute(catalog_entries, include_terms=("type",), exclude_terms=("sous",))
        diameter_attr = self._find_attribute(catalog_entries, include_terms=("dia", "ext"))
        thickness_attr = self._find_attribute(catalog_entries, include_terms=("epaisseur",))

        selections: list[ItemAttributeSelection] = []
        chosen_pairs: set[tuple[int, int]] = set()

        preferred_subtype_terms = ("barre ronde", "ronde", "tube") if "round" in shape else ("fer plat", "plaque")
        preferred_type_terms = ("scie",) if "round" in shape else ("plaque",)

        for attr, preferred_terms in (
            (material_attr, ()),
            (subtype_attr, preferred_subtype_terms),
            (type_attr, preferred_type_terms),
        ):
            value = self._select_option_value(attr, context=context, preferred_terms=preferred_terms)
            if attr is None or value is None:
                continue
            pair = (attr.attribute_id, value.value_id)
            if pair in chosen_pairs:
                continue
            selections.append(ItemAttributeSelection(attribute_id=attr.attribute_id, value_id=value.value_id))
            chosen_pairs.add(pair)

        for attr, target in ((diameter_attr, diameter_target), (thickness_attr, thickness_target)):
            value = self._select_numeric_value(attr, target=target)
            if attr is None or value is None:
                continue
            pair = (attr.attribute_id, value.value_id)
            if pair in chosen_pairs:
                continue
            selections.append(ItemAttributeSelection(attribute_id=attr.attribute_id, value_id=value.value_id))
            chosen_pairs.add(pair)

        return selections

    @staticmethod
    def _selection_subsets(selections: list[ItemAttributeSelection]) -> list[list[ItemAttributeSelection]]:
        if not selections:
            return []
        return [selections[:size] for size in range(len(selections), 0, -1)]

    @staticmethod
    def _find_attribute(
        entries: list[ItemAttributeCatalogEntry],
        *,
        include_terms: tuple[str, ...],
        exclude_terms: tuple[str, ...] = (),
    ) -> ItemAttributeCatalogEntry | None:
        for entry in entries:
            normalized_name = VentesSousTraitanceService._normalize_text(entry.attribute_name)
            if any(term not in normalized_name for term in include_terms):
                continue
            if any(term in normalized_name for term in exclude_terms):
                continue
            return entry
        return None

    @staticmethod
    def _select_option_value(
        entry: ItemAttributeCatalogEntry | None,
        *,
        context: str,
        preferred_terms: tuple[str, ...] = (),
    ) -> ItemAttributeCatalogValue | None:
        if entry is None or not entry.values:
            return None

        best: ItemAttributeCatalogValue | None = None
        best_score = 0
        for candidate in entry.values:
            normalized_value = VentesSousTraitanceService._normalize_text(candidate.value)
            if not normalized_value:
                continue
            score = 0
            if normalized_value in context:
                score += 120 + len(normalized_value)
            value_tokens = [tok for tok in normalized_value.split() if len(tok) >= 2]
            score += sum(10 for tok in value_tokens if tok in context)
            for preferred in preferred_terms:
                normalized_preferred = VentesSousTraitanceService._normalize_text(preferred)
                if normalized_preferred and normalized_preferred in normalized_value:
                    score += 20
            if score > best_score:
                best = candidate
                best_score = score
        return best

    @staticmethod
    def _select_numeric_value(
        entry: ItemAttributeCatalogEntry | None,
        *,
        target: float | None,
    ) -> ItemAttributeCatalogValue | None:
        if entry is None or target is None:
            return None
        best: ItemAttributeCatalogValue | None = None
        best_diff: float | None = None
        for candidate in entry.values:
            number = VentesSousTraitanceService._coerce_float(candidate.value)
            if number is None:
                continue
            diff = abs(number - target)
            if best_diff is None or diff < best_diff:
                best = candidate
                best_diff = diff
        return best

    @staticmethod
    def _selection_display(
        selections: list[ItemAttributeSelection],
        *,
        catalog_entries: list[ItemAttributeCatalogEntry],
    ) -> list[dict[str, Any]]:
        values_by_attribute = {entry.attribute_id: entry for entry in catalog_entries}
        display_rows: list[dict[str, Any]] = []
        for selection in selections:
            entry = values_by_attribute.get(selection.attribute_id)
            if entry is None:
                display_rows.append(
                    {
                        "attribute_id": selection.attribute_id,
                        "value_id": selection.value_id,
                    }
                )
                continue
            value = next((candidate for candidate in entry.values if candidate.value_id == selection.value_id), None)
            display_rows.append(
                {
                    "attribute_id": selection.attribute_id,
                    "attribute_name": entry.attribute_name,
                    "value_id": selection.value_id,
                    "value": value.value if value else None,
                }
            )
        return display_rows

    @staticmethod
    def _build_material_label(attributes: list[ItemAttributeValueEntry]) -> str:
        if not attributes:
            return ""
        normalized_map = {VentesSousTraitanceService._normalize_text(attr.attribute_name): attr.value for attr in attributes}
        ordered_names = (
            ("sous", "type"),
            ("mater",),
            ("dia", "ext"),
            ("epaisseur",),
            ("type",),
        )
        ordered_values: list[str] = []
        for target in ordered_names:
            for normalized_name, value in normalized_map.items():
                if any(term not in normalized_name for term in target):
                    continue
                if not value:
                    continue
                rendered = str(value).strip()
                if rendered and rendered not in ordered_values:
                    ordered_values.append(rendered)
                break
        if ordered_values:
            return " ".join(ordered_values)
        fallback = [str(attr.value).strip() for attr in attributes if str(attr.value).strip()]
        return " ".join(fallback)

    def _get_item_attribute_service(self) -> ItemAttributeService | None:
        if self._item_attribute_service is not None:
            return self._item_attribute_service
        try:
            self._item_attribute_service = ItemAttributeService()
        except Exception as exc:  # pragma: no cover - constructor safety fallback
            logger.warning("ItemAttributeService unavailable for raw material resolution: %s", exc)
            return None
        return self._item_attribute_service

    @staticmethod
    def _run_async_blocking(coro: Any, *, timeout_seconds: float) -> Any:
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(asyncio.run, coro)
            try:
                return future.result(timeout=timeout_seconds)
            except FuturesTimeoutError as exc:
                raise TimeoutError(f"Async operation timed out after {timeout_seconds}s") from exc

    @staticmethod
    def _extract_post_machining_operations(feature_details: dict[str, Any]) -> list[tuple[str, str]]:
        candidates: list[str] = []
        for key in ("additional_operations", "general_notes"):
            value = feature_details.get(key)
            if isinstance(value, list):
                candidates.extend(str(v) for v in value if v is not None)
        part_summary = feature_details.get("part_summary")
        if isinstance(part_summary, dict):
            notes = part_summary.get("notes")
            if notes:
                candidates.append(str(notes))

        operations: list[tuple[str, str]] = []
        seen_codes: set[str] = set()
        for text in candidates:
            normalized = text.strip()
            if not normalized:
                continue
            operation = VentesSousTraitanceService._classify_treatment_operation(normalized)
            if not operation:
                continue
            op_code, description = operation
            if op_code in seen_codes:
                continue
            operations.append((op_code, description))
            seen_codes.add(op_code)
        return operations

    @staticmethod
    def _classify_treatment_operation(text: str) -> tuple[str, str] | None:
        for pattern, operation in _TREATMENT_PATTERNS:
            if pattern.search(text):
                return operation
        return None

    @staticmethod
    def _classify_post_cnc_support_operation(text: str) -> tuple[str, str] | None:
        for pattern, operation in _POST_CNC_SUPPORT_PATTERNS:
            if pattern.search(text):
                return operation
        return None

    @staticmethod
    def _is_treatment_step(step: dict[str, Any]) -> bool:
        combined = f"{step.get('operation_code') or ''} {step.get('description') or ''}".strip()
        return VentesSousTraitanceService._classify_treatment_operation(combined) is not None

    @staticmethod
    def _is_post_machining_step(step: dict[str, Any]) -> bool:
        combined = f"{step.get('operation_code') or ''} {step.get('description') or ''}".strip()
        return (
            VentesSousTraitanceService._classify_treatment_operation(combined) is not None
            or VentesSousTraitanceService._classify_post_cnc_support_operation(combined) is not None
        )

    @staticmethod
    def _is_cnc_machining_step(step: dict[str, Any]) -> bool:
        combined = f"{step.get('operation_code') or ''} {step.get('description') or ''}".strip()
        machine_group = str(step.get("machine_group_id") or "").strip().upper()
        if VentesSousTraitanceService._is_post_machining_step(step):
            return False
        if "CNC" in machine_group:
            return True
        return _CNC_STEP_REGEX.search(combined) is not None

    @staticmethod
    def _material_context_text(
        *,
        source_text: str,
        metadata: dict[str, Any],
        feature_details: dict[str, Any],
    ) -> str:
        fragments = [source_text, str(metadata.get("material_spec") or "")]
        part_summary = feature_details.get("part_summary")
        if isinstance(part_summary, dict):
            fragments.append(str(part_summary.get("material") or ""))
            fragments.append(str(part_summary.get("notes") or ""))
        for key in ("additional_operations", "general_notes"):
            values = feature_details.get(key)
            if isinstance(values, list):
                fragments.extend(str(v) for v in values if v is not None)
        normalized_fragments = [VentesSousTraitanceService._normalize_text(value) for value in fragments if value]
        return " ".join(fragment for fragment in normalized_fragments if fragment)

    @staticmethod
    def _material_is_missing(value: Any) -> bool:
        normalized = VentesSousTraitanceService._normalize_text(value)
        return normalized in _MISSING_MATERIAL_MARKERS

    @staticmethod
    def _normalize_text(value: Any) -> str:
        if value is None:
            return ""
        text = str(value).strip().lower()
        if not text:
            return ""
        normalized = unicodedata.normalize("NFKD", text)
        normalized = normalized.encode("ascii", "ignore").decode("ascii")
        normalized = re.sub(r"[^a-z0-9.]+", " ", normalized)
        return re.sub(r"\s{2,}", " ", normalized).strip()

    @staticmethod
    def _coerce_float(value: Any) -> float | None:
        if value is None:
            return None
        text = str(value).strip().replace(",", ".")
        if not text:
            return None
        match = re.search(r"-?\d+(?:\.\d+)?", text)
        if not match:
            return None
        try:
            return float(match.group(0))
        except ValueError:
            return None

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

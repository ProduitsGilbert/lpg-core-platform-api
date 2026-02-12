from __future__ import annotations

from typing import Any

from app.adapters.ai_client import AIClient
from app.domain.ventes_sous_traitance.machine_config import (
    compact_machine_groups_context,
    load_machine_groups_config,
)


class VentesSousTraitanceAnalysisPipeline:
    """
    Multi-step LLM orchestration for subcontracting quote analysis.
    """

    def __init__(self, ai_client: AIClient | None = None) -> None:
        self._ai = ai_client or AIClient()

    def run(self, *, source_text: str) -> dict[str, Any]:
        step1 = self._step1_extract_metadata(source_text)
        step2 = self._step2_classify(source_text)
        step3 = self._step3_complexity(step2=step2, tolerance_note=str(step1.get("general_tolerances_note") or ""))
        step4 = self._step4_generate_routings(
            step1=step1,
            step2=step2,
            step3=step3,
        )
        return {
            "step1_metadata": step1,
            "step2_classification": step2,
            "step3_complexity": step3,
            "step4_routings": step4,
        }

    def _step1_extract_metadata(self, source_text: str) -> dict[str, Any]:
        schema = {
            "customer_part_number": None,
            "internal_part_number": None,
            "revision": None,
            "units": None,
            "material_spec": None,
            "thickness_mm": None,
            "quantity_requested": None,
            "general_tolerances_note": None,
            "surface_finish_requirements": None,
            "welding_requirements_note": None,
            "confidence": 0.0,
        }
        return self._ai.extract_structured_data(
            source_text,
            schema,
            context=(
                "Step 1 metadata extraction for manufacturing drawing. "
                "Return only factual values found in text; keep missing fields null."
            ),
        )

    def _step2_classify(self, source_text: str) -> dict[str, Any]:
        schema = {
            "shape_class": "unknown",
            "overall_envelope_mm": {"x": None, "y": None, "z": None},
            "overall_envelope_confidence": {"x": 0.0, "y": 0.0, "z": 0.0},
            "feature_counts": {
                "holes": None,
                "threaded_holes": None,
                "machined_faces": None,
                "bores": None,
                "pockets_slots": None,
            },
            "weight_estimate_kg": None,
            "confidence": 0.0,
        }
        return self._ai.extract_structured_data(
            source_text,
            schema,
            context=(
                "Step 2 part classification. Infer envelope and rough feature counts. "
                "If uncertain, keep unknown/null and lower confidence."
            ),
        )

    def _step3_complexity(self, *, step2: dict[str, Any], tolerance_note: str) -> dict[str, Any]:
        schema = {
            "complexity_score": 1,
            "drivers": [],
            "risk_flags": [],
            "confidence": 0.0,
        }
        payload = {
            "step2": step2,
            "tolerance_note": tolerance_note,
        }
        return self._ai.extract_structured_data(
            str(payload),
            schema,
            context=(
                "Step 3 complexity scoring from 1 to 5. "
                "Include concise drivers and manufacturing risk flags."
            ),
        )

    def _step4_generate_routings(
        self,
        *,
        step1: dict[str, Any],
        step2: dict[str, Any],
        step3: dict[str, Any],
    ) -> dict[str, Any]:
        machine_config = load_machine_groups_config()
        machine_context = compact_machine_groups_context(machine_config)
        schema = {
            "scenarios": [
                {
                    "scenario_name": "Baseline",
                    "rationale": "",
                    "confidence_score": 0.0,
                    "assumptions": [],
                    "unknowns": [],
                    "steps": [
                        {
                            "operation_code": "OP",
                            "description": "",
                            "machine_group_id": None,
                            "setup_time_min": 0,
                            "cycle_time_min": 0,
                            "handling_time_min": 0,
                            "inspection_time_min": 0,
                            "time_confidence": 0.0,
                        }
                    ],
                }
            ]
        }
        payload = {
            "step1_metadata": step1,
            "step2_classification": step2,
            "step3_complexity": step3,
            "machine_groups": machine_context,
        }
        return self._ai.extract_structured_data(
            str(payload),
            schema,
            context=(
                "Step 4 routing generation. Produce 1 to 3 realistic routing scenarios with "
                "ordered steps and setup/cycle/handling/inspection times in minutes."
            ),
        )


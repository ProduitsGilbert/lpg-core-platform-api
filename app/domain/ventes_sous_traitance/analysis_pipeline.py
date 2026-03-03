from __future__ import annotations

import re
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

    def run(self, *, source_text: str, page_image_data_urls: list[str] | None = None) -> dict[str, Any]:
        images = page_image_data_urls or []
        step1 = self._step1_extract_metadata(source_text, images)
        step2 = self._step2_classify(source_text, images)
        step3 = self._step3_complexity(step2=step2, tolerance_note=str(step1.get("general_tolerances_note") or ""))
        step4 = self._step4_extract_feature_details(
            step1=step1,
            step2=step2,
            step3=step3,
            source_text=source_text,
            page_image_data_urls=images,
        )
        step5 = self._step5_generate_routings(
            step1=step1,
            step2=step2,
            step3=step3,
            step4=step4,
        )
        return {
            "step1_metadata": step1,
            "step2_classification": step2,
            "step3_complexity": step3,
            "step4_feature_details": step4,
            "step5_routings": step5,
            # Backward compatibility for existing consumers.
            "step4_routings": step5,
        }

    def _step1_extract_metadata(self, source_text: str, page_image_data_urls: list[str]) -> dict[str, Any]:
        schema = {
            "customer_name": None,
            "customer_address": None,
            "customer_phone": None,
            "customer_email": None,
            "customer_website": None,
            "drawing_owner_note": None,
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
        result = self._ai.extract_structured_data(
            source_text,
            schema,
            context=(
                "Step 1 metadata extraction for manufacturing drawing. "
                "Use the drawing visuals as primary source of truth and extracted text as secondary support. "
                "Capture customer/company info from title block or legal notes. "
                "Return only factual values; keep missing fields null."
            ),
            image_inputs=page_image_data_urls,
        )
        # Keep strictly LLM-first when AI assistance is enabled.
        if self._ai.enabled:
            return result if isinstance(result, dict) else schema
        return self._enrich_step1_from_text(source_text, result if isinstance(result, dict) else schema)

    def _step2_classify(self, source_text: str, page_image_data_urls: list[str]) -> dict[str, Any]:
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
                "Step 2 part classification. Use full-page drawing visuals first, then extracted text for confirmation. "
                "Infer envelope and rough feature counts. "
                "If uncertain, keep unknown/null and lower confidence."
            ),
            image_inputs=page_image_data_urls,
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

    def _step4_extract_feature_details(
        self,
        *,
        step1: dict[str, Any],
        step2: dict[str, Any],
        step3: dict[str, Any],
        source_text: str,
        page_image_data_urls: list[str],
    ) -> dict[str, Any]:
        schema = {
            "part_summary": {
                "material": None,
                "customer_provides_material": None,
                "overall_bounding_box_mm": {"L": None, "W": None, "H": None},
                "estimated_raw_stock_size_mm": {"L": None, "W": None, "H": None},
                "number_of_setups": None,
                "requires_4th_or_5th_axis": None,
                "drilled_holes_count": None,
                "threaded_holes_count": None,
                "high_precision_features_count": None,
                "machined_faces_count": None,
                "notes": None,
            },
            "machining_features": [
                {
                    "feature_id": "F001",
                    "type": "flat_face",
                    "description": "",
                    "quantity": 1,
                    "dimensions": {
                        "width_mm": None,
                        "length_mm": None,
                        "depth_mm": None,
                        "diameter_mm": None,
                        "thread_spec": None,
                    },
                    "tolerance": None,
                    "surface_finish_ra": None,
                    "location": None,
                    "complexity_factors": [],
                    "estimated_operation_time_min": None,
                }
            ],
            "additional_operations": [],
            "general_notes": [],
            "confidence": 0.0,
        }
        payload = {
            "source_text": source_text,
            "step1_metadata": step1,
            "step2_classification": step2,
            "step3_complexity": step3,
            "feature_taxonomy": {
                "milling_facing": [
                    "flat_face",
                    "external_contour",
                    "pocket",
                    "slot_channel_groove",
                    "boss_protrusion_island",
                    "step_shoulder",
                ],
                "hole_making": [
                    "drilled_hole",
                    "bored_or_reamed_hole",
                    "threaded_hole",
                    "counterbore_or_countersink",
                ],
                "special_finishing": [
                    "chamfer_bevel_fillet",
                    "keyway_spline",
                    "oring_or_seal_groove",
                    "engraving_marking",
                ],
            },
            "complexity_risk_flags": [
                "aspect_ratio_gt_5",
                "tight_tolerance_lt_0.05mm_or_fit_class",
                "thin_walls",
                "multi_axis_or_multi_setup",
                "high_material_removal",
                "surface_finish_lt_ra_1.6",
                "material_specific_risk",
            ],
        }
        return self._ai.extract_structured_data(
            str(payload),
            schema,
            context=(
                "Step 4 detailed machining feature extraction for CNC steel parts. "
                "Use drawing visuals as primary evidence and treat extracted text as supplementary. "
                "Identify and quantify features using the provided taxonomy. "
                "Estimate drilled holes, threaded holes, high precision features "
                "(very tight tolerance or 3-digit precision), and number of machined faces. "
                "Set number_of_setups to CNC machining-center setup count only (integer 1 to 3). "
                "Do not count cutting, welding, deburring, quality control, inspection, or treatments in number_of_setups. "
                "If drawing mentions treatment, paint, plating, coating, or hardening after machining, add it in "
                "additional_operations using concise operation names. "
                "Use valid JSON only; keep unknown values null."
            ),
            image_inputs=page_image_data_urls,
        )

    def _step5_generate_routings(
        self,
        *,
        step1: dict[str, Any],
        step2: dict[str, Any],
        step3: dict[str, Any],
        step4: dict[str, Any],
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
        part_summary = step4.get("part_summary") if isinstance(step4, dict) and isinstance(step4.get("part_summary"), dict) else {}
        additional_operations = step4.get("additional_operations") if isinstance(step4, dict) else None
        payload = {
            "step1_metadata": step1,
            "step2_classification": step2,
            "step3_complexity": step3,
            "step4_feature_details": step4,
            "machine_groups": machine_context,
            "routing_constraints": {
                "max_machining_setups": part_summary.get("number_of_setups"),
                "requires_4th_or_5th_axis": part_summary.get("requires_4th_or_5th_axis"),
                "post_machining_operations": additional_operations if isinstance(additional_operations, list) else [],
                "rules": [
                    "A routing step is one machine center/station setup, not an individual feature.",
                    "Do not create routing steps for each hole/face/thread/chamfer; those are feature-level details within a setup.",
                    "Treat max_machining_setups as hard limit for CNC machining-center setups only (1 to 3).",
                    "If requires_4th_or_5th_axis is false, do not include any 4th/5th-axis operations.",
                    "Use machine_group_id values from machine_groups and keep them compatible with process family/capabilities.",
                    "For CNC-focused parts, include deburring and quality control after the last CNC setup unless already explicit.",
                    "Post-machining treatments (paint/plating/hardening/heat-treat) must be explicit final routing steps.",
                ],
            },
        }
        return self._ai.extract_structured_data(
            str(payload),
            schema,
            context=(
                "Step 5 routing generation. Produce 1 to 3 realistic routing scenarios with "
                "ordered steps and setup/cycle/handling/inspection times in minutes. "
                "A routing step represents a machine center/station setup, not per-feature machining actions. "
                "Respect max_machining_setups as hard ceiling for CNC setups only and keep CNC setups between 1 and 3. "
                "Group feature operations (holes/facing/threads/chamfers) into the appropriate CNC setup descriptions. "
                "Keep non-CNC centers explicit when needed (for example cutting, welding, heat treatment). "
                "Use only machine_group_id values present in machine_groups. "
                "Default to deburring then quality control after CNC when not already present. "
                "When post-machining treatments are required, represent each as its own routing step near the end."
            ),
        )

    def _enrich_step1_from_text(self, source_text: str, current: dict[str, Any]) -> dict[str, Any]:
        """
        Fill important metadata directly from text when LLM extraction is missing fields.
        """
        text = source_text or ""
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        lowered = text.lower()

        if not current.get("customer_name"):
            owner_match = re.search(r"property of\s+([A-Za-z0-9 .,&'()-]{3,80}?)(?:\.| is| est|$)", text, flags=re.IGNORECASE)
            if owner_match:
                current["customer_name"] = owner_match.group(1).strip(" .")
            else:
                company_line = self._find_company_line(lines)
                if company_line:
                    current["customer_name"] = company_line

        if not current.get("customer_phone"):
            phone_match = re.search(r"(?:(?:t[eé]l)|(?:tel)|(?:phone))[:\s]*([+()0-9 .-]{7,})", text, flags=re.IGNORECASE)
            if phone_match:
                current["customer_phone"] = phone_match.group(1).strip()

        if not current.get("customer_email"):
            email_match = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
            if email_match:
                current["customer_email"] = email_match.group(0)

        if not current.get("customer_website"):
            website_match = re.search(r"(?:https?://)?(?:www\.)?[A-Za-z0-9.-]+\.[A-Za-z]{2,}(?:/[A-Za-z0-9._~:/?#@!$&'()*+,;=-]*)?", text)
            if website_match and "." in website_match.group(0):
                current["customer_website"] = website_match.group(0)

        if not current.get("customer_address"):
            current["customer_address"] = self._find_address_block(lines)

        if not current.get("drawing_owner_note"):
            note_match = re.search(r"(All information.*?prohibited\.)", text, flags=re.IGNORECASE | re.DOTALL)
            if note_match:
                current["drawing_owner_note"] = " ".join(note_match.group(1).split())

        if not current.get("units"):
            if "dimensions imperial" in lowered or "lbm" in lowered or "inch" in lowered:
                current["units"] = "inch"
            elif " mm" in lowered or "dimensions metric" in lowered:
                current["units"] = "mm"

        if not current.get("material_spec"):
            material_match = re.search(r"(?:materiau|material)\s+([A-Za-z0-9 ./-]{2,60})", text, flags=re.IGNORECASE)
            if material_match:
                current["material_spec"] = material_match.group(1).strip(" .")

        if not current.get("revision"):
            rev_match = re.search(r"(?:\brev(?:ision)?\b[ .:-]*)([A-Z0-9]{1,6})", text, flags=re.IGNORECASE)
            if rev_match:
                current["revision"] = rev_match.group(1).upper()

        if current.get("confidence") in (None, 0, 0.0):
            current["confidence"] = 0.45
        return current

    def _find_company_line(self, lines: list[str]) -> str | None:
        company_keywords = (" inc", " ltee", " ltée", " ltd", " corporation", " fabrication", " industries", " international")
        for ln in lines:
            lowered = f" {ln.lower()} "
            if any(keyword in lowered for keyword in company_keywords) and len(ln) <= 90:
                # Avoid generic legal sentence fragments as company name.
                if "all information" in lowered or "prohibited" in lowered:
                    continue
                return ln.strip(" .")
        return None

    def _find_address_block(self, lines: list[str]) -> str | None:
        postal_pattern = re.compile(r"[A-Z]\d[A-Z]\s?\d[A-Z]\d")
        for idx, ln in enumerate(lines):
            if postal_pattern.search(ln.upper()):
                start = max(0, idx - 3)
                block = lines[start : idx + 1]
                return ", ".join(block)
        return None

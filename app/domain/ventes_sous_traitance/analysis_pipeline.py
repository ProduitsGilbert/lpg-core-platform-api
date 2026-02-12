from __future__ import annotations

from typing import Any
import re

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
                "Capture customer/company info from title block or legal notes. "
                "Return only factual values found in text; keep missing fields null."
            ),
        )
        # Keep strictly LLM-first when AI assistance is enabled.
        if self._ai.enabled:
            return result if isinstance(result, dict) else schema
        return self._enrich_step1_from_text(source_text, result if isinstance(result, dict) else schema)

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

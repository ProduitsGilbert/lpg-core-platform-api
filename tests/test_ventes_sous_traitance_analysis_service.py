from __future__ import annotations

from unittest.mock import MagicMock
from uuid import uuid4

from app.domain.erp.models import (
    ItemAttributeCatalogEntry,
    ItemAttributeCatalogResponse,
    ItemAttributeCatalogValue,
    ItemAttributeItemLookupResponse,
    ItemAttributeSelection,
    ItemAttributesResponse,
    ItemAttributeValueEntry,
)
from app.domain.ventes_sous_traitance.service import VentesSousTraitanceService


def test_start_analysis_runs_multistep_pipeline_and_persists_outputs() -> None:
    quote_id = uuid4()
    run_id = uuid4()
    part_id = uuid4()
    routing_id = uuid4()

    repository = MagicMock()
    repository.create_analysis_run.return_value = run_id
    repository.get_quote_source_text.return_value = "drawing notes"
    repository.upsert_part_from_analysis.return_value = part_id
    routing = MagicMock()
    routing.routing_id = routing_id
    repository.save_generated_routings.return_value = [routing]

    pipeline = MagicMock()
    pipeline.run.return_value = {
        "step1_metadata": {"customer_part_number": "A-100", "confidence": 0.8},
        "step2_classification": {"shape_class": "prismatic", "confidence": 0.7},
        "step3_complexity": {"complexity_score": 3, "confidence": 0.75},
        "step4_routings": {"scenarios": [{"scenario_name": "Baseline", "steps": []}]},
    }

    service = VentesSousTraitanceService(repository=repository, analysis_pipeline=pipeline)
    returned_run_id = service.start_analysis(quote_id)

    assert returned_run_id == run_id
    repository.create_analysis_run.assert_called_once()
    pipeline.run.assert_called_once_with(source_text="drawing notes", page_image_data_urls=[])
    repository.complete_analysis_run.assert_called_once()
    repository.fail_analysis_run.assert_not_called()


def test_start_analysis_marks_run_failed_on_pipeline_exception() -> None:
    quote_id = uuid4()
    run_id = uuid4()

    repository = MagicMock()
    repository.create_analysis_run.return_value = run_id
    repository.get_quote_source_text.return_value = "drawing notes"

    pipeline = MagicMock()
    pipeline.run.side_effect = RuntimeError("LLM unavailable")

    service = VentesSousTraitanceService(repository=repository, analysis_pipeline=pipeline)
    returned_run_id = service.start_analysis(quote_id)

    assert returned_run_id == run_id
    repository.fail_analysis_run.assert_called_once()
    repository.complete_analysis_run.assert_not_called()


def test_start_analysis_from_text_includes_user_guidance() -> None:
    quote_id = uuid4()
    run_id = uuid4()
    part_id = uuid4()

    repository = MagicMock()
    repository.create_analysis_run.return_value = run_id
    repository.upsert_part_from_analysis.return_value = part_id
    repository.save_generated_routings.return_value = []

    pipeline = MagicMock()
    pipeline.run.return_value = {
        "step1_metadata": {"customer_part_number": "A-100", "confidence": 0.8},
        "step2_classification": {"shape_class": "prismatic", "confidence": 0.7},
        "step3_complexity": {"complexity_score": 2, "confidence": 0.7},
        "step4_routings": {"scenarios": []},
    }

    service = VentesSousTraitanceService(repository=repository, analysis_pipeline=pipeline)
    returned_run_id = service.start_analysis_from_text(
        quote_id,
        source_text="DOC TEXT",
        user_cue="Prefer no welding",
        part_cues=[{"part_ref": "A", "cue": "Machine only"}],
    )

    assert returned_run_id == run_id
    pipeline.run.assert_called_once()
    called_text = pipeline.run.call_args.kwargs["source_text"]
    called_images = pipeline.run.call_args.kwargs["page_image_data_urls"]
    assert "DOC TEXT" in called_text
    assert "[Estimator Cue]" in called_text
    assert "Prefer no welding" in called_text
    assert "[Part Cues JSON]" in called_text
    assert called_images == []


def test_start_analysis_normalizes_routing_setups_and_treatment_steps() -> None:
    quote_id = uuid4()
    run_id = uuid4()
    part_id = uuid4()

    repository = MagicMock()
    repository.create_analysis_run.return_value = run_id
    repository.upsert_part_from_analysis.return_value = part_id
    repository.save_generated_routings.return_value = []

    pipeline = MagicMock()
    pipeline.run.return_value = {
        "step1_metadata": {"confidence": 0.8},
        "step2_classification": {"shape_class": "prismatic", "confidence": 0.7},
        "step3_complexity": {"complexity_score": 2, "confidence": 0.7},
        "step4_feature_details": {
            "part_summary": {
                "number_of_setups": 2,
                "requires_4th_or_5th_axis": False,
            },
            "additional_operations": ["Heat treatment after machining"],
            "general_notes": [],
        },
        "step5_routings": {
            "scenarios": [
                {
                    "scenario_name": "Baseline",
                    "assumptions": [],
                    "steps": [
                        {"operation_code": "OP_1", "description": "Setup 1 milling"},
                        {"operation_code": "OP_2", "description": "Setup 2 drilling"},
                        {"operation_code": "OP_3", "description": "Setup 3 finishing"},
                        {"operation_code": "OP_4", "description": "4th-axis contouring"},
                    ],
                }
            ]
        },
    }

    service = VentesSousTraitanceService(repository=repository, analysis_pipeline=pipeline)
    returned_run_id = service.start_analysis_from_text(quote_id, source_text="DOC TEXT")

    assert returned_run_id == run_id
    saved_payload = repository.save_generated_routings.call_args.kwargs["scenarios_payload"]
    steps = saved_payload["scenarios"][0]["steps"]
    assert len(steps) == 3
    assert "includes:" in str(steps[1]["description"])
    assert steps[-1]["operation_code"] == "OP_HEAT_TREAT"
    assumptions = saved_payload["scenarios"][0]["assumptions"]
    assert any("number_of_setups=2" in item for item in assumptions)
    assert any("requires_4th_or_5th_axis=false" in item for item in assumptions)


class _StubItemAttributeService:
    async def get_attribute_catalog(self) -> ItemAttributeCatalogResponse:
        return ItemAttributeCatalogResponse(
            attributes=[
                ItemAttributeCatalogEntry(
                    attribute_id=2,
                    attribute_name="Matériel",
                    attribute_type="Option",
                    values=[ItemAttributeCatalogValue(value_id=332, value="1018")],
                ),
                ItemAttributeCatalogEntry(
                    attribute_id=3,
                    attribute_name="Type",
                    attribute_type="Option",
                    values=[
                        ItemAttributeCatalogValue(value_id=6, value="SCIE"),
                        ItemAttributeCatalogValue(value_id=7, value="PLAQUE"),
                    ],
                ),
                ItemAttributeCatalogEntry(
                    attribute_id=4,
                    attribute_name="Sous-Type",
                    attribute_type="Option",
                    values=[ItemAttributeCatalogValue(value_id=9, value="BARRE RONDE")],
                ),
                ItemAttributeCatalogEntry(
                    attribute_id=7,
                    attribute_name="Dia Exterieur",
                    attribute_type="Decimal",
                    values=[ItemAttributeCatalogValue(value_id=744, value="0.125")],
                ),
            ]
        )

    async def get_items_by_attributes(self, selections: list[ItemAttributeSelection]) -> ItemAttributeItemLookupResponse:
        return ItemAttributeItemLookupResponse(
            selections=selections,
            item_ids=["0430204"],
        )

    async def get_item_attributes(self, item_no: str) -> ItemAttributesResponse:
        assert item_no == "0430204"
        return ItemAttributesResponse(
            item_id=item_no,
            attributes=[
                ItemAttributeValueEntry(
                    attribute_id=2,
                    attribute_name="Matériel",
                    attribute_type="Option",
                    value_id=332,
                    value="1018",
                ),
                ItemAttributeValueEntry(
                    attribute_id=3,
                    attribute_name="Type",
                    attribute_type="Option",
                    value_id=6,
                    value="SCIE",
                ),
                ItemAttributeValueEntry(
                    attribute_id=4,
                    attribute_name="Sous-Type",
                    attribute_type="Option",
                    value_id=9,
                    value="BARRE RONDE",
                ),
                ItemAttributeValueEntry(
                    attribute_id=7,
                    attribute_name="Dia Exterieur",
                    attribute_type="Decimal",
                    value_id=744,
                    value="0.125",
                ),
            ],
        )


def test_start_analysis_auto_selects_raw_material_from_attribute_lookup() -> None:
    quote_id = uuid4()
    run_id = uuid4()
    part_id = uuid4()

    repository = MagicMock()
    repository.create_analysis_run.return_value = run_id
    repository.upsert_part_from_analysis.return_value = part_id
    repository.save_generated_routings.return_value = []

    pipeline = MagicMock()
    pipeline.run.return_value = {
        "step1_metadata": {"material_spec": None, "confidence": 0.8},
        "step2_classification": {"shape_class": "round", "confidence": 0.7},
        "step3_complexity": {"complexity_score": 2, "confidence": 0.7},
        "step4_feature_details": {
            "part_summary": {
                "material": None,
                "customer_provides_material": False,
                "estimated_raw_stock_size_mm": {"L": 50, "W": 0.125, "H": 0.125},
            },
            "additional_operations": [],
            "general_notes": [],
        },
        "step5_routings": {"scenarios": []},
    }

    service = VentesSousTraitanceService(
        repository=repository,
        analysis_pipeline=pipeline,
        item_attribute_service=_StubItemAttributeService(),
    )
    returned_run_id = service.start_analysis_from_text(quote_id, source_text="Round bar part, customer gave no material.")

    assert returned_run_id == run_id
    metadata = repository.upsert_part_from_analysis.call_args.kwargs["metadata"]
    assert metadata["material_spec"] == "BARRE RONDE 1018 0.125 SCIE"
    feature_payload = repository.save_part_feature_set_from_llm.call_args.kwargs["payload"]
    assert feature_payload["part_summary"]["material"] == "BARRE RONDE 1018 0.125 SCIE"
    assert feature_payload["part_summary"]["material_item_id"] == "0430204"

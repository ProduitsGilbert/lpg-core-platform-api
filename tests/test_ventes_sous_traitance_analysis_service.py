from __future__ import annotations

from uuid import uuid4
from unittest.mock import MagicMock

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

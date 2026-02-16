from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from pypdf import PdfReader
import pytest

from app.main import app
from app.api.v1.ventes_sous_traitance.router import get_service
from app.domain.ventes_sous_traitance.analysis_pipeline import VentesSousTraitanceAnalysisPipeline
from app.domain.ventes_sous_traitance.models import JobStatusResponse, QuoteSummary
from app.domain.ventes_sous_traitance.service import VentesSousTraitanceService


def _extract_pdf_text(pdf_path: Path) -> str:
    reader = PdfReader(str(pdf_path))
    return "\n".join((page.extract_text() or "") for page in reader.pages)


class _InMemoryAnalyzeRepo:
    def __init__(self, quote_id: UUID, source_text: str) -> None:
        now = datetime.now(timezone.utc)
        self._quote_id = quote_id
        self._source_text = source_text
        self._quote = QuoteSummary(
            quote_id=quote_id,
            quote_number="Q-SAMPLE-001",
            customer_id=uuid4(),
            status="draft",
            currency="CAD",
            due_date=None,
            sent_at=None,
            closed_at=None,
            loss_reason_code=None,
            loss_reason_note=None,
            notes="sample",
            created_at=now,
            updated_at=now,
        )
        self._runs: dict[UUID, JobStatusResponse] = {}

    @property
    def is_configured(self) -> bool:
        return True

    def get_quote(self, quote_id: UUID) -> QuoteSummary | None:
        if quote_id == self._quote_id:
            return self._quote
        return None

    def create_analysis_run(self, quote_id: UUID, *, model_name: str, stage: str = "routing") -> UUID:
        run_id = uuid4()
        self._runs[run_id] = JobStatusResponse(
            job_id=run_id,
            status="ok",
            stage=stage,
            progress=0.0,
            started_at=datetime.now(timezone.utc),
            ended_at=None,
            error_text=None,
            output_json=None,
        )
        return run_id

    def get_quote_source_text(self, quote_id: UUID) -> str:
        return self._source_text

    def upsert_part_from_analysis(self, quote_id: UUID, metadata: dict, classification: dict, complexity: dict) -> UUID:
        return uuid4()

    def save_part_extraction(self, part_id: UUID, *, model_name: str, prompt_version: str, payload: dict, confidence: float | None) -> None:
        return None

    def save_part_feature_set_from_llm(self, *, part_id: UUID, run_id: UUID, payload: dict) -> None:
        return None

    def save_generated_routings(self, part_id: UUID, scenarios_payload: dict, *, run_id: UUID | None = None) -> list:
        return []

    def complete_analysis_run(self, run_id: UUID, output: dict) -> None:
        self._runs[run_id] = JobStatusResponse(
            job_id=run_id,
            status="ok",
            stage="routing",
            progress=1.0,
            started_at=self._runs[run_id].started_at,
            ended_at=datetime.now(timezone.utc),
            error_text=None,
            output_json=json.dumps(output),
        )

    def fail_analysis_run(self, run_id: UUID, error_text: str) -> None:
        self._runs[run_id] = JobStatusResponse(
            job_id=run_id,
            status="error",
            stage="routing",
            progress=1.0,
            started_at=self._runs[run_id].started_at,
            ended_at=datetime.now(timezone.utc),
            error_text=error_text,
            output_json=None,
        )

    def get_job(self, job_id: UUID) -> JobStatusResponse | None:
        return self._runs.get(job_id)


class _StubAIClient:
    enabled = True

    def extract_structured_data(
        self,
        text: str,
        schema: dict,
        context: str | None = None,
        image_inputs: list[str] | None = None,
    ) -> dict:
        payload = dict(schema)
        if "customer_name" in payload:
            payload["customer_name"] = "Inotech Fabrication Inc" if "inotech" in text.lower() else "Unknown"
            payload["confidence"] = 0.9
        elif "shape_class" in payload:
            payload["shape_class"] = "prismatic"
            payload["confidence"] = 0.7
        elif "complexity_score" in payload:
            payload["complexity_score"] = 2
            payload["drivers"] = ["light plate work"]
            payload["risk_flags"] = []
            payload["confidence"] = 0.75
        elif "scenarios" in payload:
            payload["scenarios"] = [
                {
                    "scenario_name": "Baseline",
                    "rationale": "stub for endpoint pipeline test",
                    "confidence_score": 0.7,
                    "assumptions": [],
                    "unknowns": [],
                    "steps": [],
                }
            ]
        return payload


def test_analyze_endpoint_extracts_customer_from_sample_pdf() -> None:
    sample_pdf = Path("docs/sous-traitance_example/803100-1343_ok.pdf")
    if not sample_pdf.exists():
        pytest.skip(f"Sample PDF not found: {sample_pdf}")
    source_text = _extract_pdf_text(sample_pdf)
    quote_id = uuid4()

    repo = _InMemoryAnalyzeRepo(quote_id=quote_id, source_text=source_text)
    service = VentesSousTraitanceService(
        repository=repo,
        analysis_pipeline=VentesSousTraitanceAnalysisPipeline(ai_client=_StubAIClient()),
    )
    app.dependency_overrides[get_service] = lambda: service
    client = TestClient(app)

    analyze_response = client.post(f"/api/v1/vente-sous-traitance/quotes/{quote_id}/analyze")
    assert analyze_response.status_code == 200, analyze_response.text
    run_id = UUID(analyze_response.json()["job_id"])

    job_response = client.get(f"/api/v1/vente-sous-traitance/jobs/{run_id}")
    assert job_response.status_code == 200, job_response.text
    payload = job_response.json()
    assert payload["status"] == "ok"
    assert payload["output_json"]
    output = json.loads(payload["output_json"])
    step1 = output["step1_metadata"]
    customer_name = (step1.get("customer_name") or "").lower()
    assert "inotech" in customer_name

    app.dependency_overrides.clear()

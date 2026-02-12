from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4
from unittest.mock import MagicMock
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.api.v1.ventes_sous_traitance.router import get_service
from app.domain.ventes_sous_traitance.models import CustomerSummary, QuoteSummary


def _client_with_service(stub: MagicMock) -> TestClient:
    app.dependency_overrides[get_service] = lambda: stub
    return TestClient(app)


def _sample_quote() -> QuoteSummary:
    now = datetime.now(timezone.utc)
    return QuoteSummary(
        quote_id=uuid4(),
        quote_number="Q-0001",
        customer_id=uuid4(),
        status="draft",
        currency="CAD",
        due_date=None,
        sent_at=None,
        closed_at=None,
        loss_reason_code=None,
        loss_reason_note=None,
        notes="Initial quote",
        created_at=now,
        updated_at=now,
    )


def test_openapi_contains_ventes_tag() -> None:
    client = TestClient(app)
    response = client.get("/openapi.json")
    assert response.status_code == 200
    payload = response.json()
    quote_post = payload["paths"]["/api/v1/quotes"]["post"]
    assert "Ventes - Sous-Traitance" in quote_post["tags"]


def test_list_quotes_endpoint() -> None:
    stub = MagicMock()
    quote = _sample_quote()
    stub.list_quotes.return_value = [quote]
    client = _client_with_service(stub)
    response = client.get(f"/api/v1/quotes?status=draft&customer={quote.customer_id}")
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["quote_id"] == str(quote.quote_id)
    stub.list_quotes.assert_called_once_with(status="draft", customer_id=quote.customer_id)
    app.dependency_overrides.clear()


def test_list_customers_endpoint() -> None:
    stub = MagicMock()
    customer = CustomerSummary(
        customer_id=uuid4(),
        name="Produits Gilbert Inc.",
        email="sales@example.com",
        phone="555-111-2222",
        created_at=datetime.now(timezone.utc),
    )
    stub.list_customers.return_value = [customer]
    client = _client_with_service(stub)
    response = client.get("/api/v1/customers?q=gilbert&limit=50")
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["customer_id"] == str(customer.customer_id)
    assert payload[0]["name"] == customer.name
    stub.list_customers.assert_called_once_with(search="gilbert", limit=50)
    app.dependency_overrides.clear()


def test_get_quote_not_found() -> None:
    stub = MagicMock()
    stub.get_quote.return_value = None
    quote_id = uuid4()
    client = _client_with_service(stub)
    response = client.get(f"/api/v1/quotes/{quote_id}")
    assert response.status_code == 404
    assert response.json()["detail"] == "Quote not found"
    app.dependency_overrides.clear()


def test_create_quote_endpoint() -> None:
    stub = MagicMock()
    quote = _sample_quote()
    stub.create_quote.return_value = quote
    client = _client_with_service(stub)

    response = client.post(
        "/api/v1/quotes",
        json={
            "customer_id": str(quote.customer_id),
            "quote_number": "Q-0001",
            "status": "draft",
            "currency": "CAD",
            "notes": "Initial quote",
        },
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["quote_id"] == str(quote.quote_id)
    app.dependency_overrides.clear()


def test_patch_routing_step_endpoint() -> None:
    stub = MagicMock()
    step_id = uuid4()
    routing_id = uuid4()
    operation_id = uuid4()
    stub.update_routing_step.return_value = {
        "step_id": step_id,
        "routing_id": routing_id,
        "step_no": 1,
        "operation_id": operation_id,
        "machine_group_id": "CNC",
        "description": "Updated",
        "setup_time_min": "5.0",
        "cycle_time_min": "10.0",
        "handling_time_min": "2.0",
        "inspection_time_min": "1.0",
        "qty_basis": 1,
        "user_override": True,
        "estimator_note": None,
        "time_confidence": "0.8",
        "source": "user",
    }
    client = _client_with_service(stub)

    response = client.patch(
        f"/api/v1/routing_steps/{step_id}",
        json={"setup_time_min": "5.0", "source": "user", "user_override": True},
    )
    assert response.status_code == 200
    assert UUID(response.json()["step_id"]) == step_id
    app.dependency_overrides.clear()


def test_analyze_quote_upload_endpoint() -> None:
    stub = MagicMock()
    quote = _sample_quote()
    run_id = uuid4()
    stub.get_quote.return_value = quote
    stub.start_analysis_from_text.return_value = run_id
    client = _client_with_service(stub)

    with patch("app.api.v1.ventes_sous_traitance.router._extract_pdf_text_from_bytes", return_value="PDF text"):
        response = client.post(
            f"/api/v1/quotes/{quote.quote_id}/analyze-upload",
            files={"file": ("drawing.pdf", b"%PDF-1.4 dummy", "application/pdf")},
            data={
                "user_cue": "Prefer no welding",
                "part_cues_json": '[{"part_ref":"A","cue":"CNC only"}]',
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["job_id"] == str(run_id)
    assert payload["quote_id"] == str(quote.quote_id)
    stub.start_analysis_from_text.assert_called_once()
    called = stub.start_analysis_from_text.call_args
    assert called.kwargs["user_cue"] == "Prefer no welding"
    assert called.kwargs["part_cues"] == [{"part_ref": "A", "cue": "CNC only"}]
    app.dependency_overrides.clear()


def test_analyze_quote_upload_rejects_invalid_part_cues_json() -> None:
    stub = MagicMock()
    quote = _sample_quote()
    stub.get_quote.return_value = quote
    client = _client_with_service(stub)

    with patch("app.api.v1.ventes_sous_traitance.router._extract_pdf_text_from_bytes", return_value="PDF text"):
        response = client.post(
            f"/api/v1/quotes/{quote.quote_id}/analyze-upload",
            files={"file": ("drawing.pdf", b"%PDF-1.4 dummy", "application/pdf")},
            data={"part_cues_json": '{"part_ref":"A"}'},
        )

    assert response.status_code == 400
    assert "part_cues_json must be a JSON array" in response.json()["detail"]
    app.dependency_overrides.clear()

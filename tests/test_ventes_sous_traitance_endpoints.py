from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4
from unittest.mock import MagicMock
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.api.v1.ventes_sous_traitance.router import get_service
from app.domain.ventes_sous_traitance.models import CustomerSummary, MachineResponse, QuoteSummary


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
    quote_post = payload["paths"]["/api/v1/vente-sous-traitance/quotes"]["post"]
    assert "Ventes - Sous-Traitance" in quote_post["tags"]


def test_list_quotes_endpoint() -> None:
    stub = MagicMock()
    quote = _sample_quote()
    stub.list_quotes.return_value = [quote]
    client = _client_with_service(stub)
    response = client.get(f"/api/v1/vente-sous-traitance/quotes?status=draft&customer={quote.customer_id}")
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
    response = client.get("/api/v1/vente-sous-traitance/customers?q=gilbert&limit=50")
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["customer_id"] == str(customer.customer_id)
    assert payload[0]["name"] == customer.name
    stub.list_customers.assert_called_once_with(search="gilbert", limit=50)
    app.dependency_overrides.clear()


def test_create_customer_endpoint() -> None:
    stub = MagicMock()
    now = datetime.now(timezone.utc)
    customer_id = uuid4()
    stub.create_customer.return_value = {
        "customer_id": customer_id,
        "name": "New Customer",
        "email": "new@example.com",
        "phone": "555-1234",
        "created_at": now,
    }
    client = _client_with_service(stub)
    response = client.post(
        "/api/v1/vente-sous-traitance/customers",
        json={"name": "New Customer", "email": "new@example.com", "phone": "555-1234"},
    )
    assert response.status_code == 201
    assert response.json()["customer_id"] == str(customer_id)
    app.dependency_overrides.clear()


def test_update_customer_not_found() -> None:
    stub = MagicMock()
    customer_id = uuid4()
    stub.update_customer.return_value = None
    client = _client_with_service(stub)
    response = client.patch(f"/api/v1/vente-sous-traitance/customers/{customer_id}", json={"name": "Updated"})
    assert response.status_code == 404
    assert response.json()["detail"] == "Customer not found"
    app.dependency_overrides.clear()


def test_delete_customer_not_found() -> None:
    stub = MagicMock()
    customer_id = uuid4()
    stub.delete_customer.return_value = False
    client = _client_with_service(stub)
    response = client.delete(f"/api/v1/vente-sous-traitance/customers/{customer_id}")
    assert response.status_code == 404
    assert response.json()["detail"] == "Customer not found"
    app.dependency_overrides.clear()


def test_list_machine_groups_endpoint() -> None:
    stub = MagicMock()
    stub.list_machine_groups.return_value = [
        {
            "machine_group_id": "CNC_BORING_LARGE_4AX",
            "name": "CNC Boring Large 4-Axis",
            "process_families_json": '["milling"]',
            "config_json": None,
            "updated_at": datetime.now(timezone.utc),
        }
    ]
    client = _client_with_service(stub)
    response = client.get("/api/v1/vente-sous-traitance/machine-groups?q=boring&limit=25")
    assert response.status_code == 200
    payload = response.json()
    assert payload[0]["machine_group_id"] == "CNC_BORING_LARGE_4AX"
    stub.list_machine_groups.assert_called_once_with(search="boring", limit=25)
    app.dependency_overrides.clear()


def test_create_machine_group_endpoint() -> None:
    stub = MagicMock()
    stub.create_machine_group.return_value = {
        "machine_group_id": "CNC_NEW",
        "name": "CNC New",
        "process_families_json": '["milling"]',
        "config_json": None,
        "updated_at": datetime.now(timezone.utc),
    }
    client = _client_with_service(stub)
    response = client.post(
        "/api/v1/vente-sous-traitance/machine-groups",
        json={"machine_group_id": "CNC_NEW", "name": "CNC New", "process_families_json": '["milling"]'},
    )
    assert response.status_code == 201
    assert response.json()["machine_group_id"] == "CNC_NEW"
    app.dependency_overrides.clear()


def test_update_machine_group_not_found() -> None:
    stub = MagicMock()
    stub.update_machine_group.return_value = None
    client = _client_with_service(stub)
    response = client.patch("/api/v1/vente-sous-traitance/machine-groups/CNC_UNKNOWN", json={"name": "Unknown"})
    assert response.status_code == 404
    assert response.json()["detail"] == "Machine group not found"
    app.dependency_overrides.clear()


def test_delete_machine_group_not_found() -> None:
    stub = MagicMock()
    stub.delete_machine_group.return_value = False
    client = _client_with_service(stub)
    response = client.delete("/api/v1/vente-sous-traitance/machine-groups/CNC_UNKNOWN")
    assert response.status_code == 404
    assert response.json()["detail"] == "Machine group not found"
    app.dependency_overrides.clear()


def test_list_machine_capability_options_endpoint() -> None:
    stub = MagicMock()
    stub.list_machine_capability_options.return_value = [
        {
            "capability_code": "PROCESS_FAMILY",
            "capability_value": "milling",
            "unit": None,
            "usage_count": 8,
        }
    ]
    client = _client_with_service(stub)
    response = client.get("/api/v1/vente-sous-traitance/machine-capabilities/options?q=mill&capability_code=PROCESS_FAMILY&limit=30")
    assert response.status_code == 200
    payload = response.json()
    assert payload[0]["capability_code"] == "PROCESS_FAMILY"
    assert payload[0]["capability_value"] == "milling"
    stub.list_machine_capability_options.assert_called_once_with(
        search="mill",
        capability_code="PROCESS_FAMILY",
        limit=30,
    )
    app.dependency_overrides.clear()


def test_create_machine_capability_option_endpoint() -> None:
    stub = MagicMock()
    option_id = uuid4()
    now = datetime.now(timezone.utc)
    stub.create_machine_capability_option.return_value = {
        "option_id": option_id,
        "capability_code": "AXES",
        "capability_value": None,
        "unit": None,
        "is_active": True,
        "notes": None,
        "created_at": now,
        "updated_at": now,
    }
    client = _client_with_service(stub)
    response = client.post(
        "/api/v1/vente-sous-traitance/machine-capabilities/options",
        json={"capability_code": "AXES", "is_active": True},
    )
    assert response.status_code == 201
    assert response.json()["option_id"] == str(option_id)
    app.dependency_overrides.clear()


def test_update_machine_capability_option_not_found() -> None:
    stub = MagicMock()
    option_id = uuid4()
    stub.update_machine_capability_option.return_value = None
    client = _client_with_service(stub)
    response = client.patch(f"/api/v1/vente-sous-traitance/machine-capabilities/options/{option_id}", json={"is_active": False})
    assert response.status_code == 404
    assert response.json()["detail"] == "Machine capability option not found"
    app.dependency_overrides.clear()


def test_list_machine_capability_catalog_endpoint() -> None:
    stub = MagicMock()
    stub.list_machine_capability_catalog.return_value = [
        {
            "capability_code": "AXES",
            "recommended_input_type": "number",
            "suggested_unit": None,
            "usage_count": 12,
            "example_values": ["2", "4", "5"],
        }
    ]
    client = _client_with_service(stub)
    response = client.get("/api/v1/vente-sous-traitance/machine-capabilities/catalog?q=AX&limit=15")
    assert response.status_code == 200
    payload = response.json()
    assert payload[0]["capability_code"] == "AXES"
    assert payload[0]["recommended_input_type"] == "number"
    stub.list_machine_capability_catalog.assert_called_once_with(
        search="AX",
        limit=15,
    )
    app.dependency_overrides.clear()


def test_list_machines_endpoint() -> None:
    stub = MagicMock()
    now = datetime.now(timezone.utc)
    machine = MachineResponse(
        machine_id=uuid4(),
        machine_code="MC-01",
        machine_name="Machine 01",
        machine_group_id="CNC_BORING_LARGE_4AX",
        is_active=True,
        default_setup_time_min="120",
        default_runtime_min="45",
        envelope_x_mm="2000",
        envelope_y_mm="1200",
        envelope_z_mm="1000",
        max_part_weight_kg="3000",
        notes=None,
        created_at=now,
        updated_at=now,
        capabilities=[],
    )
    stub.list_machines.return_value = [machine]
    client = _client_with_service(stub)
    response = client.get("/api/v1/vente-sous-traitance/machines?q=mc&machine_group_id=CNC_BORING_LARGE_4AX&active_only=true&limit=10")
    assert response.status_code == 200
    payload = response.json()
    assert payload[0]["machine_code"] == "MC-01"
    stub.list_machines.assert_called_once_with(
        search="mc",
        machine_group_id="CNC_BORING_LARGE_4AX",
        active_only=True,
        limit=10,
    )
    app.dependency_overrides.clear()


def test_create_machine_endpoint() -> None:
    stub = MagicMock()
    now = datetime.now(timezone.utc)
    machine_id = uuid4()
    stub.create_machine.return_value = {
        "machine_id": machine_id,
        "machine_code": "MC-NEW",
        "machine_name": "Machine New",
        "machine_group_id": "CNC_BORING_LARGE_4AX",
        "is_active": True,
        "default_setup_time_min": "90",
        "default_runtime_min": "30",
        "envelope_x_mm": None,
        "envelope_y_mm": None,
        "envelope_z_mm": None,
        "max_part_weight_kg": None,
        "notes": None,
        "created_at": now,
        "updated_at": now,
        "capabilities": [],
    }
    client = _client_with_service(stub)
    response = client.post(
        "/api/v1/vente-sous-traitance/machines",
        json={
            "machine_code": "MC-NEW",
            "machine_name": "Machine New",
            "machine_group_id": "CNC_BORING_LARGE_4AX",
            "default_setup_time_min": "90",
            "default_runtime_min": "30",
            "capabilities": [],
        },
    )
    assert response.status_code == 201
    assert response.json()["machine_id"] == str(machine_id)
    app.dependency_overrides.clear()


def test_update_machine_not_found() -> None:
    stub = MagicMock()
    machine_id = uuid4()
    stub.update_machine.return_value = None
    client = _client_with_service(stub)
    response = client.patch(f"/api/v1/vente-sous-traitance/machines/{machine_id}", json={"default_runtime_min": "55"})
    assert response.status_code == 404
    assert response.json()["detail"] == "Machine not found"
    app.dependency_overrides.clear()


def test_delete_machine_not_found() -> None:
    stub = MagicMock()
    machine_id = uuid4()
    stub.delete_machine.return_value = False
    client = _client_with_service(stub)
    response = client.delete(f"/api/v1/vente-sous-traitance/machines/{machine_id}")
    assert response.status_code == 404
    assert response.json()["detail"] == "Machine not found"
    app.dependency_overrides.clear()


def test_get_quote_not_found() -> None:
    stub = MagicMock()
    stub.get_quote.return_value = None
    quote_id = uuid4()
    client = _client_with_service(stub)
    response = client.get(f"/api/v1/vente-sous-traitance/quotes/{quote_id}")
    assert response.status_code == 404
    assert response.json()["detail"] == "Quote not found"
    app.dependency_overrides.clear()


def test_create_quote_endpoint() -> None:
    stub = MagicMock()
    quote = _sample_quote()
    stub.create_quote.return_value = quote
    client = _client_with_service(stub)

    response = client.post(
        "/api/v1/vente-sous-traitance/quotes",
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
        f"/api/v1/vente-sous-traitance/routing_steps/{step_id}",
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
            f"/api/v1/vente-sous-traitance/quotes/{quote.quote_id}/analyze-upload",
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
            f"/api/v1/vente-sous-traitance/quotes/{quote.quote_id}/analyze-upload",
            files={"file": ("drawing.pdf", b"%PDF-1.4 dummy", "application/pdf")},
            data={"part_cues_json": '{"part_ref":"A"}'},
        )

    assert response.status_code == 400
    assert "part_cues_json must be a JSON array" in response.json()["detail"]
    app.dependency_overrides.clear()

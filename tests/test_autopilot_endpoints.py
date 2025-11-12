"""
Fastems1 Autopilot endpoint smoke tests.
"""

from __future__ import annotations

from typing import Any, Dict, Tuple

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.settings import settings
from app.api.v1.usinage.fastems1.autopilot import router as autopilot_router
from app.domain.usinage.fastems1.autopilot.models import (
    ActionPlan,
    ActionPlanStep,
    PlanCandidate,
    ScoreBreakdown,
    SuggestionResult,
)
from app.domain.usinage.fastems1.autopilot.repositories import PlannedJobRow


client = TestClient(app)


class StubRepository:
    def __init__(self) -> None:
        self._planned_job = PlannedJobRow(
            planned_job_id=1,
            plan_batch_id="batch-123",
            machine_id="DMC1",
            sequence_index=1,
            work_order="WO-001",
            part_id="PART-01",
            operation_id="OP-10",
            machine_pallet_id="PAL-1",
            material_pallet_id=None,
            estimated_setup_minutes=12.0,
            estimated_cycle_minutes=25.0,
            status="planned",
        )
        self.refused = False

    def get_planned_job(self, planned_job_id: int) -> PlannedJobRow | None:
        if planned_job_id == self._planned_job.planned_job_id:
            return self._planned_job
        return None

    def list_machine_status(self) -> Dict[str, Dict[str, Any]]:
        return {"DMC1": {"MachineId": "DMC1", "IsAvailable": 1, "Status": "available"}}


class StubPlanner:
    async def refresh_plan(self, jobs_per_machine=None, machine_ids=None) -> Dict[str, Any]:
        return {"plan_batch_id": "batch-123", "machines": ["DMC1"], "planned_jobs": 2}


class StubSuggestion:
    def __init__(self) -> None:
        self.result = SuggestionResult(
            decision_id=42,
            machine_id="DMC1",
            work_order="WO-001",
            part_id="PART-01",
            operation_id="OP-10",
            machine_pallet_id="PAL-1",
            material_pallet_id="MAT-2",
            estimated_setup_minutes=12.0,
            estimated_cycle_minutes=25.0,
            score=ScoreBreakdown(total=15.0, tool_penalty=1.0, setup_penalty=8.0, material_penalty=2.0, balance_penalty=4.0),
            action_plan=ActionPlan(
                steps=[
                    ActionPlanStep(step_type="UNLOAD_PALLET", description="Unload finished part"),
                    ActionPlanStep(step_type="LOAD_RAW_MATERIAL", description="Load WO-001 material"),
                ],
                fixture_hardware_list=[{"item": "FixtureA", "location": "RackA"}],
            ),
            alternatives=[
                PlanCandidate(
                    work_order="WO-002",
                    part_id="PART-02",
                    operation_id="OP-20",
                    machine_id="DMC2",
                    machine_pallet_id=None,
                    material_pallet_id=None,
                    estimated_setup_minutes=20.0,
                    estimated_cycle_minutes=30.0,
                    sequence_index=1,
                )
            ],
        )

    async def next_suggestion(self, max_alternatives: int = 0, details: bool = False) -> SuggestionResult:
        return self.result


class StubControlService:
    def __init__(self, repo: StubRepository) -> None:
        self.repo = repo
        self.machine_updates: Dict[str, Dict[str, Any]] = {}
        self.started_setup_id = 99

    def refuse_job(self, planned_job: PlannedJobRow, decision_id: int | None, reason: str | None) -> None:
        self.repo.refused = True

    def set_machine_status(self, machine_id: str, is_available: bool, status_text: str, reason: str | None) -> Dict[str, Dict[str, Any]]:
        self.machine_updates[machine_id] = {
            "MachineId": machine_id,
            "IsAvailable": 1 if is_available else 0,
            "Status": status_text,
            "Reason": reason,
        }
        return self.machine_updates

    def start_setup_session(
        self,
        machine_id: str,
        machine_pallet_id: str | None,
        work_order: str | None,
        part_id: str | None,
        operation_id: str | None,
        setup_type: str | None,
        decision_id: int | None,
    ) -> int:
        return self.started_setup_id

    def end_setup_session(self, setup_id: int) -> bool:
        return setup_id == self.started_setup_id


@pytest.fixture(name="autopilot_overrides")
def autopilot_overrides_fixture():
    settings.fastems1_autopilot_enabled = True
    repo = StubRepository()
    planner = StubPlanner()
    suggestion = StubSuggestion()
    control = StubControlService(repo)

    overrides = {
        autopilot_router.get_repository: lambda: repo,
        autopilot_router.get_planner_service: lambda: planner,
        autopilot_router.get_suggestion_service: lambda: suggestion,
        autopilot_router.get_control_service: lambda: control,
    }

    previous: Dict[Any, Any] = {}
    for dependency, override in overrides.items():
        previous[dependency] = app.dependency_overrides.get(dependency)
        app.dependency_overrides[dependency] = override

    try:
        yield repo, control, suggestion
    finally:
        for dependency, prior in previous.items():
            if prior is None:
                app.dependency_overrides.pop(dependency, None)
            else:
                app.dependency_overrides[dependency] = prior


def test_plan_refresh_returns_summary(autopilot_overrides):
    response = client.post("/api/v1/usinage/fastems1/autopilot/plan/refresh")
    assert response.status_code == 200
    payload = response.json()
    assert payload["plan_batch_id"] == "batch-123"
    assert payload["machines"] == ["DMC1"]
    assert payload["planned_jobs"] == 2


def test_next_suggestion_returns_payload(autopilot_overrides):
    response = client.post(
        "/api/v1/usinage/fastems1/autopilot/next",
        json={"max_alternatives": 1},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["decision_id"] == 42
    assert payload["machine_id"] == "DMC1"
    assert payload["action_plan"]["steps"][0]["step_type"] == "UNLOAD_PALLET"
    assert payload["alternatives"][0]["machine_id"] == "DMC2"


def test_refuse_endpoint_marks_job(autopilot_overrides):
    repo, _, _ = autopilot_overrides
    response = client.post(
        "/api/v1/usinage/fastems1/autopilot/refuse",
        json={"planned_job_id": 1, "reason": "Fixture busy"},
    )
    assert response.status_code == 200
    assert repo.refused is True


def test_machine_status_endpoint_updates_state(autopilot_overrides):
    response = client.post(
        "/api/v1/usinage/fastems1/autopilot/machine/status",
        json={"machine_id": "DMC1", "is_available": False, "status": "maintenance", "reason": "Inspection"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["DMC1"]["Status"] == "maintenance"
    assert payload["DMC1"]["IsAvailable"] == 0


def test_setup_session_endpoints(autopilot_overrides):
    start_resp = client.post(
        "/api/v1/usinage/fastems1/autopilot/fixture/setup/start",
        json={"machine_id": "DMC1"},
    )
    assert start_resp.status_code == 200
    setup_id = start_resp.json()["setup_id"]
    end_resp = client.post(f"/api/v1/usinage/fastems1/autopilot/fixture/setup/end/{setup_id}")
    assert end_resp.status_code == 200
    assert end_resp.json()["completed"] is True

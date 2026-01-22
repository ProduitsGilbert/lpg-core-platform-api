"""
Fastems1 Autopilot API router.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from functools import lru_cache

from app.api.v1.usinage.fastems1.autopilot.schemas import (
    NextRequest,
    PlanRefreshResponse,
    RefuseRequest,
    SetupEndResponse,
    SetupStartRequest,
    SetupStartResponse,
    SuggestionResponse,
    MachineStatusRequest,
)
from app.api.v1.usinage.fastems1.autopilot.schemas import ActionPlanModel, ActionPlanStepModel
from app.deps import get_autopilot_db
from app.domain.usinage.fastems1.autopilot.providers import (
    FixtureProvider,
    MaterialProvider,
    PalletRouteProvider,
    ToolingProvider,
    WorkOrderProvider,
)
from app.domain.usinage.fastems1.autopilot.repositories import AutopilotRepository
from app.domain.usinage.fastems1.autopilot.services import (
    AutopilotControlService,
    AutopilotPlannerService,
    AutopilotSuggestionService,
)
from app.settings import settings

router = APIRouter(prefix="/autopilot", tags=["Fastems1 Autopilot"])

def ensure_enabled() -> None:
    if not settings.fastems1_autopilot_enabled:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Fastems1 Autopilot is disabled")


@lru_cache(maxsize=1)
def _get_providers() -> tuple[WorkOrderProvider, FixtureProvider, ToolingProvider, MaterialProvider, PalletRouteProvider]:
    """
    Lazily build provider singletons.

    Important: Some providers may require optional DB drivers (e.g., ODBC). By deferring
    instantiation, we avoid import-time failures in environments where those drivers are absent,
    and we only initialize providers when the Autopilot feature is enabled.
    """
    return (
        WorkOrderProvider(),
        FixtureProvider(),
        ToolingProvider(),
        MaterialProvider(),
        PalletRouteProvider(),
    )


def get_workorder_provider(_: None = Depends(ensure_enabled)) -> WorkOrderProvider:
    return _get_providers()[0]


def get_fixture_provider(_: None = Depends(ensure_enabled)) -> FixtureProvider:
    return _get_providers()[1]


def get_tooling_provider(_: None = Depends(ensure_enabled)) -> ToolingProvider:
    return _get_providers()[2]


def get_material_provider(_: None = Depends(ensure_enabled)) -> MaterialProvider:
    return _get_providers()[3]


def get_pallet_route_provider(_: None = Depends(ensure_enabled)) -> PalletRouteProvider:
    return _get_providers()[4]


def get_repository(db: Session = Depends(get_autopilot_db)) -> AutopilotRepository:
    return AutopilotRepository(db)


def get_planner_service(
    repo: AutopilotRepository = Depends(get_repository),
    workorder_provider: WorkOrderProvider = Depends(get_workorder_provider),
    fixture_provider: FixtureProvider = Depends(get_fixture_provider),
    tooling_provider: ToolingProvider = Depends(get_tooling_provider),
    material_provider: MaterialProvider = Depends(get_material_provider),
    pallet_route_provider: PalletRouteProvider = Depends(get_pallet_route_provider),
) -> AutopilotPlannerService:
    return AutopilotPlannerService(
        repo,
        workorder_provider,
        fixture_provider,
        tooling_provider,
        material_provider,
        pallet_route_provider,
    )


def get_suggestion_service(
    repo: AutopilotRepository = Depends(get_repository),
    fixture_provider: FixtureProvider = Depends(get_fixture_provider),
    tooling_provider: ToolingProvider = Depends(get_tooling_provider),
    pallet_route_provider: PalletRouteProvider = Depends(get_pallet_route_provider),
    workorder_provider: WorkOrderProvider = Depends(get_workorder_provider),
) -> AutopilotSuggestionService:
    return AutopilotSuggestionService(
        repo,
        fixture_provider,
        tooling_provider,
        pallet_route_provider,
        workorder_provider,
    )


def get_control_service(repo: AutopilotRepository = Depends(get_repository)) -> AutopilotControlService:
    return AutopilotControlService(repo)


@router.post("/plan/refresh", response_model=PlanRefreshResponse, summary="Rebuild short-horizon plan")
async def refresh_plan(
    _: None = Depends(ensure_enabled),
    planner: AutopilotPlannerService = Depends(get_planner_service),
) -> PlanRefreshResponse:
    summary = await planner.refresh_plan()
    return PlanRefreshResponse(**summary)


@router.post("/next", response_model=SuggestionResponse, summary="Return the best next job suggestion")
async def next_suggestion(
    payload: NextRequest,
    _: None = Depends(ensure_enabled),
    suggestion_service: AutopilotSuggestionService = Depends(get_suggestion_service),
) -> SuggestionResponse:
    result = await suggestion_service.next_suggestion(payload.max_alternatives, payload.details)
    action_plan = ActionPlanModel(
        steps=[ActionPlanStepModel(**asdict(step)) for step in result.action_plan.steps],
        fixture_hardware_list=result.action_plan.fixture_hardware_list,
    )
    return SuggestionResponse(
        decision_id=result.decision_id,
        machine_id=result.machine_id,
        work_order=result.work_order,
        part_id=result.part_id,
        operation_id=result.operation_id,
        machine_pallet_id=result.machine_pallet_id,
        material_pallet_id=result.material_pallet_id,
        estimated_setup_minutes=result.estimated_setup_minutes,
        estimated_cycle_minutes=result.estimated_cycle_minutes,
        score_total=result.score.total,
        score_breakdown={
            "tool": result.score.tool_penalty,
            "setup": result.score.setup_penalty,
            "material": result.score.material_penalty,
            "balance": result.score.balance_penalty,
        },
        action_plan=action_plan,
        alternatives=[
            {
                "machine_id": alt.machine_id,
                "work_order": alt.work_order,
                "part_id": alt.part_id,
                "operation_id": alt.operation_id,
                "estimated_setup_minutes": alt.estimated_setup_minutes,
                "estimated_cycle_minutes": alt.estimated_cycle_minutes,
                "score_total": alt.score.total if alt.score else None,
            }
            for alt in result.alternatives
        ],
        details=result.details,
    )


@router.post("/refuse", summary="Operator refusal and ignore")
async def refuse_job(
    payload: RefuseRequest,
    _: None = Depends(ensure_enabled),
    repo: AutopilotRepository = Depends(get_repository),
    control_service: AutopilotControlService = Depends(get_control_service),
) -> Dict[str, str]:
    job = repo.get_planned_job(payload.planned_job_id)
    if not job:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Planned job not found")
    control_service.refuse_job(job, payload.decision_id, payload.reason)
    return {"status": "ignored"}


@router.post("/machine/status", summary="Set machine availability")
async def set_machine_status(
    payload: MachineStatusRequest,
    _: None = Depends(ensure_enabled),
    control_service: AutopilotControlService = Depends(get_control_service),
) -> Dict[str, dict]:
    return control_service.set_machine_status(
        machine_id=payload.machine_id,
        is_available=payload.is_available,
        status_text=payload.status,
        reason=payload.reason,
    )


@router.post("/fixture/setup/start", response_model=SetupStartResponse, summary="Start a setup session")
async def setup_start(
    payload: SetupStartRequest,
    _: None = Depends(ensure_enabled),
    control_service: AutopilotControlService = Depends(get_control_service),
) -> SetupStartResponse:
    setup_id = control_service.start_setup_session(
        machine_id=payload.machine_id,
        machine_pallet_id=payload.machine_pallet_id,
        work_order=payload.work_order,
        part_id=payload.part_id,
        operation_id=payload.operation_id,
        setup_type=payload.setup_type,
        decision_id=payload.decision_id,
    )
    return SetupStartResponse(setup_id=setup_id)


@router.post("/fixture/setup/end/{setup_id}", response_model=SetupEndResponse, summary="End a setup session")
async def setup_end(
    setup_id: int,
    _: None = Depends(ensure_enabled),
    control_service: AutopilotControlService = Depends(get_control_service),
) -> SetupEndResponse:
    completed = control_service.end_setup_session(setup_id)
    return SetupEndResponse(setup_id=setup_id, completed=completed)

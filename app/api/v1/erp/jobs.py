"""ERP Jobs endpoints (Jobs, JobTaskLines, JobPlanningLines)."""

from __future__ import annotations

from datetime import date
import logging
from typing import Any, Dict, List, Optional

import httpx
import logfire
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.domain.erp.business_central_data_service import BusinessCentralODataService
from app.domain.erp.models import BusinessCentralRecordCreate, BusinessCentralRecordUpdate

logger = logging.getLogger(__name__)

router = APIRouter(tags=["ERP - Jobs"])


def get_odata_service() -> BusinessCentralODataService:
    """FastAPI dependency for the Business Central OData service."""
    return BusinessCentralODataService()


def _odata_literal(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, (int, float)):
        return str(value)
    sanitized = str(value).replace("'", "''")
    return f"'{sanitized}'"


def _build_filter(filters: Dict[str, Any]) -> Optional[str]:
    parts = []
    for field, value in filters.items():
        if value is None:
            continue
        parts.append(f"{field} eq {_odata_literal(value)}")
    if not parts:
        return None
    return " and ".join(parts)


def _build_resource(resource: str, *, filters: Optional[Dict[str, Any]] = None, top: Optional[int] = None) -> str:
    query_parts: List[str] = []
    if filters:
        filter_expr = _build_filter(filters)
        if filter_expr:
            query_parts.append(f"$filter={filter_expr}")
    if top is not None:
        query_parts.append(f"$top={int(top)}")
    if not query_parts:
        return resource
    return f"{resource}?{'&'.join(query_parts)}"


def _raise_bc_http_error(resource: str, exc: httpx.HTTPStatusError) -> None:
    status_code = exc.response.status_code if exc.response else status.HTTP_502_BAD_GATEWAY
    if status_code == 404:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "BC_NOT_FOUND",
                    "message": "Business Central record not found",
                    "resource": resource,
                }
            },
        ) from exc
    if status_code == 409:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": {
                    "code": "BC_CONFLICT",
                    "message": "Business Central conflict while updating",
                    "resource": resource,
                }
            },
        ) from exc
    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail={
            "error": {
                "code": "BC_UPSTREAM_ERROR",
                "message": "Business Central request failed",
                "upstream_status": status_code,
                "resource": resource,
            }
        },
    ) from exc


def _raise_bc_request_error(resource: str, exc: httpx.RequestError) -> None:
    logger.error(
        "Business Central request failed",
        extra={"resource": resource, "error": str(exc)},
    )
    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail={
            "error": {
                "code": "BC_UPSTREAM_UNAVAILABLE",
                "message": "Business Central service unreachable",
                "resource": resource,
            }
        },
    ) from exc


@router.get(
    "/jobs",
    response_model=List[Dict[str, Any]],
    summary="List jobs",
    description="Retrieve Business Central jobs with optional filtering by job number (No).",
)
async def list_jobs(
    no: Optional[str] = Query(default=None, description="Filter by job number (No)."),
    status_filter: Optional[str] = Query(
        default="Open",
        alias="status",
        description="Filter by job status (e.g., Open). Defaults to Open.",
    ),
    top: Optional[int] = Query(default=None, ge=1, le=500, description="Limit the number of records returned."),
    service: BusinessCentralODataService = Depends(get_odata_service),
) -> List[Dict[str, Any]]:
    resource = _build_resource("Jobs", filters={"No": no, "Status": status_filter}, top=top)
    with logfire.span("bc_jobs.list_jobs", job_no=no, status=status_filter, top=top):
        try:
            return await service.fetch_collection(resource)
        except httpx.HTTPStatusError as exc:
            _raise_bc_http_error("Jobs", exc)
        except httpx.RequestError as exc:
            _raise_bc_request_error("Jobs", exc)
    return []


@router.get(
    "/jobs/default-dimensions",
    response_model=List[Dict[str, Any]],
    summary="List job default dimensions",
    description=(
        "Retrieve Business Central DefaultDimensions rows for a job number (No). "
        "Useful for resolving DIVISION and REGION."
    ),
)
async def list_job_default_dimensions(
    job_no: str = Query(..., min_length=1, description="Job number (No)."),
    dimension_code: Optional[str] = Query(
        default=None,
        description="Optional dimension code filter (e.g., DIVISION, REGION).",
    ),
    top: Optional[int] = Query(default=None, ge=1, le=500, description="Limit the number of records returned."),
    service: BusinessCentralODataService = Depends(get_odata_service),
) -> List[Dict[str, Any]]:
    resource = _build_resource(
        "DefaultDimensions",
        filters={"No": job_no, "Dimension_Code": dimension_code},
        top=top,
    )
    with logfire.span(
        "bc_jobs.list_job_default_dimensions",
        job_no=job_no,
        dimension_code=dimension_code,
        top=top,
    ):
        try:
            return await service.fetch_collection(resource)
        except httpx.HTTPStatusError as exc:
            _raise_bc_http_error("DefaultDimensions", exc)
        except httpx.RequestError as exc:
            _raise_bc_request_error("DefaultDimensions", exc)
    return []


@router.post(
    "/jobs",
    response_model=Dict[str, Any],
    summary="Create job",
    description="Create a new job in Business Central (Jobs).",
)
async def create_job(
    payload: BusinessCentralRecordCreate,
    service: BusinessCentralODataService = Depends(get_odata_service),
) -> Dict[str, Any]:
    if not payload.data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "BC_EMPTY_PAYLOAD",
                    "message": "Create payload is empty",
                }
            },
        )
    with logfire.span("bc_jobs.create_job", fields=list(payload.data.keys())):
        try:
            return await service.create_record("Jobs", payload.data)
        except httpx.HTTPStatusError as exc:
            _raise_bc_http_error("Jobs", exc)
        except httpx.RequestError as exc:
            _raise_bc_request_error("Jobs", exc)
    return {}


@router.patch(
    "/jobs/{system_id}",
    response_model=Dict[str, Any],
    summary="Update job",
    description="Update an existing job in Business Central by SystemId.",
)
async def update_job(
    system_id: str,
    payload: BusinessCentralRecordUpdate,
    service: BusinessCentralODataService = Depends(get_odata_service),
) -> Dict[str, Any]:
    if not payload.data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "BC_EMPTY_PAYLOAD",
                    "message": "Update payload is empty",
                }
            },
        )
    with logfire.span("bc_jobs.update_job", system_id=system_id, fields=list(payload.data.keys())):
        try:
            return await service.update_record("Jobs", system_id, payload.data, etag=payload.etag)
        except httpx.HTTPStatusError as exc:
            _raise_bc_http_error("Jobs", exc)
        except httpx.RequestError as exc:
            _raise_bc_request_error("Jobs", exc)
    return {}


@router.get(
    "/job-task-lines",
    response_model=List[Dict[str, Any]],
    summary="List job task lines",
    description="Retrieve Business Central job task lines with optional filtering by job number and task number.",
)
async def list_job_task_lines(
    job_no: Optional[str] = Query(default=None, description="Filter by job number (Job_No)."),
    job_task_no: Optional[str] = Query(default=None, description="Filter by job task number (Job_Task_No)."),
    top: Optional[int] = Query(default=None, ge=1, le=500, description="Limit the number of records returned."),
    service: BusinessCentralODataService = Depends(get_odata_service),
) -> List[Dict[str, Any]]:
    resource = _build_resource(
        "JobTaskLines",
        filters={"Job_No": job_no, "Job_Task_No": job_task_no},
        top=top,
    )
    with logfire.span("bc_jobs.list_job_task_lines", job_no=job_no, job_task_no=job_task_no, top=top):
        try:
            return await service.fetch_collection(resource)
        except httpx.HTTPStatusError as exc:
            _raise_bc_http_error("JobTaskLines", exc)
        except httpx.RequestError as exc:
            _raise_bc_request_error("JobTaskLines", exc)
    return []


@router.post(
    "/job-task-lines",
    response_model=Dict[str, Any],
    summary="Create job task line",
    description="Create a new job task line in Business Central (JobTaskLines).",
)
async def create_job_task_line(
    payload: BusinessCentralRecordCreate,
    service: BusinessCentralODataService = Depends(get_odata_service),
) -> Dict[str, Any]:
    if not payload.data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "BC_EMPTY_PAYLOAD",
                    "message": "Create payload is empty",
                }
            },
        )
    with logfire.span("bc_jobs.create_job_task_line", fields=list(payload.data.keys())):
        try:
            return await service.create_record("JobTaskLines", payload.data)
        except httpx.HTTPStatusError as exc:
            _raise_bc_http_error("JobTaskLines", exc)
        except httpx.RequestError as exc:
            _raise_bc_request_error("JobTaskLines", exc)
    return {}


@router.patch(
    "/job-task-lines/{system_id}",
    response_model=Dict[str, Any],
    summary="Update job task line",
    description="Update an existing job task line in Business Central by SystemId.",
)
async def update_job_task_line(
    system_id: str,
    payload: BusinessCentralRecordUpdate,
    service: BusinessCentralODataService = Depends(get_odata_service),
) -> Dict[str, Any]:
    if not payload.data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "BC_EMPTY_PAYLOAD",
                    "message": "Update payload is empty",
                }
            },
        )
    with logfire.span(
        "bc_jobs.update_job_task_line",
        system_id=system_id,
        fields=list(payload.data.keys()),
    ):
        try:
            return await service.update_record("JobTaskLines", system_id, payload.data, etag=payload.etag)
        except httpx.HTTPStatusError as exc:
            _raise_bc_http_error("JobTaskLines", exc)
        except httpx.RequestError as exc:
            _raise_bc_request_error("JobTaskLines", exc)
    return {}


@router.get(
    "/job-planning-lines",
    response_model=List[Dict[str, Any]],
    summary="List job planning lines",
    description="Retrieve Business Central job planning lines with optional filtering by job and task numbers.",
)
async def list_job_planning_lines(
    job_no: Optional[str] = Query(default=None, description="Filter by job number (Job_No)."),
    job_task_no: Optional[str] = Query(default=None, description="Filter by job task number (Job_Task_No)."),
    line_no: Optional[int] = Query(default=None, description="Filter by line number (Line_No)."),
    top: Optional[int] = Query(default=None, ge=1, le=500, description="Limit the number of records returned."),
    service: BusinessCentralODataService = Depends(get_odata_service),
) -> List[Dict[str, Any]]:
    resource = _build_resource(
        "JobPlanningLines",
        filters={"Job_No": job_no, "Job_Task_No": job_task_no, "Line_No": line_no},
        top=top,
    )
    with logfire.span(
        "bc_jobs.list_job_planning_lines",
        job_no=job_no,
        job_task_no=job_task_no,
        line_no=line_no,
        top=top,
    ):
        try:
            return await service.fetch_collection(resource)
        except httpx.HTTPStatusError as exc:
            _raise_bc_http_error("JobPlanningLines", exc)
        except httpx.RequestError as exc:
            _raise_bc_request_error("JobPlanningLines", exc)
    return []


@router.post(
    "/job-planning-lines",
    response_model=Dict[str, Any],
    summary="Create job planning line",
    description="Create a new job planning line in Business Central (JobPlanningLines).",
)
async def create_job_planning_line(
    payload: BusinessCentralRecordCreate,
    service: BusinessCentralODataService = Depends(get_odata_service),
) -> Dict[str, Any]:
    if not payload.data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "BC_EMPTY_PAYLOAD",
                    "message": "Create payload is empty",
                }
            },
        )
    with logfire.span("bc_jobs.create_job_planning_line", fields=list(payload.data.keys())):
        try:
            return await service.create_record("JobPlanningLines", payload.data)
        except httpx.HTTPStatusError as exc:
            _raise_bc_http_error("JobPlanningLines", exc)
        except httpx.RequestError as exc:
            _raise_bc_request_error("JobPlanningLines", exc)
    return {}


@router.patch(
    "/job-planning-lines/{system_id}",
    response_model=Dict[str, Any],
    summary="Update job planning line",
    description="Update an existing job planning line in Business Central by SystemId.",
)
async def update_job_planning_line(
    system_id: str,
    payload: BusinessCentralRecordUpdate,
    service: BusinessCentralODataService = Depends(get_odata_service),
) -> Dict[str, Any]:
    if not payload.data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "BC_EMPTY_PAYLOAD",
                    "message": "Update payload is empty",
                }
            },
        )
    with logfire.span(
        "bc_jobs.update_job_planning_line",
        system_id=system_id,
        fields=list(payload.data.keys()),
    ):
        try:
            return await service.update_record("JobPlanningLines", system_id, payload.data, etag=payload.etag)
        except httpx.HTTPStatusError as exc:
            _raise_bc_http_error("JobPlanningLines", exc)
        except httpx.RequestError as exc:
            _raise_bc_request_error("JobPlanningLines", exc)
    return {}

"""ClickUp tasks endpoints."""

from __future__ import annotations

import logging
from typing import Optional

import logfire
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.v1.models import CollectionResponse, ErrorResponse, SingleResponse
from app.deps import get_db
from app.domain.clickup.service import ClickUpService
from app.domain.clickup.models import ClickUpTaskResponse, ClickUpTasksResponse
from app.errors import BaseAPIException

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tasks", tags=["ClickUp - Tasks"])

clickup_service = ClickUpService()


@router.get(
    "/sav-rabotage",
    response_model=CollectionResponse[ClickUpTaskResponse],
    responses={
        200: {"description": "Tasks retrieved successfully"},
        400: {"description": "Invalid request parameters", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
    summary="List SAV/Rabotage tasks",
    description="""
    Retrieve tasks from the SAV (Service Après Vente) / Rabotage folder.

    - If customer_id is provided, only tasks for that specific customer will be returned
    - If no customer_id is provided, all tasks will be returned
    - Tasks include status, start date, due date, description, and other relevant information
    """,
)
async def list_sav_rabotage_tasks(
    customer_id: Optional[str] = Query(
        None,
        description="Customer ID to filter tasks (optional). If not provided, all tasks are returned.",
        example="CUST123"
    ),
    include_closed: bool = Query(
        False,
        description="Whether to include closed/completed tasks",
        example=False
    ),
    page: Optional[int] = Query(
        None,
        description="Page number for pagination (optional)",
        ge=1,
        example=1
    ),
    db: Session = Depends(get_db),
) -> CollectionResponse[ClickUpTaskResponse]:
    """List tasks from SAV/Rabotage folder with optional customer filtering."""
    try:
        with logfire.span(
            "list_sav_rabotage_tasks",
            customer_id=customer_id,
            include_closed=include_closed,
            page=page
        ):
            result = await clickup_service.get_sav_rabotage_tasks(
                customer_id=customer_id,
                include_closed=include_closed,
                page=page
            )

        return CollectionResponse(data=result.tasks)
    except HTTPException:
        raise
    except BaseAPIException:
        # Let BaseAPIException bubble up to global handler
        raise
    except Exception as exc:
        logger.error("Error retrieving SAV/Rabotage tasks: %s", exc)
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "Failed to retrieve ClickUp tasks",
                    "trace_id": getattr(db, "trace_id", "unknown"),
                }
            },
        )


@router.get(
    "/space/{space_id}/customer/{customer_id}",
    response_model=CollectionResponse[ClickUpTaskResponse],
    responses={
        200: {"description": "Tasks retrieved successfully"},
        400: {"description": "Invalid request parameters", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
    summary="List tasks for a customer in a space",
    description="""
    Retrieve tasks from a specific ClickUp space filtered by customer ID.

    - Includes tasks from all lists within the space (folder and folderless lists)
    - Includes closed/completed tasks by default
    - Supports pagination with `page` parameter (per ClickUp list pagination)
    """,
)
async def list_tasks_for_customer_in_space(
    space_id: str,
    customer_id: str,
    include_closed: bool = Query(
        True,
        description="Whether to include closed/completed tasks",
        example=True
    ),
    page: Optional[int] = Query(
        None,
        description="Page number for pagination (optional)",
        ge=1,
        example=1
    ),
    db: Session = Depends(get_db),
) -> CollectionResponse[ClickUpTaskResponse]:
    """List tasks for a specific customer in a space."""
    try:
        with logfire.span(
            "list_tasks_for_customer_in_space",
            space_id=space_id,
            customer_id=customer_id,
            include_closed=include_closed,
            page=page
        ):
            result = await clickup_service.get_tasks_for_customer_in_space(
                space_id=space_id,
                customer_id=customer_id,
                include_closed=include_closed,
                page=page
            )

        return CollectionResponse(data=result.tasks)
    except HTTPException:
        raise
    except BaseAPIException:
        raise
    except Exception as exc:
        logger.error("Error retrieving tasks for customer %s in space %s: %s", customer_id, space_id, exc)
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "Failed to retrieve ClickUp tasks",
                    "trace_id": getattr(db, "trace_id", "unknown"),
                }
            },
        )

@router.get(
    "/sav-rabotage/{task_id}",
    response_model=SingleResponse[ClickUpTaskResponse],
    responses={
        200: {"description": "Task retrieved successfully"},
        404: {"description": "Task not found", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
    summary="Get task by ID",
    description="Retrieve a specific task from ClickUp by its ID.",
)
async def get_task_by_id(
    task_id: str,
    db: Session = Depends(get_db),
) -> SingleResponse[ClickUpTaskResponse]:
    """Get a specific ClickUp task by ID."""
    try:
        with logfire.span("get_task_by_id", task_id=task_id):
            task = await clickup_service.get_task_by_id(task_id)

        if not task:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": {
                        "code": "TASK_NOT_FOUND",
                        "message": f"Task '{task_id}' not found",
                        "trace_id": getattr(db, "trace_id", "unknown"),
                    }
                },
            )

        return SingleResponse(data=task)
    except HTTPException:
        raise
    except BaseAPIException:
        # Let BaseAPIException bubble up to global handler
        raise
    except Exception as exc:
        logger.error("Error retrieving task %s: %s", task_id, exc)
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "Failed to retrieve ClickUp task",
                    "trace_id": getattr(db, "trace_id", "unknown"),
                }
            },
        )



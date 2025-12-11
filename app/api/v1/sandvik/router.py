"""
Sandvik API router.

This module provides FastAPI endpoints for accessing Sandvik Machining Insights data.
"""

from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from app.api.v1.sandvik.schemas import (
    MachineHistoryRequest,
    LiveMetricsRequest,
    TimeseriesRequest,
    MachineHistoryResponse,
    LiveMetricsResponse,
    TimeseriesResponse,
    MachineConfig
)
from app.domain.sandvik.config import get_machine_config, get_machine_group_names
from app.domain.sandvik.service import SandvikService
from app.settings import settings

router = APIRouter(prefix="", tags=["Sandvik Machining Insights"])


def ensure_enabled() -> None:
    """Ensure Sandvik API integration is enabled."""
    if not settings.sandvik_api_enabled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sandvik API integration is disabled"
        )


def get_sandvik_service() -> SandvikService:
    """Get Sandvik service instance."""
    return SandvikService()


@router.get("/machines", response_model=MachineConfig, summary="Get machine configuration")
async def get_machines(
    _: None = Depends(ensure_enabled)
) -> MachineConfig:
    """
    Get available machine configuration.

    Returns the complete machine configuration including all groups and devices.
    """
    return get_machine_config()


@router.get("/machine-groups", summary="Get available machine group names")
async def get_machine_groups(
    _: None = Depends(ensure_enabled)
) -> JSONResponse:
    """
    Get list of available machine group names.

    Returns a simple list of machine group names that can be used in other endpoints.
    """
    groups = get_machine_group_names()
    return JSONResponse(content={"groups": groups})


@router.post("/timeseries", response_model=TimeseriesResponse, summary="Get raw timeseries metrics")
async def get_timeseries_metrics(
    request: TimeseriesRequest,
    _: None = Depends(ensure_enabled),
    service: SandvikService = Depends(get_sandvik_service)
) -> TimeseriesResponse:
    """
    Get raw timeseries metrics data from Sandvik API.

    This endpoint returns the processed timeseries data directly from the Sandvik API,
    cleaned and formatted according to the documentation specifications.
    """
    try:
        # Get access token and fetch data
        raw_data = service.client.fetch_timeseries_data(
            machine_names=request.machine_names,
            start_date=request.start_date,
            end_date=request.end_date,
            part_numbers=request.part_numbers
        )

        # Process the data
        processed_data = service._process_timeseries_data(raw_data)

        return TimeseriesResponse(
            data=processed_data,
            count=len(processed_data)
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch timeseries data: {str(e)}"
        )


@router.post("/machines/history", response_model=MachineHistoryResponse, summary="Get machine history")
async def get_machine_history(
    request: MachineHistoryRequest,
    _: None = Depends(ensure_enabled),
    service: SandvikService = Depends(get_sandvik_service)
) -> MachineHistoryResponse:
    """
    Get machine history data with summaries.

    Returns aggregated metrics and summaries for machines or machine groups
    over a specified date range. If no machines are specified, returns data
    for all available machines.
    """
    try:
        return service.get_machine_history(
            machine_group=request.machine_group,
            machine_names=request.machine_names,
            start_date=request.start_date,
            end_date=request.end_date,
            part_numbers=request.part_numbers
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch machine history: {str(e)}"
        )


@router.post("/machines/live", response_model=LiveMetricsResponse, summary="Get live machine metrics")
async def get_live_metrics(
    request: LiveMetricsRequest,
    _: None = Depends(ensure_enabled),
    service: SandvikService = Depends(get_sandvik_service)
) -> LiveMetricsResponse:
    """
    Get live machine metrics (recent data).

    Returns current status and recent performance metrics for machines.
    Default lookback period is 24 hours.
    """
    try:
        return service.get_live_metrics(
            machine_group=request.machine_group,
            machine_names=request.machine_names,
            lookback_hours=request.lookback_hours
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch live metrics: {str(e)}"
        )


# Convenience endpoints for specific machine groups
@router.get("/groups/{group_name}/history", response_model=MachineHistoryResponse, summary="Get machine group history")
async def get_machine_group_history(
    group_name: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    part_numbers: Optional[List[str]] = None,
    _: None = Depends(ensure_enabled),
    service: SandvikService = Depends(get_sandvik_service)
) -> MachineHistoryResponse:
    """
    Get history data for a specific machine group.

    Path parameters:
    - group_name: Name of the machine group (e.g., 'DMC_100', 'NLX2500')

    Query parameters:
    - start_date: Optional start date (YYYY-MM-DD)
    - end_date: Optional end date (YYYY-MM-DD)
    - part_numbers: Optional comma-separated list of part numbers
    """
    try:
        # Validate group name
        available_groups = get_machine_group_names()
        if group_name not in available_groups:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Machine group '{group_name}' not found. Available groups: {available_groups}"
            )

        return service.get_machine_history(
            machine_group=group_name,
            start_date=start_date,
            end_date=end_date,
            part_numbers=part_numbers
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch machine group history: {str(e)}"
        )


@router.get("/groups/{group_name}/live", response_model=LiveMetricsResponse, summary="Get machine group live metrics")
async def get_machine_group_live(
    group_name: str,
    lookback_hours: Optional[int] = 24,
    _: None = Depends(ensure_enabled),
    service: SandvikService = Depends(get_sandvik_service)
) -> LiveMetricsResponse:
    """
    Get live metrics for a specific machine group.

    Path parameters:
    - group_name: Name of the machine group (e.g., 'DMC_100', 'NLX2500')

    Query parameters:
    - lookback_hours: Hours of recent data to include (1-168, default: 24)
    """
    try:
        # Validate group name
        available_groups = get_machine_group_names()
        if group_name not in available_groups:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Machine group '{group_name}' not found. Available groups: {available_groups}"
            )

        if lookback_hours and (lookback_hours < 1 or lookback_hours > 168):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="lookback_hours must be between 1 and 168"
            )

        return service.get_live_metrics(
            machine_group=group_name,
            lookback_hours=lookback_hours
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch machine group live metrics: {str(e)}"
        )

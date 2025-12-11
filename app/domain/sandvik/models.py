"""
Sandvik API domain models and schemas.

This module defines Pydantic models for Sandvik Machining Insights API
requests and responses.
"""

from datetime import date
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class MachineGroup(BaseModel):
    """Machine group configuration model."""
    display_name: str = Field(..., description="Human-readable display name for the group")
    devices: List[str] = Field(..., description="List of device identifiers in this group")


class MachineConfig(BaseModel):
    """Machine configuration with all available groups."""
    groups: Dict[str, MachineGroup] = Field(..., description="Dictionary of machine groups by name")


class TimeseriesRequest(BaseModel):
    """Request model for timeseries metrics API."""
    machine_names: List[str] = Field(..., description="List of machine names to query")
    start_date: Optional[date] = Field(None, description="Start date for data range (defaults to 10 days ago)")
    end_date: Optional[date] = Field(None, description="End date for data range (defaults to today)")
    part_numbers: Optional[List[str]] = Field(None, description="Optional list of part numbers to filter by")


class MachineHistoryRequest(BaseModel):
    """Request model for machine history data."""
    machine_group: Optional[str] = Field(None, description="Machine group name (e.g., 'DMC_100', 'NLX2500')")
    machine_names: Optional[List[str]] = Field(None, description="Specific machine names to query")
    start_date: Optional[date] = Field(None, description="Start date for history range")
    end_date: Optional[date] = Field(None, description="End date for history range")
    part_numbers: Optional[List[str]] = Field(None, description="Optional list of part numbers to filter by")


class LiveMetricsRequest(BaseModel):
    """Request model for live machine metrics."""
    machine_group: Optional[str] = Field(None, description="Machine group name")
    machine_names: Optional[List[str]] = Field(None, description="Specific machine names to query")
    lookback_hours: Optional[int] = Field(24, ge=1, le=168, description="Hours of recent data to fetch (1-168)")


class TimeseriesMetric(BaseModel):
    """Individual timeseries metric record."""
    device: str = Field(..., description="Cleaned machine device name")
    workday: date = Field(..., description="Workday date")
    kind: str = Field(..., description="Part number/kind identifier")
    duration_sum: int = Field(..., description="Total duration in milliseconds")
    total_part_count: int = Field(..., description="Total number of parts produced")
    good_part_count: int = Field(..., description="Number of good parts")
    bad_part_count: int = Field(..., description="Number of bad parts")
    cycle_time: Optional[float] = Field(None, description="Cycle time in milliseconds")
    producing_duration: int = Field(..., description="Time spent producing in milliseconds")
    pdt_duration: int = Field(..., description="Planned downtime duration in milliseconds")
    udt_duration: int = Field(..., description="Unplanned downtime duration in milliseconds")
    setup_duration: int = Field(..., description="Setup time duration in milliseconds")
    producing_percentage: float = Field(..., description="Percentage of time producing (0.0-1.0)")
    pdt_percentage: float = Field(..., description="Percentage of planned downtime (0.0-1.0)")
    udt_percentage: float = Field(..., description="Percentage of unplanned downtime (0.0-1.0)")
    setup_percentage: float = Field(..., description="Percentage of setup time (0.0-1.0)")


class MachineMetricsSummary(BaseModel):
    """Summary metrics for a machine over a time period."""
    device: str = Field(..., description="Machine device name")
    total_duration: int = Field(..., description="Total operating time in milliseconds")
    total_parts: int = Field(..., description="Total parts produced")
    good_parts: int = Field(..., description="Good parts produced")
    bad_parts: int = Field(..., description="Bad parts produced")
    average_cycle_time: Optional[float] = Field(None, description="Average cycle time in milliseconds")
    producing_time: int = Field(..., description="Total producing time in milliseconds")
    planned_downtime: int = Field(..., description="Total planned downtime in milliseconds")
    unplanned_downtime: int = Field(..., description="Total unplanned downtime in milliseconds")
    setup_time: int = Field(..., description="Total setup time in milliseconds")
    availability_percentage: float = Field(..., description="Overall availability percentage (0.0-1.0)")
    efficiency_percentage: float = Field(..., description="Production efficiency percentage (0.0-1.0)")


class MachineGroupSummary(BaseModel):
    """Summary for an entire machine group."""
    group_name: str = Field(..., description="Machine group name")
    machine_count: int = Field(..., description="Number of machines in group")
    total_parts: int = Field(..., description="Total parts produced by group")
    average_availability: float = Field(..., description="Average availability across machines")
    average_efficiency: float = Field(..., description="Average efficiency across machines")
    machines: List[MachineMetricsSummary] = Field(..., description="Individual machine summaries")


class TimeseriesResponse(BaseModel):
    """Response model for timeseries metrics API."""
    data: List[TimeseriesMetric] = Field(..., description="List of timeseries metric records")
    count: int = Field(..., description="Number of records returned")


class MachineHistoryResponse(BaseModel):
    """Response model for machine history API."""
    machine_summaries: List[MachineMetricsSummary] = Field(..., description="Individual machine summaries")
    group_summaries: List[MachineGroupSummary] = Field(..., description="Machine group summaries")
    date_range: Dict[str, date] = Field(..., description="Date range of the data")


class LiveMetricsResponse(BaseModel):
    """Response model for live metrics API."""
    machine_summaries: List[MachineMetricsSummary] = Field(..., description="Current machine status summaries")
    last_updated: str = Field(..., description="Timestamp of last data update")
    lookback_hours: int = Field(..., description="Hours of data included in summary")

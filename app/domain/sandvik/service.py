"""
Sandvik domain service for machining insights.

This module provides business logic for processing Sandvik API data
and generating machine history and live view summaries.
"""

import logging
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional
from collections import defaultdict

import pandas as pd

from app.domain.sandvik.client import SandvikAPIClient
from app.domain.sandvik.config import expand_machine_groups, get_machine_config
from app.domain.sandvik.models import (
    MachineHistoryResponse,
    MachineMetricsSummary,
    MachineGroupSummary,
    LiveMetricsResponse,
    TimeseriesMetric
)

logger = logging.getLogger(__name__)


class SandvikService:
    """Service for processing Sandvik machining insights data."""

    def __init__(self):
        self.client = SandvikAPIClient()
        self.machine_config = get_machine_config()

    def get_machine_history(
        self,
        machine_group: str = None,
        machine_names: List[str] = None,
        start_date: date = None,
        end_date: date = None,
        part_numbers: List[str] = None
    ) -> MachineHistoryResponse:
        """
        Get machine history data for specified machines/groups.

        Args:
            machine_group: Optional machine group name
            machine_names: Optional list of specific machine names
            start_date: Start date for history range
            end_date: End date for history range
            part_numbers: Optional list of part numbers to filter by

        Returns:
            MachineHistoryResponse with summaries
        """
        # Determine which machines to query
        if machine_names:
            machines_to_query = machine_names
        elif machine_group:
            machines_to_query = expand_machine_groups([machine_group])
        else:
            machines_to_query = expand_machine_groups()

        logger.info(f"Fetching history for {len(machines_to_query)} machines")

        # Fetch raw data
        raw_data = self.client.fetch_timeseries_data(
            machine_names=machines_to_query,
            start_date=start_date,
            end_date=end_date,
            part_numbers=part_numbers
        )

        # Process data
        processed_data = self._process_timeseries_data(raw_data)
        machine_summaries = self._calculate_machine_summaries(processed_data)
        group_summaries = self._calculate_group_summaries(machine_summaries)

        return MachineHistoryResponse(
            machine_summaries=machine_summaries,
            group_summaries=group_summaries,
            date_range={
                "start": start_date or (date.today() - timedelta(days=10)),
                "end": end_date or date.today()
            }
        )

    def get_live_metrics(
        self,
        machine_group: str = None,
        machine_names: List[str] = None,
        lookback_hours: int = 24
    ) -> LiveMetricsResponse:
        """
        Get live metrics for machines (recent data).

        Args:
            machine_group: Optional machine group name
            machine_names: Optional list of specific machine names
            lookback_hours: Hours of recent data to include

        Returns:
            LiveMetricsResponse with current status
        """
        # Determine which machines to query
        if machine_names:
            machines_to_query = machine_names
        elif machine_group:
            machines_to_query = expand_machine_groups([machine_group])
        else:
            machines_to_query = expand_machine_groups()

        # Calculate date range for recent data
        end_date = date.today()
        start_date = end_date - timedelta(hours=lookback_hours)

        logger.info(f"Fetching live metrics for {len(machines_to_query)} machines (last {lookback_hours} hours)")

        # Fetch raw data
        raw_data = self.client.fetch_timeseries_data(
            machine_names=machines_to_query,
            start_date=start_date,
            end_date=end_date
        )

        # Process data
        processed_data = self._process_timeseries_data(raw_data)
        machine_summaries = self._calculate_machine_summaries(processed_data)

        return LiveMetricsResponse(
            machine_summaries=machine_summaries,
            last_updated=datetime.now().isoformat(),
            lookback_hours=lookback_hours
        )

    def _process_timeseries_data(self, raw_data: List[Dict]) -> List[TimeseriesMetric]:
        """
        Process raw timeseries data from API into structured format.

        Args:
            raw_data: Raw data from Sandvik API

        Returns:
            List of processed TimeseriesMetric objects
        """
        processed_records = []

        for record in raw_data:
            try:
                # Clean device name
                device = self.client.clean_device_name(record.get("device", ""))

                # Convert workday to date
                workday_str = record.get("workday")
                if workday_str:
                    workday = pd.to_datetime(workday_str).date()
                else:
                    continue  # Skip records without workday

                # Format part kind
                kind = record.get("kind", "")
                if kind:
                    kind = self.client.format_part_kind(kind)

                # Create TimeseriesMetric object
                metric = TimeseriesMetric(
                    device=device,
                    workday=workday,
                    kind=kind,
                    duration_sum=record.get("duration_sum", 0),
                    total_part_count=record.get("total_part_count", 0),
                    good_part_count=record.get("good_part_count", 0),
                    bad_part_count=record.get("bad_part_count", 0),
                    cycle_time=record.get("cycle_time"),
                    producing_duration=record.get("producing_duration", 0),
                    pdt_duration=record.get("pdt_duration", 0),
                    udt_duration=record.get("udt_duration", 0),
                    setup_duration=record.get("setup_duration", 0),
                    producing_percentage=record.get("producing_percentage", 0.0),
                    pdt_percentage=record.get("pdt_percentage", 0.0),
                    udt_percentage=record.get("udt_percentage", 0.0),
                    setup_percentage=record.get("setup_percentage", 0.0)
                )

                processed_records.append(metric)

            except Exception as e:
                logger.warning(f"Failed to process record: {record}. Error: {e}")
                continue

        logger.info(f"Processed {len(processed_records)} timeseries records")
        return processed_records

    def _calculate_machine_summaries(self, data: List[TimeseriesMetric]) -> List[MachineMetricsSummary]:
        """
        Calculate summary metrics for each machine.

        Args:
            data: Processed timeseries data

        Returns:
            List of machine summaries
        """
        # Group data by device
        device_data = defaultdict(list)
        for record in data:
            device_data[record.device].append(record)

        summaries = []

        for device, records in device_data.items():
            # Aggregate metrics across all records for this device
            total_duration = sum(r.duration_sum for r in records)
            total_parts = sum(r.total_part_count for r in records)
            good_parts = sum(r.good_part_count for r in records)
            bad_parts = sum(r.bad_part_count for r in records)

            # Calculate average cycle time (only for records with cycle time)
            cycle_times = [r.cycle_time for r in records if r.cycle_time is not None]
            average_cycle_time = sum(cycle_times) / len(cycle_times) if cycle_times else None

            # Aggregate time breakdowns
            producing_time = sum(r.producing_duration for r in records)
            planned_downtime = sum(r.pdt_duration for r in records)
            unplanned_downtime = sum(r.udt_duration for r in records)
            setup_time = sum(r.setup_duration for r in records)

            # Calculate percentages
            if total_duration > 0:
                availability_percentage = producing_time / total_duration
                # Efficiency = good parts / total parts (if we have part data)
                efficiency_percentage = good_parts / total_parts if total_parts > 0 else 0.0
            else:
                availability_percentage = 0.0
                efficiency_percentage = 0.0

            summary = MachineMetricsSummary(
                device=device,
                total_duration=total_duration,
                total_parts=total_parts,
                good_parts=good_parts,
                bad_parts=bad_parts,
                average_cycle_time=average_cycle_time,
                producing_time=producing_time,
                planned_downtime=planned_downtime,
                unplanned_downtime=unplanned_downtime,
                setup_time=setup_time,
                availability_percentage=round(availability_percentage, 4),
                efficiency_percentage=round(efficiency_percentage, 4)
            )

            summaries.append(summary)

        # Sort by device name
        summaries.sort(key=lambda x: x.device)

        return summaries

    def _calculate_group_summaries(self, machine_summaries: List[MachineMetricsSummary]) -> List[MachineGroupSummary]:
        """
        Calculate summary metrics for machine groups.

        Args:
            machine_summaries: Individual machine summaries

        Returns:
            List of group summaries
        """
        # Group machines by their groups
        group_data = defaultdict(list)

        for summary in machine_summaries:
            # Find which group this machine belongs to
            for group_name, group_info in self.machine_config.groups.items():
                if any(summary.device in device for device in group_info.devices):
                    group_data[group_name].append(summary)
                    break

        group_summaries = []

        for group_name, summaries in group_data.items():
            machine_count = len(summaries)
            total_parts = sum(s.total_parts for s in summaries)
            avg_availability = sum(s.availability_percentage for s in summaries) / machine_count
            avg_efficiency = sum(s.efficiency_percentage for s in summaries) / machine_count

            group_summary = MachineGroupSummary(
                group_name=group_name,
                machine_count=machine_count,
                total_parts=total_parts,
                average_availability=round(avg_availability, 4),
                average_efficiency=round(avg_efficiency, 4),
                machines=summaries
            )

            group_summaries.append(group_summary)

        # Sort by group name
        group_summaries.sort(key=lambda x: x.group_name)

        return group_summaries

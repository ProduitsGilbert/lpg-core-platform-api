"""
Sandvik API client for Machining Insights platform.

This module provides a client for authenticating with and fetching data from
the Sandvik Machining Insights API.
"""

import logging
import re
from datetime import date, datetime, time, timezone
from typing import Dict, List, Optional, Any
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from app.settings import settings

logger = logging.getLogger(__name__)


class SandvikAPIClient:
    """Client for interacting with Sandvik Machining Insights API."""

    def __init__(self):
        self.base_url = settings.sandvik_base_url
        self.tenant = settings.sandvik_tenant
        self.timeout = settings.sandvik_api_timeout
        self.max_retries = settings.sandvik_max_retries

        # API endpoints
        self.oauth_url = f"{self.base_url}/api/v1/auth/oauth/token"
        self.timeseries_url = f"{self.base_url}/api/v3/timeseries-metrics/flattened"

        # Session with retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=self.max_retries,
            status_forcelist=[429, 500, 502, 503, 504],
            backoff_factor=1
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)

        # Cached token
        self._access_token: Optional[str] = None
        self._token_expires: Optional[datetime] = None

    def _get_auth_headers(self) -> Dict[str, str]:
        """Get headers for authentication requests."""
        return {
            "Content-Type": "application/x-www-form-urlencoded",
            "X-Tenant": self.tenant
        }

    def _get_api_headers(self, token: str) -> Dict[str, str]:
        """Get headers for API requests."""
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-Tenant": self.tenant
        }

    def get_access_token(self) -> str:
        """
        Obtain OAuth2 access token using password grant flow.

        Returns:
            Access token string

        Raises:
            requests.HTTPError: If authentication fails
        """
        if not all([
            settings.sandvik_username,
            settings.sandvik_password,
            settings.sandvik_client_id,
            settings.sandvik_client_secret
        ]):
            raise ValueError("Sandvik API credentials not configured")

        # Check if we have a valid cached token
        if self._access_token and self._token_expires:
            if datetime.now(timezone.utc) < self._token_expires:
                return self._access_token

        data = {
            "grant_type": "password",
            "username": settings.sandvik_username,
            "password": settings.sandvik_password,
            "client_id": settings.sandvik_client_id,
            "client_secret": settings.sandvik_client_secret
        }

        logger.info("Requesting new Sandvik API access token")

        response = self.session.post(
            self.oauth_url,
            headers=self._get_auth_headers(),
            data=data,
            timeout=self.timeout
        )

        response.raise_for_status()

        token_data = response.json()
        self._access_token = token_data["access_token"]

        # Cache token with expiration (assuming 1 hour validity)
        self._token_expires = datetime.now(timezone.utc) + datetime.timedelta(hours=1)

        logger.info("Successfully obtained Sandvik API access token")
        return self._access_token

    def fetch_timeseries_data(
        self,
        machine_names: List[str],
        start_date: date = None,
        end_date: date = None,
        part_numbers: List[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch timeseries metrics data from Sandvik API.

        Args:
            machine_names: List of machine device names
            start_date: Start date for data range
            end_date: End date for data range
            part_numbers: Optional list of part numbers to filter by

        Returns:
            List of timeseries metric records

        Raises:
            requests.HTTPError: If API request fails
        """
        token = self.get_access_token()
        payload = self._build_timeseries_payload(machine_names, start_date, end_date, part_numbers)

        logger.info(f"Fetching timeseries data for {len(machine_names)} machines from {start_date} to {end_date}")

        response = self.session.post(
            self.timeseries_url,
            headers=self._get_api_headers(token),
            json=payload,
            timeout=self.timeout
        )

        response.raise_for_status()

        data = response.json()
        logger.info(f"Successfully fetched {len(data)} timeseries records")

        return data

    def _build_timeseries_payload(
        self,
        machine_names: List[str],
        start_date: date = None,
        end_date: date = None,
        part_numbers: List[str] = None
    ) -> Dict[str, Any]:
        """
        Build the payload for timeseries metrics API request.

        Args:
            machine_names: List of machine device names
            start_date: Start date for data range
            end_date: End date for data range
            part_numbers: Optional list of part numbers to filter by

        Returns:
            Request payload dictionary
        """
        # Default to last 10 days if no dates provided
        if not start_date:
            start_date = date.today() - datetime.timedelta(days=10)
        if not end_date:
            end_date = date.today()

        # Convert dates to ISO format with timezone
        start_datetime = datetime.combine(start_date, time.min, timezone.utc)
        end_datetime = datetime.combine(end_date, time.max, timezone.utc)

        payload = {
            "filters": {
                "must": [
                    {
                        "filterType": "terms",
                        "fieldName": "entity.device",
                        "values": machine_names
                    },
                    {
                        "filterType": "term",
                        "fieldName": "entity.plant",
                        "values": self.tenant
                    },
                    {
                        "filterType": "range",
                        "fieldName": "timestamp",
                        "values": {
                            "gte": start_datetime.isoformat().replace("+00:00", "Z"),
                            "lt": end_datetime.isoformat().replace("+00:00", "Z")
                        }
                    }
                ],
                "mustNot": []
            },
            "bins": [
                {
                    "binName": "by_workday",
                    "fieldName": "dimensions.workday",
                    "aggType": "date_histogram",
                    "options": {
                        "calendar_interval": "day",
                        "script": {
                            "scriptName": "exclude_days_of_week",
                            "ignoreScript": True
                        }
                    }
                },
                {
                    "binName": "by_kind",
                    "fieldName": "dimensions.part_kind",
                    "aggType": "terms",
                    "options": {}
                },
                {
                    "binName": "by_device",
                    "fieldName": "entity.device",
                    "aggType": "terms",
                    "options": {}
                }
            ],
            "metrics": [
                "duration_sum",
                "total_part_count",
                "good_part_count",
                "bad_part_count",
                "cycle_time",
                "producing_duration",
                "pdt_duration",
                "udt_duration",
                "setup_duration",
                "producing_percentage",
                "pdt_percentage",
                "udt_percentage",
                "setup_percentage"
            ]
        }

        # Optional part number filter
        if part_numbers:
            payload["filters"]["must"].append({
                "filterType": "terms",
                "fieldName": "dimensions.part_kind",
                "values": part_numbers
            })

        return payload

    @staticmethod
    def clean_device_name(device_name: str) -> str:
        """
        Clean device names by removing prefix and hash suffix.

        Args:
            device_name: Raw device name from API

        Returns:
            Cleaned device name
        """
        # Remove 'produitsgilbert_' prefix
        cleaned = device_name.replace(f"{settings.sandvik_tenant}_", "")

        # Remove hash suffix (last underscore followed by 6 characters)
        cleaned = re.sub(r"_[a-fA-F0-9]{6}$", "", cleaned)

        return cleaned

    @staticmethod
    def format_part_kind(part_kind: str) -> str:
        """
        Format part kind identifiers.

        Args:
            part_kind: Raw part kind from API

        Returns:
            Formatted part kind
        """
        # Apply regex transformation: r"^(\d{7})-(\d{3})-(\dOP)$" → r"\1_\2-\3"
        return re.sub(
            r"^(\d{7})-(\d{3})-(\dOP)$",
            r"\1_\2-\3",
            part_kind
        )

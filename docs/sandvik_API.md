# Sandvik Machining Insights API Integration Documentation

## Overview
This document outlines how to recreate the Sandvik Insight API integration logic from the existing Streamlit dashboard into a FastAPI application. The integration fetches manufacturing data (timeseries metrics) from Sandvik's Machining Insights platform.

## Libraries and Dependencies

### Core Dependencies
```txt
pandas>=2.0.0
requests>=2.31.0
python-dotenv>=1.0.0
fastapi>=0.100.0
uvicorn>=0.23.0
pydantic>=2.0.0
logfire>=0.0.0  # For logging (optional)
```

### Optional Dependencies (for development/testing)
```txt
mypy>=1.5.0
types-requests>=2.31.0
```

## API Configuration and Credentials

### Environment Variables
Create a `.env` file in your project root:

```env

```

### API Endpoints

```python
API_BASE_URL = "https://machininginsights.sandvikcoromant.com"

# Authentication endpoint
OAUTH_URL = f"{API_BASE_URL}/api/v1/auth/oauth/token"

# Device information endpoint
PLANT_DEVICE_URL = f"{API_BASE_URL}/api/v1/plant/device"

# Timeseries metrics endpoint
TIMESERIES_URL = f"{API_BASE_URL}/api/v3/timeseries-metrics/flattened"
```

## Authentication Flow

### OAuth2 Password Grant Flow

```python
import requests
from typing import Dict, Any

def get_access_token() -> str:
    """Obtain OAuth2 access token using password grant flow."""

    url = "https://machininginsights.sandvikcoromant.com/api/v1/auth/oauth/token"

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "X-Tenant": "produitsgilbert"
    }

    data = {
        "grant_type": "password",
        "username": "apiuser",
        "password": "V1MANAAP!user",
        "client_id": "tenant_produitsgilbert",
        "client_secret": "oZBPsF@PtaJOrcUcs5U!6^!ok#@U!#EH"
    }

    response = requests.post(url, headers=headers, data=data)
    response.raise_for_status()

    token_data = response.json()
    return token_data["access_token"]
```

### Token Usage
All subsequent API calls require the Authorization header:
```python
headers = {
    "Authorization": f"Bearer {access_token}",
    "X-Tenant": "produitsgilbert"
}
```

## Machine/Device Configuration

### Available Machines
The system has the following machine groups and devices:

```python
MACHINE_GROUPS = {
    "DMC_100": {
        "display_name": "DMC 100 (Machines 1-4)",
        "devices": [
            "produitsgilbert_DMC_100_01_5a1286",
            "produitsgilbert_DMC_100_02_3c11c4",
            "produitsgilbert_DMC_100_03_9ad22c",
            "produitsgilbert_DMC_100_04_d81500",
        ],
    },
    "NLX2500": {
        "display_name": "NLX-2500 (Machines 1-5)",
        "devices": [
            "produitsgilbert_NLX-2500-01_1f62d2",
            "produitsgilbert_NLX-2500-02_c48076",
            "produitsgilbert_NLX-2500-03_7db86c",
            "produitsgilbert_NLX-2500-04_aae59b",
            "produitsgilbert_NLX-2500-05_1291f0",
        ],
    },
    "MZ350": {
        "display_name": "TOU-MZ350 (Machines 1-3)",
        "devices": [
            "produitsgilbert_TOU-MZ350-01_dd405f",
            "produitsgilbert_TOU-MZ350-02_97ae33",
            "produitsgilbert_TOU-MZ350-03_f3e3e6",
        ],
    },
    "DMC_340": {
        "display_name": "DMC 340 (Machine 1)",
        "devices": ["produitsgilbert_DMC_340_01_53afe9"],
    },
    "DEC_370": {
        "display_name": "DEC 370 (Machine 1)",
        "devices": ["produitsgilbert_DEC_370_01_90441a"],
    },
    "MTV_655": {
        "display_name": "MTV 655 (Machine 1)",
        "devices": ["produitsgilbert_MTV_655_01_65b08f"],
    },
}
```

### Device Name Pattern
Device names follow the pattern: `produitsgilbert_{MACHINE_TYPE}_{NUMBER}_{HASH}`

Where:
- `produitsgilbert_` is the tenant prefix
- `{MACHINE_TYPE}` is the machine model (e.g., DMC_100, NLX-2500)
- `{NUMBER}` is the machine number (01, 02, etc.)
- `{HASH}` is a 6-character hexadecimal identifier

### Device Name Cleaning Function

```python
import re

def clean_device_name(device_name: str) -> str:
    """Clean device names by removing prefix and hash suffix."""
    # Remove 'produitsgilbert_' prefix
    cleaned = device_name.replace("produitsgilbert_", "")

    # Remove hash suffix (last underscore followed by 6 characters)
    cleaned = re.sub(r"_[a-fA-F0-9]{6}$", "", cleaned)

    return cleaned
```

## Data Fetching API

### Timeseries Metrics Endpoint

**Method:** POST
**URL:** `https://machininginsights.sandvikcoromant.com/api/v3/timeseries-metrics/flattened`

**Headers:**
```json
{
  "Authorization": "Bearer {access_token}",
  "Content-Type": "application/json",
  "X-Tenant": "produitsgilbert"
}
```

### Request Payload Structure

```python
def build_timeseries_payload(
    machine_names: list[str],
    start_date: datetime.date = None,
    end_date: datetime.date = None,
    part_numbers: list[str] = None
) -> dict:
    """Build the payload for timeseries metrics API request."""

    # Default to last 10 days if no dates provided
    if not start_date:
        start_date = datetime.date.today() - datetime.timedelta(days=10)
    if not end_date:
        end_date = datetime.date.today()

    # Convert dates to ISO format with timezone
    start_datetime = datetime.datetime.combine(
        start_date, datetime.time.min, datetime.timezone.utc
    )
    end_datetime = datetime.datetime.combine(
        end_date, datetime.time.max, datetime.timezone.utc
    )

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
                    "values": "produitsgilbert"
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
```

## Response Data Structure

### API Response Format
The `/v3/timeseries-metrics/flattened` endpoint returns a flattened JSON array where each object represents a unique combination of the bin dimensions (device, workday, part_kind) with corresponding metric values.

### Expected DataFrame Columns
The API returns data in the following format (after processing):

- `device`: Machine identifier (cleaned)
- `workday`: Date of the workday (converted from string to date)
- `kind`: Part number/kind identifier (formatted)
- `duration_sum`: Total duration in milliseconds
- `total_part_count`: Total number of parts produced
- `good_part_count`: Number of good parts
- `bad_part_count`: Number of bad parts
- `cycle_time`: Cycle time in milliseconds
- `producing_duration`: Time spent producing
- `pdt_duration`: Planned downtime duration
- `udt_duration`: Unplanned downtime duration
- `setup_duration`: Setup time duration
- `producing_percentage`: Percentage of time producing (decimal)
- `pdt_percentage`: Percentage of planned downtime (decimal)
- `udt_percentage`: Percentage of unplanned downtime (decimal)
- `setup_percentage`: Percentage of setup time (decimal)

### Data Processing Notes

1. **Workday Conversion**: Convert workday strings to date objects using `pd.to_datetime(df["workday"]).dt.date`
2. **Part Kind Formatting**: Apply regex transformation: `r"^(\d{7})-(\d{3})-(\dOP)$"` → `r"\1_\2-\3"`
3. **Time Units**: All durations are in milliseconds, percentages are decimal values (0.0 to 1.0)
4. **Null Handling**: Check for null cycle_time and zero total_part_count - this may indicate data availability issues
5. **Device Name Cleaning**: Remove tenant prefix and hash suffix from device names

## FastAPI Implementation Example

### Pydantic Models

```python
from pydantic import BaseModel
from typing import List, Optional
from datetime import date

class TimeseriesRequest(BaseModel):
    machine_names: List[str]
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    part_numbers: Optional[List[str]] = None

class MachineGroup(BaseModel):
    display_name: str
    devices: List[str]

class MachineConfig(BaseModel):
    groups: dict[str, MachineGroup]
```

### FastAPI Endpoint

```python
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import pandas as pd

app = FastAPI(title="Sandvik Insight API")

@app.post("/api/v1/timeseries-metrics")
async def get_timeseries_metrics(request: TimeseriesRequest):
    """Fetch timeseries metrics from Sandvik Insight API."""
    try:
        # Get access token
        token = get_access_token()

        # Build payload
        payload = build_timeseries_payload(
            request.machine_names,
            request.start_date,
            request.end_date,
            request.part_numbers
        )

        # Make API request
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-Tenant": "produitsgilbert"
        }

        response = requests.post(TIMESERIES_URL, headers=headers, json=payload)
        response.raise_for_status()

        # Process response
        data = response.json()
        df = pd.DataFrame(data)

        # Apply data processing
        if "workday" in df.columns:
            df["workday"] = pd.to_datetime(df["workday"]).dt.date

        if "device" in df.columns:
            df["device"] = df["device"].apply(clean_device_name)

        # Apply part kind formatting
        if "kind" in df.columns:
            df["kind"] = df["kind"].str.replace(
                r"^(\d{7})-(\d{3})-(\dOP)$", r"\1_\2-\3", regex=True
            )

        return JSONResponse(content=df.to_dict(orient="records"))

    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"API request failed: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

@app.get("/api/v1/machines")
async def get_machines():
    """Get available machine configuration."""
    return MachineConfig(groups=MACHINE_GROUPS)
```

## Error Handling and Logging

### Common Error Scenarios

1. **Authentication Failures**: Invalid credentials or expired tokens
2. **Rate Limiting**: API request limits exceeded
3. **Network Issues**: Connection timeouts or connectivity problems
4. **Data Availability**: No data found for requested parameters
5. **Invalid Parameters**: Malformed device names or date ranges

### Logging Recommendations

```python
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Log API calls
logger.info(f"Fetching data for devices: {machine_names}")
logger.info(f"Date range: {start_date} to {end_date}")

# Log errors
logger.error(f"API request failed: {str(e)}")
```

## Testing and Development

### Unit Testing Example

```python
import pytest
from unittest.mock import patch, MagicMock

def test_get_access_token():
    """Test OAuth token retrieval."""
    with patch('requests.post') as mock_post:
        mock_response = MagicMock()
        mock_response.json.return_value = {"access_token": "test_token"}
        mock_post.return_value = mock_response

        token = get_access_token()
        assert token == "test_token"

def test_clean_device_name():
    """Test device name cleaning."""
    input_name = "produitsgilbert_DMC_100_01_5a1286"
    expected = "DMC_100_01"
    assert clean_device_name(input_name) == expected
```

### Integration Testing

```python
def test_timeseries_api_integration():
    """Test full API integration with mock responses."""
    # Mock the entire API flow
    with patch('requests.post') as mock_post:
        # Mock token response
        token_response = MagicMock()
        token_response.json.return_value = {"access_token": "test_token"}

        # Mock data response
        data_response = MagicMock()
        data_response.json.return_value = [
            {
                "device": "produitsgilbert_DMC_100_01_5a1286",
                "workday": "2024-01-01",
                "kind": "1234567-001-1OP",
                "total_part_count": 100,
                "cycle_time": 300000
            }
        ]

        # Configure mock to return different responses
        mock_post.side_effect = [token_response, data_response]

        # Test the endpoint
        request = TimeseriesRequest(machine_names=["test_device"])
        result = get_timeseries_metrics(request)

        assert len(result) == 1
        assert result[0]["device"] == "DMC_100_01"
```

## Deployment Considerations

### Environment Setup

1. **Environment Variables**: Ensure all required env vars are set
2. **Secrets Management**: Use secure storage for API credentials
3. **Network Access**: Ensure outbound HTTPS access to Sandvik API
4. **Rate Limiting**: Implement request throttling if needed
5. **Caching**: Consider caching device lists and tokens

### Production Configuration

```python
# Production settings
API_TIMEOUT = int(os.getenv("SANDVIK_API_TIMEOUT", 30))
MAX_RETRIES = int(os.getenv("SANDVIK_MAX_RETRIES", 3))

# Request session with retry strategy
session = requests.Session()
retry_strategy = Retry(
    total=MAX_RETRIES,
    status_forcelist=[429, 500, 502, 503, 504],
    backoff_factor=1
)
adapter = HTTPAdapter(max_retries=retry_strategy)
session.mount("https://", adapter)
```

This documentation provides everything needed to recreate the Sandvik Insight API integration in a FastAPI application. The implementation includes authentication, data fetching, processing, and error handling patterns from the original codebase.

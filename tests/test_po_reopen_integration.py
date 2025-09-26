"""Live integration test for the PO reopen endpoint."""

import os
import time
from typing import Tuple

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.settings import settings


pytestmark = pytest.mark.integration


def _get_po_status(client: TestClient, po_number: str) -> Tuple[int, str]:
    response = client.get(f"/api/v1/erp/po/{po_number}")
    status = ""
    try:
        payload = response.json()
        status = payload.get("data", {}).get("status", "") if isinstance(payload, dict) else ""
    except ValueError:
        status = ""
    return response.status_code, status


@pytest.mark.integration
def test_reopen_purchase_order_live():
    if os.getenv("BC_RUN_INTEGRATION") != "1":
        pytest.skip("Set BC_RUN_INTEGRATION=1 to run live Business Central integration tests")

    if not settings.erp_base_url or "example" in settings.erp_base_url:
        pytest.skip("ERP endpoint not configured for integration testing")

    po_number = os.getenv("BC_TEST_PO_NUMBER", "PO034369")

    client = TestClient(app)

    status_code, initial_status = _get_po_status(client, po_number)
    assert status_code == 200, f"Failed to fetch PO {po_number} details"

    open_response = client.post(
        "/api/v1/erp/po/reopen",
        json={"headerNo": po_number},
    )

    assert open_response.status_code == 200, open_response.text

    final_status = ""
    for _ in range(5):
        code, final_status = _get_po_status(client, po_number)
        if code == 200 and final_status and final_status.lower() == "open":
            break
        time.sleep(1)

    assert final_status and final_status.lower() == "open"

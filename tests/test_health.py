"""
Health check test for the FastAPI application.

This test ensures the health endpoint is working correctly
and provides the required smoke test for CI/CD.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app


def test_health():
    """
    Test the health endpoint returns 200 OK with expected status.
    
    This is a critical smoke test that ensures the application
    is functioning at a basic level.
    """
    client = TestClient(app)
    response = client.get("/healthz")
    
    assert response.status_code == 200
    
    data = response.json()
    assert data.get("status") == "ok"
    assert "service" in data
    assert "version" in data
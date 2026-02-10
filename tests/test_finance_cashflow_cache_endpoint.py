import os
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from app.domain.finance.models import CashflowProjection
from app.main import app


def _client() -> TestClient:
    os.environ.setdefault("FINANCE_API_TOKEN", "finance-secret")
    return TestClient(app)


class _CacheStub:
    is_configured = True

    def __init__(self, snapshot=None, latest_snapshot=None):
        self.snapshot = snapshot
        self.latest_snapshot = latest_snapshot
        self.upserts = []
        self.invalidations = []
        self.pruned = []

    def get_snapshot(self, **kwargs):
        _ = kwargs
        return self.snapshot

    def get_latest_snapshot(self, **kwargs):
        _ = kwargs
        return self.latest_snapshot

    def upsert_snapshot(self, **kwargs):
        self.upserts.append(kwargs)

    def prune_before(self, cache_date: str):
        self.pruned.append(cache_date)

    def invalidate_cache_date(self, cache_date: str):
        self.invalidations.append(cache_date)


def test_cashflow_projection_uses_cache_hit() -> None:
    client = _client()
    cache = _CacheStub(
        snapshot={
            "start_date": "2026-02-01",
            "end_date": "2026-02-02",
            "daily_flows": [],
        }
    )
    svc = MagicMock()
    svc.get_projection = AsyncMock()

    app.dependency_overrides = app.dependency_overrides or {}
    from app.api.v1.finance.router import get_service, verify_finance_token

    app.dependency_overrides[get_service] = lambda: svc
    app.dependency_overrides[verify_finance_token] = lambda: "finance-secret"
    try:
        with patch("app.api.v1.finance.router.cashflow_projection_cache", cache):
            response = client.get(
                "/api/v1/finance/cashflow?start_date=2026-02-01&end_date=2026-02-02",
                headers={"X-Finance-Token": "finance-secret"},
            )
    finally:
        app.dependency_overrides.pop(get_service, None)
        app.dependency_overrides.pop(verify_finance_token, None)

    assert response.status_code == 200, response.text
    svc.get_projection.assert_not_called()


def test_cashflow_projection_cache_miss_populates_cache() -> None:
    client = _client()
    cache = _CacheStub(snapshot=None)
    svc = MagicMock()
    svc.get_projection = AsyncMock(
        return_value=CashflowProjection.model_validate(
            {
                "start_date": "2026-02-01",
                "end_date": "2026-02-02",
                "daily_flows": [],
            }
        )
    )

    from app.api.v1.finance.router import get_service, verify_finance_token

    app.dependency_overrides[get_service] = lambda: svc
    app.dependency_overrides[verify_finance_token] = lambda: "finance-secret"
    try:
        with patch("app.api.v1.finance.router.cashflow_projection_cache", cache):
            response = client.get(
                "/api/v1/finance/cashflow?start_date=2026-02-01&end_date=2026-02-02",
                headers={"X-Finance-Token": "finance-secret"},
            )
    finally:
        app.dependency_overrides.pop(get_service, None)
        app.dependency_overrides.pop(verify_finance_token, None)

    assert response.status_code == 200, response.text
    svc.get_projection.assert_awaited_once()
    assert len(cache.upserts) == 1


def test_cashflow_projection_refresh_bypasses_cache() -> None:
    client = _client()
    cache = _CacheStub(
        snapshot={
            "start_date": "2026-02-01",
            "end_date": "2026-02-02",
            "daily_flows": [],
        }
    )
    svc = MagicMock()
    svc.get_projection = AsyncMock(
        return_value=CashflowProjection.model_validate(
            {
                "start_date": "2026-02-01",
                "end_date": "2026-02-02",
                "daily_flows": [],
            }
        )
    )

    from app.api.v1.finance.router import get_service, verify_finance_token

    app.dependency_overrides[get_service] = lambda: svc
    app.dependency_overrides[verify_finance_token] = lambda: "finance-secret"
    try:
        with patch("app.api.v1.finance.router.cashflow_projection_cache", cache):
            response = client.get(
                "/api/v1/finance/cashflow?start_date=2026-02-01&end_date=2026-02-02&refresh=true",
                headers={"X-Finance-Token": "finance-secret"},
            )
    finally:
        app.dependency_overrides.pop(get_service, None)
        app.dependency_overrides.pop(verify_finance_token, None)

    assert response.status_code == 200, response.text
    svc.get_projection.assert_awaited_once()


def test_cashflow_projection_uses_stale_cache_when_today_missing() -> None:
    client = _client()
    cache = _CacheStub(
        snapshot=None,
        latest_snapshot={
            "start_date": "2026-02-01",
            "end_date": "2026-02-02",
            "daily_flows": [],
        },
    )
    svc = MagicMock()
    svc.get_projection = AsyncMock()

    from app.api.v1.finance.router import get_service, verify_finance_token

    app.dependency_overrides[get_service] = lambda: svc
    app.dependency_overrides[verify_finance_token] = lambda: "finance-secret"
    try:
        with patch("app.api.v1.finance.router.cashflow_projection_cache", cache):
            response = client.get(
                "/api/v1/finance/cashflow?start_date=2026-02-01&end_date=2026-02-02",
                headers={"X-Finance-Token": "finance-secret"},
            )
    finally:
        app.dependency_overrides.pop(get_service, None)
        app.dependency_overrides.pop(verify_finance_token, None)

    assert response.status_code == 200, response.text
    svc.get_projection.assert_not_called()


def test_create_manual_entry_invalidates_today_cache() -> None:
    client = _client()
    cache = _CacheStub()
    svc = MagicMock()
    svc.create_entry = MagicMock(
        return_value={
            "id": 1,
            "description": "test",
            "amount": "10.00",
            "currency_code": "CAD",
            "transaction_type": "Payment",
            "transaction_date": "2026-02-09",
            "is_periodic": False,
            "recurrence_frequency": None,
            "recurrence_interval": None,
            "recurrence_count": None,
            "recurrence_end_date": None,
            "created_at": "2026-02-09T00:00:00",
            "updated_at": "2026-02-09T00:00:00",
        }
    )

    from app.api.v1.finance.router import get_service, verify_finance_token

    app.dependency_overrides[get_service] = lambda: svc
    app.dependency_overrides[verify_finance_token] = lambda: "finance-secret"
    try:
        with patch("app.api.v1.finance.router.cashflow_projection_cache", cache):
            response = client.post(
                "/api/v1/finance/cashflow/entries",
                headers={"X-Finance-Token": "finance-secret"},
                json={
                    "description": "test",
                    "amount": "10.00",
                    "currency_code": "CAD",
                    "transaction_type": "Payment",
                    "transaction_date": "2026-02-09",
                    "is_periodic": False,
                },
            )
    finally:
        app.dependency_overrides.pop(get_service, None)
        app.dependency_overrides.pop(verify_finance_token, None)

    assert response.status_code == 201, response.text
    assert len(cache.invalidations) == 1

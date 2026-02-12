import pytest

from app.adapters.erp_client import ERPClient


@pytest.mark.asyncio
async def test_get_job_default_dimensions_encodes_special_chars(monkeypatch):
    client = ERPClient()
    captured = {}

    async def _fake_fetch(resource_path: str, *, fail_on_404: bool = False):
        _ = fail_on_404
        captured["resource"] = resource_path
        return []

    monkeypatch.setattr(client, "_fetch_odata_collection", _fake_fetch)

    await client.get_job_default_dimensions("INVMG60#01")

    resource = captured["resource"]
    assert resource.startswith("DefaultDimensions?%24filter=")
    assert "%23" in resource


@pytest.mark.asyncio
async def test_get_job_encodes_special_chars(monkeypatch):
    client = ERPClient()
    captured = {}

    async def _fake_fetch(resource_path: str, *, fail_on_404: bool = False):
        _ = fail_on_404
        captured["resource"] = resource_path
        return []

    monkeypatch.setattr(client, "_fetch_odata_collection", _fake_fetch)

    await client.get_job("INVMG60#01")

    resource = captured["resource"]
    assert resource.startswith("Jobs?%24filter=")
    assert "%23" in resource

import httpx
import pytest

from app.domain.edi.eleknet.client import ElekNetClient
from app.domain.edi.eleknet.errors import ElekNetTimeoutError


@pytest.mark.asyncio
async def test_post_xpa_retries_once_on_network_error():
    calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        if calls["count"] == 1:
            raise httpx.ConnectError("network down", request=request)
        return httpx.Response(200, text="<xPAResponse><returnCode>S</returnCode></xPAResponse>")

    async_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = ElekNetClient(
        base_url="https://vendor.example.com/eleknet",
        username="user",
        password="pass",
        max_network_retries=1,
        async_client=async_client,
    )

    response_xml = await client.post_xpa("<request />")
    await async_client.aclose()

    assert calls["count"] == 2
    assert "<returnCode>S</returnCode>" in response_xml


@pytest.mark.asyncio
async def test_post_order_timeout_raises_gateway_timeout_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timeout", request=request)

    async_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = ElekNetClient(
        base_url="https://vendor.example.com/eleknet",
        username="user",
        password="pass",
        max_network_retries=1,
        async_client=async_client,
    )

    with pytest.raises(ElekNetTimeoutError):
        await client.post_order("<request />")

    await async_client.aclose()


@pytest.mark.asyncio
async def test_client_uses_specific_xpa_and_order_urls_when_configured():
    seen_urls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_urls.append(str(request.url))
        if request.url.path.lower().endswith("/xpa.aspx"):
            return httpx.Response(200, text="<xPAResponse><returnCode>S</returnCode></xPAResponse>")
        if request.url.path.lower().endswith("/send.aspx"):
            return httpx.Response(200, text="<orderResponse><returnCode>S</returnCode></orderResponse>")
        return httpx.Response(500, text="unexpected")

    async_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = ElekNetClient(
        base_url="https://unused.example.com/base",
        xpa_url="https://vendor.example.com/services/XmlOrder/xPA.aspx",
        order_url="https://vendor.example.com/services/XmlOrder/Send.aspx",
        username="user",
        password="pass",
        max_network_retries=0,
        async_client=async_client,
    )

    xpa_xml = await client.post_xpa("<request />")
    order_xml = await client.post_order("<request />")
    await async_client.aclose()

    assert "<returnCode>S</returnCode>" in xpa_xml
    assert "<returnCode>S</returnCode>" in order_xml
    assert seen_urls[0].endswith("/xPA.aspx")
    assert seen_urls[1].endswith("/Send.aspx")

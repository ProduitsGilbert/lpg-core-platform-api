import pytest
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app
from app.deps import get_db
from app.settings import settings


class DummyResponse:
    def __init__(self, *, status_code: int, content: bytes, headers: dict[str, str] | None = None):
        self.status_code = status_code
        self.content = content
        self.headers = headers or {}
        self.text = content.decode("utf-8", errors="ignore")

    def raise_for_status(self):
        if 400 <= self.status_code:
            raise Exception(f"HTTP {self.status_code}")


class DummyAsyncClient:
    def __init__(self, *args, response: DummyResponse, **kwargs):
        self._response = response
        self.requested_url = None
        self.requested_headers = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, url: str, headers=None):
        self.requested_url = url
        self.requested_headers = headers or {}
        return self._response


@pytest.fixture
def client(monkeypatch):
    settings.file_share_requester_id = "GIRDA01"
    settings.logfire_api_key = None

    async def _verify_database_connection():
        return True

    monkeypatch.setattr("app.main.verify_database_connection", _verify_database_connection)
    monkeypatch.setattr("app.main.dispose_engine", lambda: None)

    app = create_app()
    app.dependency_overrides[get_db] = lambda: object()

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def test_extract_assembly_components_from_item_pdf(client, monkeypatch):
    pdf_bytes = Path("tests/7260012.pdf").read_bytes()
    response = DummyResponse(
        status_code=200,
        content=pdf_bytes,
        headers={
            "Content-Type": "application/pdf",
            "Content-Disposition": 'attachment; filename="7260012.pdf"',
        },
    )

    dummy_client = DummyAsyncClient(response=response)
    monkeypatch.setattr(
        "app.domain.documents.file_share_service.httpx.AsyncClient",
        lambda *args, **kwargs: dummy_client,
    )

    api_response = client.post(
        "/api/v1/ocr/assemblies/components",
        json={"itemNo": "7260012", "revision": "08", "type": "Assembly"},
    )

    assert api_response.status_code == 200, api_response.text
    payload = api_response.json()
    assert payload["itemNo"] == "7260012"
    assert payload["revision"] == "08"
    assert payload["type"] == "Assembly"

    components = payload["components"]
    assert len(components) == 24

    # Full expected BOM list for the sample drawing (rows 3, 4, 23, R1 are intentionally excluded).
    expected = [
        {"itemNo": "7261077", "qty": 1, "position": "1"},
        {"itemNo": "7261125", "qty": 1, "position": "2"},
        {"itemNo": "0615192", "qty": 10, "position": "5"},
        {"itemNo": "0910121", "qty": 10, "position": "6"},
        {"itemNo": "0910116", "qty": 2, "position": "7"},
        {"itemNo": "0670011", "qty": 40, "position": "8"},
        {"itemNo": "3837009", "qty": 16, "position": "9"},
        {"itemNo": "0670041", "qty": 24, "position": "10"},
        {"itemNo": "0816161", "qty": 88, "position": "11"},
        {"itemNo": "0670051", "qty": 64, "position": "12"},
        {"itemNo": "0314504", "qty": 4, "position": "13"},
        {"itemNo": "0852111", "qty": 4, "position": "14"},
        {"itemNo": "0670031", "qty": 2, "position": "15"},
        {"itemNo": "7261026", "qty": 1, "position": "16"},
        {"itemNo": "7261017", "qty": 1, "position": "17"},
        {"itemNo": "7261018", "qty": 1, "position": "18"},
        {"itemNo": "7261195", "qty": 1, "position": "19"},
        {"itemNo": "7340224", "qty": 1, "position": "20"},
        {"itemNo": "8349171", "qty": 1, "position": "21"},
        {"itemNo": "7261108", "qty": 1, "position": "22"},
        {"itemNo": "7261107", "qty": 1, "position": "24"},
        {"itemNo": "0910119", "qty": 8, "position": "25"},
        {"itemNo": "0614531", "qty": 4, "position": "26"},
        {"itemNo": "7340064", "qty": 4, "position": "27"},
    ]

    def _pos(row: dict) -> int:
        return int(row["position"])

    assert sorted(components, key=_pos) == expected

    assert dummy_client.requested_url.endswith("FileShare/GetItemPDFFile(7260012)")
    assert dummy_client.requested_headers["RequesterUserID"] == "GIRDA01"


def test_extract_assembly_components_with_pdf_positions(client, monkeypatch):
    pdf_bytes = Path("tests/7260012.pdf").read_bytes()
    response = DummyResponse(
        status_code=200,
        content=pdf_bytes,
        headers={
            "Content-Type": "application/pdf",
            "Content-Disposition": 'attachment; filename="7260012.pdf"',
        },
    )

    dummy_client = DummyAsyncClient(response=response)
    monkeypatch.setattr(
        "app.domain.documents.file_share_service.httpx.AsyncClient",
        lambda *args, **kwargs: dummy_client,
    )

    api_response = client.post(
        "/api/v1/ocr/assemblies/components",
        json={"itemNo": "7260012", "revision": "08", "type": "Assembly", "includePdfPosition": True},
    )

    assert api_response.status_code == 200, api_response.text
    payload = api_response.json()

    comps = payload["components"]
    # Find a few known positions that should exist on page 1 in this drawing
    by_pos = {c["position"]: c for c in comps}
    for pos in ["1", "2", "10", "21", "27"]:
        assert pos in by_pos
        # best-effort: for this sample drawing these should be locatable as text on page 1
        assert "PdfPosition" in by_pos[pos]
        assert by_pos[pos]["PdfPosition"]["page"] == 1
        assert by_pos[pos]["PdfPosition"]["left"] >= 0
        assert by_pos[pos]["PdfPosition"]["top"] >= 0



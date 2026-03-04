from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient
from pypdf import PdfWriter

from app.api.v1.ocr.documents import router as ocr_documents_router


def _make_minimal_pdf_bytes() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    import io

    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def _make_test_app() -> FastAPI:
    app = FastAPI()
    v1 = APIRouter(prefix="/api/v1")
    v1.include_router(ocr_documents_router)
    app.include_router(v1)
    return app


def test_carrier_statement_rejects_non_pdf_extension():
    client = TestClient(_make_test_app())

    response = client.post(
        "/api/v1/ocr/documents/carrier-statements/extract",
        files={"file": ("statement.txt", b"not-a-pdf", "text/plain")},
        data={"carrier": "purolator"},
    )

    assert response.status_code == 400
    assert response.json()["detail"].lower().startswith("file must be pdf")


def test_carrier_statement_rejects_unsupported_carrier():
    client = TestClient(_make_test_app())
    pdf_bytes = _make_minimal_pdf_bytes()

    response = client.post(
        "/api/v1/ocr/documents/carrier-statements/extract",
        files={"file": ("statement.pdf", pdf_bytes, "application/pdf")},
        data={"carrier": "fedex"},
    )

    assert response.status_code == 400
    assert response.json()["detail"].startswith("Unsupported carrier")


def test_carrier_statement_returns_422_when_ocr_client_disabled(monkeypatch):
    import app.api.v1.ocr.documents as ocr_documents_module

    monkeypatch.setattr(ocr_documents_module.settings, "openai_api_key", None, raising=False)

    client = TestClient(_make_test_app())
    pdf_bytes = _make_minimal_pdf_bytes()

    response = client.post(
        "/api/v1/ocr/documents/carrier-statements/extract",
        files={"file": ("statement.pdf", pdf_bytes, "application/pdf")},
        data={"carrier": "purolator"},
    )

    assert response.status_code == 422
    payload = response.json()
    assert payload["data"]["success"] is False
    assert payload["data"]["error_message"] == "OCR client is not enabled"

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


def test_complex_document_rejects_unsupported_extension():
    client = TestClient(_make_test_app())

    response = client.post(
        "/api/v1/ocr/documents/complex/extract",
        files={"file": ("report.txt", b"not a pdf", "text/plain")},
    )

    assert response.status_code == 400
    assert response.json()["detail"].lower().startswith("file must be pdf")


def test_complex_document_returns_422_when_ocr_client_disabled(monkeypatch):
    import app.api.v1.ocr.documents as ocr_documents_module

    monkeypatch.setattr(ocr_documents_module.settings, "openai_api_key", None, raising=False)

    client = TestClient(_make_test_app())
    pdf_bytes = _make_minimal_pdf_bytes()

    response = client.post(
        "/api/v1/ocr/documents/complex/extract",
        files={"file": ("report.pdf", pdf_bytes, "application/pdf")},
    )

    assert response.status_code == 422
    payload = response.json()
    assert payload["data"]["success"] is False
    assert payload["data"]["error_message"] == "OCR client is not enabled"


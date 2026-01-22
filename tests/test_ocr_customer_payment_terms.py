from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient
from pypdf import PdfWriter

from app.api.v1.ocr.documents import router as ocr_documents_router


def _make_minimal_pdf_bytes() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)  # US Letter size in points
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


def test_customer_payment_terms_rejects_non_pdf_extension():
    client = TestClient(_make_test_app())

    response = client.post(
        "/api/v1/ocr/documents/customer-payment-terms/extract",
        files={"file": ("contract.txt", b"not a pdf", "text/plain")},
    )

    assert response.status_code == 400
    assert response.json()["detail"].lower().startswith("file must be pdf")


def test_customer_payment_terms_returns_422_when_ocr_client_disabled(monkeypatch):
    """
    When OPENAI_API_KEY is not set, the OCR client is disabled and the endpoint should return 422.
    """
    # The application settings may be loaded from .env files; force-disable OCR client for this test.
    import app.api.v1.ocr.documents as ocr_documents_module
    monkeypatch.setattr(ocr_documents_module.settings, "openai_api_key", None, raising=False)

    client = TestClient(_make_test_app())
    pdf_bytes = _make_minimal_pdf_bytes()

    response = client.post(
        "/api/v1/ocr/documents/customer-payment-terms/extract",
        files={"file": ("contract.pdf", pdf_bytes, "application/pdf")},
    )

    assert response.status_code == 422
    payload = response.json()
    assert payload["data"]["success"] is False
    assert payload["data"]["error_message"] == "OCR client is not enabled"



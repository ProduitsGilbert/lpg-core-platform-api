import json

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


def test_custom_document_rejects_invalid_schema_json():
    client = TestClient(_make_test_app())
    pdf_bytes = _make_minimal_pdf_bytes()

    response = client.post(
        "/api/v1/ocr/documents/custom/extract",
        files={"file": ("sample.pdf", pdf_bytes, "application/pdf")},
        data={
            "document_type": "custom_invoice",
            "output_schema": "{invalid-json",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"].startswith("output_schema must be valid JSON")


def test_custom_document_rejects_schema_without_properties():
    client = TestClient(_make_test_app())
    pdf_bytes = _make_minimal_pdf_bytes()

    response = client.post(
        "/api/v1/ocr/documents/custom/extract",
        files={"file": ("sample.pdf", pdf_bytes, "application/pdf")},
        data={
            "document_type": "custom_invoice",
            "output_schema": json.dumps({"type": "object"}),
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"].startswith("Invalid output_schema:")


def test_custom_document_returns_422_when_ocr_client_disabled(monkeypatch):
    import app.api.v1.ocr.documents as ocr_documents_module

    monkeypatch.setattr(ocr_documents_module.settings, "openai_api_key", None, raising=False)

    client = TestClient(_make_test_app())
    pdf_bytes = _make_minimal_pdf_bytes()

    schema = {
        "type": "object",
        "properties": {
            "document_id": {"type": "string", "description": "Document identifier"},
            "total_amount": {"type": "number", "description": "Total amount"},
            "lines": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "line_no": {"type": "integer"},
                        "description": {"type": "string"},
                        "quantity": {"type": "number"},
                    },
                    "required": ["line_no", "description", "quantity"],
                },
            },
        },
        "required": ["document_id", "total_amount"],
    }

    response = client.post(
        "/api/v1/ocr/documents/custom/extract",
        files={"file": ("sample.pdf", pdf_bytes, "application/pdf")},
        data={
            "document_type": "custom_invoice",
            "output_schema": json.dumps(schema),
        },
    )

    assert response.status_code == 422
    payload = response.json()
    assert payload["data"]["success"] is False
    assert payload["data"]["error_message"] == "OCR client is not enabled"

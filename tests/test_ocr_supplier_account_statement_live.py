import os
import re
from pathlib import Path

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient
from pypdf import PdfReader

from app.api.v1.ocr.documents import router as ocr_documents_router


WAJAX_STATEMENT_PATH = Path(__file__).resolve().parents[1] / "docs" / "etat de compte wajax 50446077_0.pdf"


def _make_test_app() -> FastAPI:
    app = FastAPI()
    v1 = APIRouter(prefix="/api/v1")
    v1.include_router(ocr_documents_router)
    app.include_router(v1)
    return app


def _extract_invoice_candidates(pdf_path: Path, limit: int = 3) -> list[str]:
    reader = PdfReader(str(pdf_path))
    pdf_text = "\n".join((p.extract_text() or "") for p in reader.pages)
    # Wajax invoice numbers are 13-digit values like 2025120161804.
    candidates = []
    for match in re.findall(r"\b20\d{11}\b", pdf_text):
        if match not in candidates:
            candidates.append(match)
        if len(candidates) >= limit:
            break
    return candidates


@pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="Requires OPENAI_API_KEY for live OCR extraction")
def test_supplier_account_statement_wajax_live_extracts_invoice_dates_and_amounts():
    if not WAJAX_STATEMENT_PATH.exists():
        pytest.skip(f"Missing Wajax statement PDF at {WAJAX_STATEMENT_PATH}")

    invoice_candidates = _extract_invoice_candidates(WAJAX_STATEMENT_PATH)
    assert len(invoice_candidates) >= 3, "Expected at least three invoice numbers from the Wajax statement PDF"

    client = TestClient(_make_test_app())
    pdf_bytes = WAJAX_STATEMENT_PATH.read_bytes()

    response = client.post(
        "/api/v1/ocr/documents/supplier-account-statements/extract",
        files={"file": (WAJAX_STATEMENT_PATH.name, pdf_bytes, "application/pdf")},
        data={
            "additional_instructions": (
                "Return every invoice line with invoice number, invoice date, and amount due. "
                "Ensure invoice numbers are preserved as strings and dates are ISO (YYYY-MM-DD)."
            )
        },
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["data"]["success"] is True, payload

    extracted = payload["data"]["extracted_data"]
    transactions = extracted.get("transactions", [])
    assert len(transactions) >= 10, "Expected a meaningful list of transactions from the statement"

    def _has_invoice_with_date_and_amount(invoice_number: str) -> bool:
        for txn in transactions:
            reference = str(txn.get("reference") or "")
            description = str(txn.get("description") or "")
            if invoice_number == reference or invoice_number in description:
                has_date = bool(txn.get("transaction_date"))
                has_amount = txn.get("debit") is not None or txn.get("credit") is not None
                if has_date and has_amount:
                    return True
        return False

    for invoice_number in invoice_candidates:
        assert _has_invoice_with_date_and_amount(
            invoice_number
        ), f"Missing invoice/date/amount for {invoice_number}"



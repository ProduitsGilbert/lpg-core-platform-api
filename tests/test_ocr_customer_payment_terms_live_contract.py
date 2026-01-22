import os
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient
from pypdf import PdfReader

from app.api.v1.ocr.documents import router as ocr_documents_router


FIXTURES_DIR = Path(__file__).parent / "fixtures" / "ocr"


def _resolve_contract_fixture() -> Path | None:
    """
    Pick the most recent Claude Howard Lumber Outfeed Bridge contract fixture.

    We support rev changes (rev 2, rev 3, etc.) so local tests don't break when the
    revision number in the filename changes.
    """
    candidates = sorted(FIXTURES_DIR.glob("Claude Howard Lumber.OUTFEED BRIDGE rev *.pdf"))
    return candidates[-1] if candidates else None


def _make_test_app() -> FastAPI:
    app = FastAPI()
    v1 = APIRouter(prefix="/api/v1")
    v1.include_router(ocr_documents_router)
    app.include_router(v1)
    return app


@pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="Requires OPENAI_API_KEY for live OCR extraction")
def test_customer_payment_terms_contract_pdf_live_extracts_expected_values():
    fixture_path = _resolve_contract_fixture()
    if not fixture_path:
        pytest.skip(
            f"Missing local PDF fixture in {FIXTURES_DIR} "
            f"(expected something like 'Claude Howard Lumber.OUTFEED BRIDGE rev 3.pdf'; file is gitignored)."
        )

    client = TestClient(_make_test_app())
    pdf_bytes = fixture_path.read_bytes()

    # Build expected values directly from the PDF text so the test stays valid across revisions.
    reader = PdfReader(str(fixture_path))
    pdf_text = "\n".join((p.extract_text() or "") for p in reader.pages[:10])

    # Expected currency (document uses "Total ($USD)")
    expected_currency = "USD" if "($USD)" in pdf_text.replace(" ", "") or "USD" in pdf_text else None

    # Expected total amount from the "Total ($USD)" line
    expected_total: Decimal | None = None
    for line in pdf_text.splitlines():
        if "Total ($USD)" in line.replace(" ", "") or "Total($USD)" in line.replace(" ", ""):
            # Common formats: "$236 680,00Total ($USD)" or "$203 800.00 Total ($USD)"
            raw = line.split("Total", 1)[0]
            raw = raw.replace("$", "").strip()
            raw = raw.replace(" ", "").replace(",", ".")
            try:
                expected_total = Decimal(raw)
            except Exception:
                expected_total = None
            break

    assert expected_total is not None, f"Could not locate Total ($USD) in PDF text for {fixture_path.name}"

    response = client.post(
        "/api/v1/ocr/documents/customer-payment-terms/extract",
        files={"file": (fixture_path.name, pdf_bytes, "application/pdf")},
        data={
            "additional_instructions": (
                "Extract the contract TOTAL amount and the Terms/payment schedule section. "
                "Return milestones with the original timing text and percent values."
            )
        },
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["data"]["success"] is True, payload

    extracted = payload["data"]["extracted_data"]

    # Total amount
    total = Decimal(str(extracted["total_amount"]).replace(" ", "").replace(",", ""))
    assert total == expected_total
    if expected_currency:
        assert (extracted.get("currency") or "").upper() == expected_currency

    # Terms/milestones
    milestones = extracted["milestones"]
    assert len(milestones) == 4

    percents = [Decimal(str(m.get("percent"))) for m in milestones]
    assert all(p == Decimal("25") for p in percents)
    assert sum(percents) == Decimal("100")

    terms_text = (extracted.get("payment_terms_text") or "").lower()
    assert "upon receiving purchase order" in terms_text
    assert "30 days after receiving purchase order" in terms_text
    assert "delivery date" in terms_text
    assert "start-up date" in terms_text



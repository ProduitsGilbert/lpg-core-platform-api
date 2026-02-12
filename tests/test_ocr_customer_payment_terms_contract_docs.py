import os
import re
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient
from pypdf import PdfReader

from app.api.v1.ocr.documents import router as ocr_documents_router


DOCS_CONTRACT_PATH = Path(__file__).resolve().parents[1] / "docs" / "CONTRACT- South Pine -  Gilbert S-Series Planer.pdf"


def _make_test_app() -> FastAPI:
    app = FastAPI()
    v1 = APIRouter(prefix="/api/v1")
    v1.include_router(ocr_documents_router)
    app.include_router(v1)
    return app


def _parse_total_and_currency(pdf_text: str) -> tuple[Decimal | None, str | None]:
    for line in pdf_text.splitlines():
        match = re.search(r"Total\s*\(\$?([A-Z]{3})\)\s*\$?([0-9][0-9\s.,]+)", line)
        if match:
            currency = match.group(1)
            raw_amount = match.group(2).replace(" ", "").replace(",", ".")
            try:
                return Decimal(raw_amount), currency
            except Exception:
                return None, currency
    return None, None


def _parse_terms_lines(pdf_text: str) -> list[str]:
    lines = [line.strip() for line in pdf_text.splitlines()]
    idx = None
    for i, line in enumerate(lines):
        if line.lower() == "terms:":
            idx = i
            break
    if idx is None:
        return []

    terms: list[str] = []
    for line in lines[idx + 1 :]:
        if not line:
            break
        if line.lower().startswith("not included"):
            break
        if "%" in line:
            terms.append(line)
    return terms


def _parse_percents(terms: list[str]) -> list[Decimal]:
    percents: list[Decimal] = []
    for line in terms:
        match = re.search(r"([0-9]+(?:[.,][0-9]+)?)\s*%", line)
        if match:
            percents.append(Decimal(match.group(1).replace(",", ".")))
    return percents


@pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="Requires OPENAI_API_KEY for live OCR extraction")
def test_customer_payment_terms_contract_docs_extracts_table():
    if not DOCS_CONTRACT_PATH.exists():
        pytest.skip(f"Missing contract PDF at {DOCS_CONTRACT_PATH}")

    client = TestClient(_make_test_app())
    pdf_bytes = DOCS_CONTRACT_PATH.read_bytes()

    reader = PdfReader(str(DOCS_CONTRACT_PATH))
    pdf_text = "\n".join((p.extract_text() or "") for p in reader.pages)

    expected_total, expected_currency = _parse_total_and_currency(pdf_text)
    terms_lines = _parse_terms_lines(pdf_text)
    expected_percents = _parse_percents(terms_lines)

    assert expected_total is not None, "Could not locate Total ($XXX) in PDF text"
    assert expected_percents, "Could not locate payment terms percentages in PDF text"

    response = client.post(
        "/api/v1/ocr/documents/customer-payment-terms/extract",
        files={"file": (DOCS_CONTRACT_PATH.name, pdf_bytes, "application/pdf")},
        data={
            "additional_instructions": (
                "Extract the contract TOTAL amount and the payment schedule. "
                "Return milestones with the original timing text and percent values."
            )
        },
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["data"]["success"] is True, payload

    extracted = payload["data"]["extracted_data"]

    total = Decimal(str(extracted["total_amount"]).replace(" ", "").replace(",", ""))
    assert total == expected_total
    if expected_currency:
        assert (extracted.get("currency") or "").upper() == expected_currency

    milestones = extracted["milestones"]
    assert len(milestones) == len(expected_percents)

    percents = [Decimal(str(m.get("percent"))) for m in milestones]
    assert percents == expected_percents
    assert sum(percents) == Decimal("100")

    terms_text = (extracted.get("payment_terms_text") or "").lower()
    for line in terms_lines:
        fragment = line.split("%", 1)[0].strip().lower()
        if fragment:
            assert fragment in terms_text

    table = extracted.get("payment_terms_table")
    assert table, "payment_terms_table missing in extracted data"
    assert len(table) == len(expected_percents)

    for row, percent in zip(table, expected_percents):
        row_percent = Decimal(str(row.get("percent")))
        assert row_percent == percent.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        expected_amount = (expected_total * percent / Decimal("100")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        row_amount = Decimal(str(row.get("calculated_amount")))
        assert row_amount == expected_amount
        if expected_currency:
            assert (row.get("currency") or "").upper() == expected_currency

    table_markdown = extracted.get("payment_terms_table_markdown") or ""
    assert "| Description | Percent | Calculated Amount | Currency |" in table_markdown

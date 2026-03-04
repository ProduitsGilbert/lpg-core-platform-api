from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

import app.api.v1.ocr.documents as ocr_documents_module
from app.api.v1.ocr.documents import router as ocr_documents_router
from app.domain.ocr.models import (
    CarrierStatementListResponse,
    CarrierStatementSaveRequest,
    CarrierStatementSaveResponse,
    CarrierStatementStoredRecord,
    CarrierStatementUpdateRequest,
)


class _InMemoryCarrierStatementRepository:
    def __init__(self) -> None:
        self.is_configured = True
        self._records: list[CarrierStatementStoredRecord] = []
        self._next_id = 1

    def save_extraction(self, request: CarrierStatementSaveRequest) -> CarrierStatementSaveResponse:
        inserted = 0
        updated = 0
        changed: list[CarrierStatementStoredRecord] = []
        now = datetime.utcnow()
        for shipment in request.extracted_data.shipments:
            existing = next(
                (
                    rec
                    for rec in self._records
                    if rec.carrier == request.carrier
                    and rec.invoice_number == request.extracted_data.invoice_number
                    and rec.shipment_date == shipment.shipment_date
                    and rec.tracking_number == shipment.tracking_number
                ),
                None,
            )

            payload = {
                "carrier": request.carrier,
                "workflow_type": request.workflow_type,
                "status": request.status,
                "matched": request.matched,
                "statement_filename": request.statement_filename,
                "account_number": request.extracted_data.account_number,
                "invoice_number": request.extracted_data.invoice_number,
                "invoice_date": request.extracted_data.invoice_date,
                "due_date": request.extracted_data.due_date,
                "currency": request.extracted_data.currency,
                "amount_due": request.extracted_data.amount_due,
                "shipment_date": shipment.shipment_date,
                "tracking_number": shipment.tracking_number,
                "shipped_from_address": shipment.shipped_from_address,
                "shipped_to_address": shipment.shipped_to_address,
                "piece_count": shipment.piece_count,
                "billed_weight": shipment.billed_weight,
                "billed_weight_unit": shipment.billed_weight_unit,
                "service_description": shipment.service_description,
                "charges": shipment.charges,
                "total_charges": shipment.total_charges,
                "ref_1": shipment.ref_1,
                "ref_2": shipment.ref_2,
                "manifest_number": shipment.manifest_number,
                "billing_note": shipment.billing_note,
                "source_page": shipment.source_page,
                "shipment_payload": shipment.model_dump(mode="json"),
                "updated_at": now,
            }

            if existing:
                record = existing.model_copy(update=payload)
                self._records = [record if rec.id == existing.id else rec for rec in self._records]
                updated += 1
                changed.append(record)
            else:
                record = CarrierStatementStoredRecord(
                    id=self._next_id,
                    created_at=now,
                    **payload,
                )
                self._next_id += 1
                self._records.append(record)
                inserted += 1
                changed.append(record)

        return CarrierStatementSaveResponse(
            inserted_count=inserted,
            updated_count=updated,
            records=changed,
        )

    def list_records(
        self,
        *,
        carrier: str | None = None,
        status: str | None = None,
        matched: bool | None = None,
        workflow_type: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> CarrierStatementListResponse:
        rows = self._records
        if carrier:
            rows = [row for row in rows if row.carrier == carrier]
        if status:
            rows = [row for row in rows if row.status == status]
        if matched is not None:
            rows = [row for row in rows if row.matched is matched]
        if workflow_type:
            rows = [row for row in rows if row.workflow_type == workflow_type]

        total = len(rows)
        paged = rows[offset : offset + limit]
        return CarrierStatementListResponse(total=total, items=paged)

    def update_record(
        self,
        record_id: int,
        updates: CarrierStatementUpdateRequest,
    ) -> CarrierStatementStoredRecord | None:
        for index, record in enumerate(self._records):
            if record.id != record_id:
                continue
            update_payload = updates.model_dump(exclude_unset=True)
            update_payload["updated_at"] = datetime.utcnow()
            updated_record = record.model_copy(update=update_payload)
            self._records[index] = updated_record
            return updated_record
        return None


def _make_test_app(repository: _InMemoryCarrierStatementRepository) -> FastAPI:
    app = FastAPI()
    v1 = APIRouter(prefix="/api/v1")
    v1.include_router(ocr_documents_router)
    app.include_router(v1)
    app.dependency_overrides[ocr_documents_module.get_carrier_statement_repository] = lambda: repository
    return app


def _sample_save_payload() -> dict:
    return {
        "carrier": "purolator",
        "workflow_type": "sales",
        "status": "new",
        "matched": False,
        "statement_filename": "Puro 515176910.pdf",
        "extracted_data": {
            "carrier": "purolator",
            "account_number": "5054208",
            "invoice_number": "515176910",
            "invoice_date": "2025-07-19",
            "due_date": "2025-08-02",
            "currency": "CAD",
            "amount_due": "2251.06",
            "processed_pages": 10,
            "shipments": [
                {
                    "shipment_date": "2025-07-02",
                    "tracking_number": "49996570740",
                    "shipped_from_address": "Les Produits Gilbert Inc\n1840 Marcotte BOUL\nROBERVAL\nQC\nG8H 2P2",
                    "shipped_to_address": "GEORGIA PACIFIC WOO\n1 GP LANE\nGURDON\nAR\n71743 US",
                    "piece_count": 1,
                    "billed_weight": "25",
                    "billed_weight_unit": "LB",
                    "service_description": "Purolator Routier E.-U.",
                    "charges": [
                        {"description": "Purolator Routier E.-U.", "amount": "47.70"},
                        {"description": "Supplement de carburant", "amount": "10.49"},
                    ],
                    "total_charges": "58.19",
                    "ref_1": None,
                    "ref_2": "GI20877",
                    "manifest_number": "49996570740",
                    "billing_note": "Prepaye",
                    "source_page": 2,
                }
            ],
            "notes": None,
        },
    }


def test_save_carrier_statement_records():
    repository = _InMemoryCarrierStatementRepository()
    client = TestClient(_make_test_app(repository))

    response = client.post(
        "/api/v1/ocr/documents/carrier-statements/records",
        json=_sample_save_payload(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["inserted_count"] == 1
    assert payload["data"]["updated_count"] == 0
    assert payload["data"]["records"][0]["tracking_number"] == "49996570740"


def test_save_carrier_statement_records_normalizes_weight_with_unit():
    repository = _InMemoryCarrierStatementRepository()
    client = TestClient(_make_test_app(repository))
    payload = _sample_save_payload()
    payload["extracted_data"]["shipments"][0]["billed_weight"] = "25 LB"
    payload["extracted_data"]["shipments"][0].pop("billed_weight_unit", None)

    response = client.post(
        "/api/v1/ocr/documents/carrier-statements/records",
        json=payload,
    )

    assert response.status_code == 200
    saved = response.json()["data"]["records"][0]
    assert saved["billed_weight"] == "25"
    assert saved["billed_weight_unit"] == "LB"


def test_list_carrier_statement_records_filters_unmatched():
    repository = _InMemoryCarrierStatementRepository()
    repository.save_extraction(CarrierStatementSaveRequest.model_validate(_sample_save_payload()))
    client = TestClient(_make_test_app(repository))

    response = client.get(
        "/api/v1/ocr/documents/carrier-statements/records",
        params={"carrier": "purolator", "matched": "false", "workflow_type": "sales"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["status"] == "new"
    assert payload["items"][0]["matched"] is False


def test_update_carrier_statement_record():
    repository = _InMemoryCarrierStatementRepository()
    save_result = repository.save_extraction(CarrierStatementSaveRequest.model_validate(_sample_save_payload()))
    saved_id = save_result.records[0].id
    client = TestClient(_make_test_app(repository))

    response = client.patch(
        f"/api/v1/ocr/documents/carrier-statements/records/{saved_id}",
        json={"status": "matched_po", "matched": True, "workflow_type": "purchase"},
    )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["id"] == saved_id
    assert payload["status"] == "matched_po"
    assert payload["matched"] is True
    assert payload["workflow_type"] == "purchase"

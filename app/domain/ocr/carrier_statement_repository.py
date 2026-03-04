from __future__ import annotations

import json
import logging
import re
import unicodedata
from typing import Optional

from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from app.domain.ocr.models import (
    CarrierStatementCharge,
    CarrierStatementListResponse,
    CarrierStatementSaveRequest,
    CarrierStatementSaveResponse,
    CarrierStatementStoredRecord,
    CarrierStatementUpdateRequest,
)
from app.errors import DatabaseError
from app.integrations.cedule_repository import get_cedule_engine

logger = logging.getLogger(__name__)


class CarrierStatementRepository:
    """Persistence repository for extracted carrier statement shipment records."""

    _TABLE = "[Cedule].[dbo].[30_COMPTABILITÉ ET FINANCES_AP_Transport_Carrier_Statement_Transaction]"
    _GILBERT_ADDRESS_TOKENS = (
        "LES PRODUITS GILBERT",
        "1840",
        "MARCOTTE",
        "ROBERVAL",
        "G8H 2P2",
    )
    _SALES_ORDER_REF_PATTERNS = (
        re.compile(r"\bGI\s*\d{3,}\b"),
        re.compile(r"\bR\s*\d{3,}\b"),
    )

    def __init__(self, engine: Optional[Engine] = None) -> None:
        self._engine = engine or get_cedule_engine()

    @property
    def is_configured(self) -> bool:
        return self._engine is not None

    def save_extraction(self, request: CarrierStatementSaveRequest) -> CarrierStatementSaveResponse:
        if not self._engine:
            raise DatabaseError("Cedule database is not configured")

        carrier = (request.carrier or request.extracted_data.carrier or "").strip().lower()
        if not carrier:
            raise ValueError("carrier is required")

        inserted_count = 0
        updated_count = 0
        records: list[CarrierStatementStoredRecord] = []
        statement = request.extracted_data

        merge_stmt = text(
            f"""
            MERGE {self._TABLE} AS target
            USING (
                SELECT
                    :carrier AS carrier,
                    :invoice_number AS invoice_number,
                    :shipment_date AS shipment_date,
                    :tracking_number AS tracking_number
            ) AS source
            ON target.carrier = source.carrier
               AND ISNULL(target.invoice_number, '') = ISNULL(source.invoice_number, '')
               AND target.shipment_date = source.shipment_date
               AND target.tracking_number = source.tracking_number
            WHEN MATCHED THEN UPDATE SET
                workflow_type = :workflow_type,
                status = :status,
                matched = :matched,
                statement_filename = :statement_filename,
                account_number = :account_number,
                invoice_date = :invoice_date,
                due_date = :due_date,
                currency = :currency,
                amount_due = :amount_due,
                shipped_from_address = :shipped_from_address,
                shipped_to_address = :shipped_to_address,
                piece_count = :piece_count,
                billed_weight = :billed_weight,
                billed_weight_unit = :billed_weight_unit,
                service_description = :service_description,
                charges_json = :charges_json,
                subtotal_before_tax = :subtotal_before_tax,
                tax_lines_json = :tax_lines_json,
                tax_total = :tax_total,
                tax_tps = :tax_tps,
                tax_tvq = :tax_tvq,
                total_charges = :total_charges,
                ref_1 = :ref_1,
                ref_2 = :ref_2,
                manifest_number = :manifest_number,
                billing_note = :billing_note,
                source_page = :source_page,
                shipment_payload_json = :shipment_payload_json,
                updated_at = SYSUTCDATETIME()
            WHEN NOT MATCHED THEN INSERT (
                carrier,
                workflow_type,
                status,
                matched,
                statement_filename,
                account_number,
                invoice_number,
                invoice_date,
                due_date,
                currency,
                amount_due,
                shipment_date,
                tracking_number,
                shipped_from_address,
                shipped_to_address,
                piece_count,
                billed_weight,
                billed_weight_unit,
                service_description,
                charges_json,
                subtotal_before_tax,
                tax_lines_json,
                tax_total,
                tax_tps,
                tax_tvq,
                total_charges,
                ref_1,
                ref_2,
                manifest_number,
                billing_note,
                source_page,
                shipment_payload_json,
                created_at,
                updated_at
            ) VALUES (
                :carrier,
                :workflow_type,
                :status,
                :matched,
                :statement_filename,
                :account_number,
                :invoice_number,
                :invoice_date,
                :due_date,
                :currency,
                :amount_due,
                :shipment_date,
                :tracking_number,
                :shipped_from_address,
                :shipped_to_address,
                :piece_count,
                :billed_weight,
                :billed_weight_unit,
                :service_description,
                :charges_json,
                :subtotal_before_tax,
                :tax_lines_json,
                :tax_total,
                :tax_tps,
                :tax_tvq,
                :total_charges,
                :ref_1,
                :ref_2,
                :manifest_number,
                :billing_note,
                :source_page,
                :shipment_payload_json,
                SYSUTCDATETIME(),
                SYSUTCDATETIME()
            )
            OUTPUT $action AS merge_action, inserted.id AS id;
            """
        )

        try:
            with self._engine.begin() as connection:
                for shipment in statement.shipments:
                    inferred_workflow_type = self.infer_workflow_type(
                        shipped_from_address=shipment.shipped_from_address,
                        shipped_to_address=shipment.shipped_to_address,
                        ref_1=shipment.ref_1,
                        ref_2=shipment.ref_2,
                        fallback=request.workflow_type,
                    )
                    charges_json = json.dumps(
                        [charge.model_dump(mode="json") for charge in shipment.charges],
                        ensure_ascii=False,
                    )
                    tax_lines_json = json.dumps(
                        [charge.model_dump(mode="json") for charge in shipment.tax_lines],
                        ensure_ascii=False,
                    )
                    shipment_payload_json = json.dumps(shipment.model_dump(mode="json"), ensure_ascii=False)
                    merge_row = connection.execute(
                        merge_stmt,
                        {
                            "carrier": carrier,
                            "workflow_type": inferred_workflow_type,
                            "status": request.status,
                            "matched": 1 if request.matched else 0,
                            "statement_filename": request.statement_filename,
                            "account_number": statement.account_number,
                            "invoice_number": statement.invoice_number,
                            "invoice_date": statement.invoice_date,
                            "due_date": statement.due_date,
                            "currency": statement.currency,
                            "amount_due": statement.amount_due,
                            "shipment_date": shipment.shipment_date,
                            "tracking_number": shipment.tracking_number,
                            "shipped_from_address": shipment.shipped_from_address,
                            "shipped_to_address": shipment.shipped_to_address,
                            "piece_count": shipment.piece_count,
                            "billed_weight": shipment.billed_weight,
                            "billed_weight_unit": shipment.billed_weight_unit,
                            "service_description": shipment.service_description,
                            "charges_json": charges_json,
                            "subtotal_before_tax": shipment.subtotal_before_tax,
                            "tax_lines_json": tax_lines_json,
                            "tax_total": shipment.tax_total,
                            "tax_tps": shipment.tax_tps,
                            "tax_tvq": shipment.tax_tvq,
                            "total_charges": shipment.total_charges,
                            "ref_1": shipment.ref_1,
                            "ref_2": shipment.ref_2,
                            "manifest_number": shipment.manifest_number,
                            "billing_note": shipment.billing_note,
                            "source_page": shipment.source_page,
                            "shipment_payload_json": shipment_payload_json,
                        },
                    ).mappings().first()

                    if not merge_row or not merge_row.get("id"):
                        continue

                    action = str(merge_row.get("merge_action") or "").upper()
                    if action == "INSERT":
                        inserted_count += 1
                    else:
                        updated_count += 1

                    record = connection.execute(
                        text(f"SELECT * FROM {self._TABLE} WHERE id = :id"),
                        {"id": int(merge_row["id"])},
                    ).mappings().first()
                    if record:
                        records.append(self._map_row(record))

            return CarrierStatementSaveResponse(
                inserted_count=inserted_count,
                updated_count=updated_count,
                records=records,
            )
        except SQLAlchemyError as exc:
            logger.error("Failed to save carrier statement extraction", exc_info=exc)
            raise DatabaseError("Unable to save carrier statement extraction") from exc

    @classmethod
    def infer_workflow_type(
        cls,
        *,
        shipped_from_address: Optional[str],
        shipped_to_address: Optional[str],
        ref_1: Optional[str],
        ref_2: Optional[str],
        fallback: str = "sales",
    ) -> str:
        """
        Infer workflow type from shipment addresses and references.

        Rules:
        - Purchase when destination address is Gilbert HQ in Roberval.
        - Sales when origin address is Gilbert HQ and ref_1/ref_2 contains a sales order-like reference.
        - Fallback to caller-provided workflow type when no rule matches.
        """
        fallback_value = (fallback or "sales").strip().lower()
        if fallback_value not in {"purchase", "sales"}:
            fallback_value = "sales"

        to_gilbert = cls._is_gilbert_hq_address(shipped_to_address)
        from_gilbert = cls._is_gilbert_hq_address(shipped_from_address)
        has_sales_reference = cls._has_sales_order_reference(ref_1, ref_2)

        if to_gilbert:
            return "purchase"
        if from_gilbert and has_sales_reference:
            return "sales"
        return fallback_value

    @classmethod
    def _is_gilbert_hq_address(cls, address: Optional[str]) -> bool:
        normalized = cls._normalize_text(address)
        if not normalized:
            return False
        return all(token in normalized for token in cls._GILBERT_ADDRESS_TOKENS)

    @classmethod
    def _has_sales_order_reference(cls, ref_1: Optional[str], ref_2: Optional[str]) -> bool:
        refs = [cls._normalize_text(ref_1), cls._normalize_text(ref_2)]
        for ref in refs:
            if not ref:
                continue
            if any(pattern.search(ref) for pattern in cls._SALES_ORDER_REF_PATTERNS):
                return True
        return False

    @staticmethod
    def _normalize_text(value: Optional[str]) -> str:
        if not value:
            return ""
        normalized = unicodedata.normalize("NFKD", str(value))
        ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
        upper_text = ascii_text.upper()
        upper_text = re.sub(r"[^A-Z0-9]+", " ", upper_text)
        return re.sub(r"\s+", " ", upper_text).strip()

    def list_records(
        self,
        *,
        carrier: Optional[str] = None,
        status: Optional[str] = None,
        matched: Optional[bool] = None,
        workflow_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> CarrierStatementListResponse:
        if not self._engine:
            raise DatabaseError("Cedule database is not configured")

        where_clauses: list[str] = []
        params: dict[str, object] = {"limit": limit, "offset": offset}

        if carrier:
            where_clauses.append("carrier = :carrier")
            params["carrier"] = carrier.strip().lower()
        if status:
            where_clauses.append("status = :status")
            params["status"] = status.strip()
        if matched is not None:
            where_clauses.append("matched = :matched")
            params["matched"] = 1 if matched else 0
        if workflow_type:
            where_clauses.append("workflow_type = :workflow_type")
            params["workflow_type"] = workflow_type.strip().lower()

        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        count_sql = text(f"SELECT COUNT(1) AS total FROM {self._TABLE} {where_sql}")
        list_sql = text(
            f"""
            SELECT *
            FROM {self._TABLE}
            {where_sql}
            ORDER BY shipment_date DESC, id DESC
            OFFSET :offset ROWS FETCH NEXT :limit ROWS ONLY
            """
        )

        try:
            with self._engine.connect() as connection:
                total = int(connection.execute(count_sql, params).scalar() or 0)
                rows = connection.execute(list_sql, params).mappings().all()
            return CarrierStatementListResponse(
                total=total,
                items=[self._map_row(row) for row in rows],
            )
        except SQLAlchemyError as exc:
            logger.error("Failed to list carrier statement records", exc_info=exc)
            raise DatabaseError("Unable to list carrier statement records") from exc

    def update_record(self, record_id: int, updates: CarrierStatementUpdateRequest) -> Optional[CarrierStatementStoredRecord]:
        if not self._engine:
            raise DatabaseError("Cedule database is not configured")

        update_data = updates.model_dump(exclude_unset=True)
        if not update_data:
            return self.get_record(record_id)

        params: dict[str, object] = {"id": record_id}
        set_parts: list[str] = []
        for key, value in update_data.items():
            if key == "matched":
                params[key] = 1 if value else 0
            elif key == "workflow_type" and isinstance(value, str):
                params[key] = value.lower()
            else:
                params[key] = value
            set_parts.append(f"{key} = :{key}")

        set_parts.append("updated_at = SYSUTCDATETIME()")
        update_sql = text(f"UPDATE {self._TABLE} SET {', '.join(set_parts)} WHERE id = :id")

        try:
            with self._engine.begin() as connection:
                result = connection.execute(update_sql, params)
                if result.rowcount == 0:
                    return None
                row = connection.execute(
                    text(f"SELECT * FROM {self._TABLE} WHERE id = :id"),
                    {"id": record_id},
                ).mappings().first()
            return self._map_row(row) if row else None
        except SQLAlchemyError as exc:
            logger.error("Failed to update carrier statement record %s", record_id, exc_info=exc)
            raise DatabaseError(f"Unable to update carrier statement record {record_id}") from exc

    def get_record(self, record_id: int) -> Optional[CarrierStatementStoredRecord]:
        if not self._engine:
            raise DatabaseError("Cedule database is not configured")
        try:
            with self._engine.connect() as connection:
                row = connection.execute(
                    text(f"SELECT * FROM {self._TABLE} WHERE id = :id"),
                    {"id": record_id},
                ).mappings().first()
            return self._map_row(row) if row else None
        except SQLAlchemyError as exc:
            logger.error("Failed to fetch carrier statement record %s", record_id, exc_info=exc)
            raise DatabaseError(f"Unable to fetch carrier statement record {record_id}") from exc

    @staticmethod
    def _map_row(row: dict) -> CarrierStatementStoredRecord:
        charges_payload = row.get("charges_json")
        tax_lines_payload = row.get("tax_lines_json")
        shipment_payload = row.get("shipment_payload_json")

        charges: list[CarrierStatementCharge] = []
        tax_lines: list[CarrierStatementCharge] = []
        if isinstance(charges_payload, str) and charges_payload.strip():
            try:
                parsed = json.loads(charges_payload)
                if isinstance(parsed, list):
                    charges = [CarrierStatementCharge.model_validate(item) for item in parsed]
            except (json.JSONDecodeError, TypeError, ValueError):
                charges = []

        if isinstance(tax_lines_payload, str) and tax_lines_payload.strip():
            try:
                parsed_tax_lines = json.loads(tax_lines_payload)
                if isinstance(parsed_tax_lines, list):
                    tax_lines = [CarrierStatementCharge.model_validate(item) for item in parsed_tax_lines]
            except (json.JSONDecodeError, TypeError, ValueError):
                tax_lines = []

        shipment_payload_data = None
        if isinstance(shipment_payload, str) and shipment_payload.strip():
            try:
                candidate = json.loads(shipment_payload)
                if isinstance(candidate, dict):
                    shipment_payload_data = candidate
            except json.JSONDecodeError:
                shipment_payload_data = None

        return CarrierStatementStoredRecord(
            id=int(row["id"]),
            carrier=str(row.get("carrier") or ""),
            workflow_type=str(row.get("workflow_type") or "sales").lower(),  # type: ignore[arg-type]
            status=str(row.get("status") or ""),
            matched=bool(row.get("matched")),
            statement_filename=row.get("statement_filename"),
            account_number=row.get("account_number"),
            invoice_number=row.get("invoice_number"),
            invoice_date=row.get("invoice_date"),
            due_date=row.get("due_date"),
            currency=str(row.get("currency") or "CAD"),
            amount_due=row.get("amount_due"),
            sales_invoice_number=row.get("sales_invoice_number"),
            sales_transport_charge_line_amount=row.get("sales_transport_charge_line_amount"),
            sales_total_amount_incl_vat=row.get("sales_total_amount_incl_vat"),
            shipment_date=row.get("shipment_date"),
            tracking_number=str(row.get("tracking_number") or ""),
            shipped_from_address=str(row.get("shipped_from_address") or ""),
            shipped_to_address=str(row.get("shipped_to_address") or ""),
            piece_count=row.get("piece_count"),
            billed_weight=row.get("billed_weight"),
            billed_weight_unit=row.get("billed_weight_unit"),
            service_description=row.get("service_description"),
            charges=charges,
            subtotal_before_tax=row.get("subtotal_before_tax"),
            tax_lines=tax_lines,
            tax_total=row.get("tax_total"),
            tax_tps=row.get("tax_tps"),
            tax_tvq=row.get("tax_tvq"),
            total_charges=row.get("total_charges"),
            ref_1=row.get("ref_1"),
            ref_2=row.get("ref_2"),
            manifest_number=row.get("manifest_number"),
            billing_note=row.get("billing_note"),
            source_page=row.get("source_page"),
            shipment_payload=shipment_payload_data,
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at"),
        )

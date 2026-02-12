from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID, uuid4
import logging
import json

from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from app.domain.ventes_sous_traitance.models import (
    CustomerSummary,
    JobStatusResponse,
    QuoteCreateRequest,
    QuoteStatusUpdateRequest,
    QuoteSummary,
    QuoteUpdateRequest,
    RoutingCreateRequest,
    RoutingResponse,
    RoutingStepCreateRequest,
    RoutingStepResponse,
    RoutingStepUpdateRequest,
    RoutingUpdateRequest,
)
from app.errors import DatabaseError
from app.integrations.cedule_repository import get_cedule_engine

logger = logging.getLogger(__name__)


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


class CeduleVentesSousTraitanceRepository:
    def __init__(self, engine: Optional[Engine] = None) -> None:
        self._engine = engine or get_cedule_engine()

    @property
    def is_configured(self) -> bool:
        return self._engine is not None

    def list_customers(self, *, search: Optional[str], limit: int = 200) -> list[CustomerSummary]:
        if not self._engine:
            raise DatabaseError("Cedule database not configured")
        safe_limit = max(1, min(limit, 1000))
        filters: list[str] = []
        params: dict[str, Any] = {"limit": safe_limit}
        if search:
            filters.append("([name] LIKE :search OR [email] LIKE :search OR [phone] LIKE :search)")
            params["search"] = f"%{search.strip()}%"
        where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""

        stmt = text(
            f"""
            SELECT TOP (:limit)
                [customer_id], [name], [email], [phone], [created_at]
            FROM [Cedule].[dbo].[40_VENTES_SOUSTRAITANCE_customers]
            {where_clause}
            ORDER BY [name] ASC, [created_at] DESC
            """
        )
        try:
            with self._engine.connect() as conn:
                rows = conn.execute(stmt, params).mappings().all()
        except SQLAlchemyError as exc:
            logger.error("Failed to list subcontracting customers", exc_info=exc)
            raise DatabaseError("Unable to list customers") from exc
        return [self._to_customer(row) for row in rows]

    def list_quotes(self, *, status: Optional[str], customer_id: Optional[UUID]) -> list[QuoteSummary]:
        if not self._engine:
            raise DatabaseError("Cedule database not configured")

        filters: list[str] = []
        params: dict[str, Any] = {}
        if status:
            filters.append("[status] = :status")
            params["status"] = status
        if customer_id:
            filters.append("[customer_id] = :customer_id")
            params["customer_id"] = str(customer_id)
        where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""

        stmt = text(
            f"""
            SELECT
                [quote_id], [quote_number], [customer_id], [status], [currency], [due_date],
                [sent_at], [closed_at], [loss_reason_code], [loss_reason_note], [notes],
                [created_at], [updated_at]
            FROM [Cedule].[dbo].[40_VENTES_SOUSTRAITANCE_quotes]
            {where_clause}
            ORDER BY [created_at] DESC
            """
        )
        try:
            with self._engine.connect() as conn:
                rows = conn.execute(stmt, params).mappings().all()
        except SQLAlchemyError as exc:
            logger.error("Failed to list subcontracting quotes", exc_info=exc)
            raise DatabaseError("Unable to list quotes") from exc
        return [self._to_quote(row) for row in rows]

    def get_quote(self, quote_id: UUID) -> Optional[QuoteSummary]:
        if not self._engine:
            raise DatabaseError("Cedule database not configured")
        stmt = text(
            """
            SELECT
                [quote_id], [quote_number], [customer_id], [status], [currency], [due_date],
                [sent_at], [closed_at], [loss_reason_code], [loss_reason_note], [notes],
                [created_at], [updated_at]
            FROM [Cedule].[dbo].[40_VENTES_SOUSTRAITANCE_quotes]
            WHERE [quote_id] = :quote_id
            """
        )
        try:
            with self._engine.connect() as conn:
                row = conn.execute(stmt, {"quote_id": str(quote_id)}).mappings().first()
        except SQLAlchemyError as exc:
            logger.error("Failed to get subcontracting quote", exc_info=exc)
            raise DatabaseError("Unable to fetch quote") from exc
        return self._to_quote(row) if row else None

    def create_quote(self, payload: QuoteCreateRequest) -> QuoteSummary:
        if not self._engine:
            raise DatabaseError("Cedule database not configured")
        quote_id = uuid4()
        stmt = text(
            """
            INSERT INTO [Cedule].[dbo].[40_VENTES_SOUSTRAITANCE_quotes]
            (
                [quote_id], [quote_number], [customer_id], [status], [currency], [due_date], [notes]
            )
            VALUES
            (
                :quote_id, :quote_number, :customer_id, :status, :currency, :due_date, :notes
            )
            """
        )
        try:
            with self._engine.begin() as conn:
                self._ensure_customer_exists(conn, payload.customer_id, payload.notes)
                conn.execute(
                    stmt,
                    {
                        "quote_id": str(quote_id),
                        "quote_number": payload.quote_number,
                        "customer_id": str(payload.customer_id),
                        "status": payload.status,
                        "currency": payload.currency,
                        "due_date": payload.due_date,
                        "notes": payload.notes,
                    },
                )
            created = self.get_quote(quote_id)
            if not created:
                raise DatabaseError("Quote created but not found afterwards")
            return created
        except SQLAlchemyError as exc:
            logger.error("Failed to create subcontracting quote", exc_info=exc)
            raise DatabaseError("Unable to create quote") from exc

    def update_quote(self, quote_id: UUID, payload: QuoteUpdateRequest) -> Optional[QuoteSummary]:
        if not self._engine:
            raise DatabaseError("Cedule database not configured")
        updates: list[str] = []
        params: dict[str, Any] = {"quote_id": str(quote_id)}

        for field in ("quote_number", "status", "currency", "due_date", "notes"):
            value = getattr(payload, field)
            if value is not None:
                updates.append(f"[{field}] = :{field}")
                params[field] = value
        if payload.customer_id is not None:
            updates.append("[customer_id] = :customer_id")
            params["customer_id"] = str(payload.customer_id)

        if not updates:
            return self.get_quote(quote_id)
        updates.append("[updated_at] = SYSUTCDATETIME()")

        stmt = text(
            f"""
            UPDATE [Cedule].[dbo].[40_VENTES_SOUSTRAITANCE_quotes]
            SET {', '.join(updates)}
            WHERE [quote_id] = :quote_id
            """
        )
        try:
            with self._engine.begin() as conn:
                if payload.customer_id is not None:
                    self._ensure_customer_exists(conn, payload.customer_id, payload.notes)
                result = conn.execute(stmt, params)
                if result.rowcount == 0:
                    return None
            return self.get_quote(quote_id)
        except SQLAlchemyError as exc:
            logger.error("Failed to update subcontracting quote", exc_info=exc)
            raise DatabaseError("Unable to update quote") from exc

    def _ensure_customer_exists(self, conn, customer_id: UUID, notes: Optional[str]) -> None:
        """
        Ensure FK customer exists for quote operations.
        Creates a placeholder customer row when a new external UUID is provided.
        """
        customer_name = self._derive_customer_name(customer_id, notes)
        stmt = text(
            """
            INSERT INTO [Cedule].[dbo].[40_VENTES_SOUSTRAITANCE_customers]
            (
                [customer_id], [name]
            )
            SELECT
                :customer_id, :name
            WHERE NOT EXISTS
            (
                SELECT 1
                FROM [Cedule].[dbo].[40_VENTES_SOUSTRAITANCE_customers]
                WHERE [customer_id] = :customer_id
            )
            """
        )
        conn.execute(
            stmt,
            {
                "customer_id": str(customer_id),
                "name": customer_name,
            },
        )

    @staticmethod
    def _derive_customer_name(customer_id: UUID, notes: Optional[str]) -> str:
        fallback = f"Customer {customer_id}"
        if not notes:
            return fallback
        for raw_line in notes.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            lowered = line.lower()
            if lowered.startswith("customer:"):
                name = line.split(":", 1)[1].strip()
                return name[:200] if name else fallback
        return fallback

    def update_quote_status(self, quote_id: UUID, payload: QuoteStatusUpdateRequest) -> Optional[QuoteSummary]:
        if not self._engine:
            raise DatabaseError("Cedule database not configured")
        closed_at = date.today() if payload.status in {"won", "lost", "cancelled"} else None
        stmt = text(
            """
            UPDATE [Cedule].[dbo].[40_VENTES_SOUSTRAITANCE_quotes]
            SET
                [status] = :status,
                [loss_reason_code] = :loss_reason_code,
                [loss_reason_note] = :loss_reason_note,
                [sent_at] = CASE WHEN :status = 'sent' THEN COALESCE([sent_at], SYSUTCDATETIME()) ELSE [sent_at] END,
                [closed_at] = CASE WHEN :closed_at IS NULL THEN [closed_at] ELSE SYSUTCDATETIME() END,
                [updated_at] = SYSUTCDATETIME()
            WHERE [quote_id] = :quote_id
            """
        )
        try:
            with self._engine.begin() as conn:
                result = conn.execute(
                    stmt,
                    {
                        "quote_id": str(quote_id),
                        "status": payload.status,
                        "loss_reason_code": payload.loss_reason_code,
                        "loss_reason_note": payload.loss_reason_note,
                        "closed_at": closed_at,
                    },
                )
                if result.rowcount == 0:
                    return None
            return self.get_quote(quote_id)
        except SQLAlchemyError as exc:
            logger.error("Failed to update quote status", exc_info=exc)
            raise DatabaseError("Unable to update quote status") from exc

    def delete_quote(self, quote_id: UUID) -> bool:
        if not self._engine:
            raise DatabaseError("Cedule database not configured")
        stmt = text(
            """
            DELETE FROM [Cedule].[dbo].[40_VENTES_SOUSTRAITANCE_quotes]
            WHERE [quote_id] = :quote_id
            """
        )
        try:
            with self._engine.begin() as conn:
                result = conn.execute(stmt, {"quote_id": str(quote_id)})
                return result.rowcount > 0
        except SQLAlchemyError as exc:
            logger.error("Failed to delete quote", exc_info=exc)
            raise DatabaseError("Unable to delete quote") from exc

    def list_routings(self, part_id: UUID) -> list[RoutingResponse]:
        if not self._engine:
            raise DatabaseError("Cedule database not configured")
        stmt = text(
            """
            SELECT [routing_id], [part_id], [scenario_name], [created_by], [selected], [rationale], [created_at]
            FROM [Cedule].[dbo].[40_VENTES_SOUSTRAITANCE_part_routings]
            WHERE [part_id] = :part_id
            ORDER BY [created_at] DESC
            """
        )
        try:
            with self._engine.connect() as conn:
                rows = conn.execute(stmt, {"part_id": str(part_id)}).mappings().all()
        except SQLAlchemyError as exc:
            logger.error("Failed to list routings", exc_info=exc)
            raise DatabaseError("Unable to list routings") from exc
        return [self._to_routing(row) for row in rows]

    def get_routing(self, routing_id: UUID) -> Optional[RoutingResponse]:
        if not self._engine:
            raise DatabaseError("Cedule database not configured")
        stmt = text(
            """
            SELECT [routing_id], [part_id], [scenario_name], [created_by], [selected], [rationale], [created_at]
            FROM [Cedule].[dbo].[40_VENTES_SOUSTRAITANCE_part_routings]
            WHERE [routing_id] = :routing_id
            """
        )
        try:
            with self._engine.connect() as conn:
                row = conn.execute(stmt, {"routing_id": str(routing_id)}).mappings().first()
        except SQLAlchemyError as exc:
            logger.error("Failed to get routing", exc_info=exc)
            raise DatabaseError("Unable to fetch routing") from exc
        return self._to_routing(row) if row else None

    def create_routing(self, part_id: UUID, payload: RoutingCreateRequest) -> RoutingResponse:
        if not self._engine:
            raise DatabaseError("Cedule database not configured")
        routing_id = uuid4()
        reset_selected_stmt = text(
            """
            UPDATE [Cedule].[dbo].[40_VENTES_SOUSTRAITANCE_part_routings]
            SET [selected] = 0
            WHERE [part_id] = :part_id
            """
        )
        insert_stmt = text(
            """
            INSERT INTO [Cedule].[dbo].[40_VENTES_SOUSTRAITANCE_part_routings]
            ([routing_id], [part_id], [scenario_name], [created_by], [selected], [rationale])
            VALUES (:routing_id, :part_id, :scenario_name, :created_by, :selected, :rationale)
            """
        )
        try:
            with self._engine.begin() as conn:
                if payload.selected:
                    conn.execute(reset_selected_stmt, {"part_id": str(part_id)})
                conn.execute(
                    insert_stmt,
                    {
                        "routing_id": str(routing_id),
                        "part_id": str(part_id),
                        "scenario_name": payload.scenario_name,
                        "created_by": payload.created_by,
                        "selected": payload.selected,
                        "rationale": payload.rationale,
                    },
                )
            created = self.get_routing(routing_id)
            if not created:
                raise DatabaseError("Routing created but not found afterwards")
            return created
        except SQLAlchemyError as exc:
            logger.error("Failed to create routing", exc_info=exc)
            raise DatabaseError("Unable to create routing") from exc

    def update_routing(self, routing_id: UUID, payload: RoutingUpdateRequest) -> Optional[RoutingResponse]:
        if not self._engine:
            raise DatabaseError("Cedule database not configured")
        current = self.get_routing(routing_id)
        if not current:
            return None

        updates: list[str] = []
        params: dict[str, Any] = {"routing_id": str(routing_id)}
        for field in ("scenario_name", "created_by", "rationale"):
            value = getattr(payload, field)
            if value is not None:
                updates.append(f"[{field}] = :{field}")
                params[field] = value

        update_stmt = None
        if updates:
            update_stmt = text(
                f"""
                UPDATE [Cedule].[dbo].[40_VENTES_SOUSTRAITANCE_part_routings]
                SET {', '.join(updates)}
                WHERE [routing_id] = :routing_id
                """
            )

        reset_selected_stmt = text(
            """
            UPDATE [Cedule].[dbo].[40_VENTES_SOUSTRAITANCE_part_routings]
            SET [selected] = 0
            WHERE [part_id] = :part_id
            """
        )
        set_selected_stmt = text(
            """
            UPDATE [Cedule].[dbo].[40_VENTES_SOUSTRAITANCE_part_routings]
            SET [selected] = :selected
            WHERE [routing_id] = :routing_id
            """
        )

        try:
            with self._engine.begin() as conn:
                if update_stmt:
                    conn.execute(update_stmt, params)
                if payload.selected is not None:
                    if payload.selected:
                        conn.execute(reset_selected_stmt, {"part_id": str(current.part_id)})
                    conn.execute(
                        set_selected_stmt,
                        {"routing_id": str(routing_id), "selected": payload.selected},
                    )
            return self.get_routing(routing_id)
        except SQLAlchemyError as exc:
            logger.error("Failed to update routing", exc_info=exc)
            raise DatabaseError("Unable to update routing") from exc

    def delete_routing(self, routing_id: UUID) -> bool:
        if not self._engine:
            raise DatabaseError("Cedule database not configured")
        stmt = text(
            """
            DELETE FROM [Cedule].[dbo].[40_VENTES_SOUSTRAITANCE_part_routings]
            WHERE [routing_id] = :routing_id
            """
        )
        try:
            with self._engine.begin() as conn:
                result = conn.execute(stmt, {"routing_id": str(routing_id)})
                return result.rowcount > 0
        except SQLAlchemyError as exc:
            logger.error("Failed to delete routing", exc_info=exc)
            raise DatabaseError("Unable to delete routing") from exc

    def list_routing_steps(self, routing_id: UUID) -> list[RoutingStepResponse]:
        if not self._engine:
            raise DatabaseError("Cedule database not configured")
        stmt = text(
            """
            SELECT
                [step_id], [routing_id], [step_no], [operation_id], [machine_group_id], [description],
                [setup_time_min], [cycle_time_min], [handling_time_min], [inspection_time_min],
                [qty_basis], [user_override], [estimator_note], [time_confidence], [source]
            FROM [Cedule].[dbo].[40_VENTES_SOUSTRAITANCE_routing_steps]
            WHERE [routing_id] = :routing_id
            ORDER BY [step_no]
            """
        )
        try:
            with self._engine.connect() as conn:
                rows = conn.execute(stmt, {"routing_id": str(routing_id)}).mappings().all()
        except SQLAlchemyError as exc:
            logger.error("Failed to list routing steps", exc_info=exc)
            raise DatabaseError("Unable to list routing steps") from exc
        return [self._to_step(row) for row in rows]

    def create_routing_step(self, routing_id: UUID, payload: RoutingStepCreateRequest) -> RoutingStepResponse:
        if not self._engine:
            raise DatabaseError("Cedule database not configured")
        step_id = uuid4()
        step_no = payload.step_no
        max_step_stmt = text(
            """
            SELECT ISNULL(MAX([step_no]), 0)
            FROM [Cedule].[dbo].[40_VENTES_SOUSTRAITANCE_routing_steps]
            WHERE [routing_id] = :routing_id
            """
        )
        insert_stmt = text(
            """
            INSERT INTO [Cedule].[dbo].[40_VENTES_SOUSTRAITANCE_routing_steps]
            (
                [step_id], [routing_id], [step_no], [operation_id], [machine_group_id], [description],
                [setup_time_min], [cycle_time_min], [handling_time_min], [inspection_time_min],
                [qty_basis], [user_override], [estimator_note], [time_confidence], [source]
            )
            VALUES
            (
                :step_id, :routing_id, :step_no, :operation_id, :machine_group_id, :description,
                :setup_time_min, :cycle_time_min, :handling_time_min, :inspection_time_min,
                :qty_basis, 0, :estimator_note, :time_confidence, :source
            )
            """
        )
        try:
            with self._engine.begin() as conn:
                if step_no is None:
                    current_max = conn.execute(max_step_stmt, {"routing_id": str(routing_id)}).scalar()
                    step_no = int(current_max or 0) + 1
                conn.execute(
                    insert_stmt,
                    {
                        "step_id": str(step_id),
                        "routing_id": str(routing_id),
                        "step_no": step_no,
                        "operation_id": str(payload.operation_id),
                        "machine_group_id": payload.machine_group_id,
                        "description": payload.description,
                        "setup_time_min": payload.setup_time_min,
                        "cycle_time_min": payload.cycle_time_min,
                        "handling_time_min": payload.handling_time_min,
                        "inspection_time_min": payload.inspection_time_min,
                        "qty_basis": payload.qty_basis,
                        "estimator_note": payload.estimator_note,
                        "time_confidence": payload.time_confidence,
                        "source": payload.source,
                    },
                )
            created = self.get_routing_step(step_id)
            if not created:
                raise DatabaseError("Routing step created but not found afterwards")
            return created
        except SQLAlchemyError as exc:
            logger.error("Failed to create routing step", exc_info=exc)
            raise DatabaseError("Unable to create routing step") from exc

    def get_routing_step(self, step_id: UUID) -> Optional[RoutingStepResponse]:
        if not self._engine:
            raise DatabaseError("Cedule database not configured")
        stmt = text(
            """
            SELECT
                [step_id], [routing_id], [step_no], [operation_id], [machine_group_id], [description],
                [setup_time_min], [cycle_time_min], [handling_time_min], [inspection_time_min],
                [qty_basis], [user_override], [estimator_note], [time_confidence], [source]
            FROM [Cedule].[dbo].[40_VENTES_SOUSTRAITANCE_routing_steps]
            WHERE [step_id] = :step_id
            """
        )
        try:
            with self._engine.connect() as conn:
                row = conn.execute(stmt, {"step_id": str(step_id)}).mappings().first()
        except SQLAlchemyError as exc:
            logger.error("Failed to get routing step", exc_info=exc)
            raise DatabaseError("Unable to fetch routing step") from exc
        return self._to_step(row) if row else None

    def update_routing_step(self, step_id: UUID, payload: RoutingStepUpdateRequest) -> Optional[RoutingStepResponse]:
        if not self._engine:
            raise DatabaseError("Cedule database not configured")
        updates: list[str] = []
        params: dict[str, Any] = {"step_id": str(step_id)}

        for field in (
            "machine_group_id",
            "description",
            "setup_time_min",
            "cycle_time_min",
            "handling_time_min",
            "inspection_time_min",
            "qty_basis",
            "estimator_note",
            "time_confidence",
            "source",
            "user_override",
        ):
            value = getattr(payload, field)
            if value is not None:
                updates.append(f"[{field}] = :{field}")
                params[field] = value

        if not updates:
            return self.get_routing_step(step_id)

        stmt = text(
            f"""
            UPDATE [Cedule].[dbo].[40_VENTES_SOUSTRAITANCE_routing_steps]
            SET {', '.join(updates)}
            WHERE [step_id] = :step_id
            """
        )
        try:
            with self._engine.begin() as conn:
                result = conn.execute(stmt, params)
                if result.rowcount == 0:
                    return None
            return self.get_routing_step(step_id)
        except SQLAlchemyError as exc:
            logger.error("Failed to update routing step", exc_info=exc)
            raise DatabaseError("Unable to update routing step") from exc

    def delete_routing_step(self, step_id: UUID) -> bool:
        if not self._engine:
            raise DatabaseError("Cedule database not configured")
        stmt = text(
            """
            DELETE FROM [Cedule].[dbo].[40_VENTES_SOUSTRAITANCE_routing_steps]
            WHERE [step_id] = :step_id
            """
        )
        try:
            with self._engine.begin() as conn:
                result = conn.execute(stmt, {"step_id": str(step_id)})
                return result.rowcount > 0
        except SQLAlchemyError as exc:
            logger.error("Failed to delete routing step", exc_info=exc)
            raise DatabaseError("Unable to delete routing step") from exc

    def get_quote_source_text(self, quote_id: UUID) -> str:
        if not self._engine:
            raise DatabaseError("Cedule database not configured")
        stmt = text(
            """
            SELECT p.[extracted_text]
            FROM [Cedule].[dbo].[40_VENTES_SOUSTRAITANCE_quote_files] f
            LEFT JOIN [Cedule].[dbo].[40_VENTES_SOUSTRAITANCE_quote_file_pages] p
              ON p.[file_id] = f.[file_id]
            WHERE f.[quote_id] = :quote_id
            ORDER BY f.[uploaded_at], p.[page_no]
            """
        )
        quote_stmt = text(
            """
            SELECT [notes]
            FROM [Cedule].[dbo].[40_VENTES_SOUSTRAITANCE_quotes]
            WHERE [quote_id] = :quote_id
            """
        )
        try:
            chunks: list[str] = []
            with self._engine.connect() as conn:
                rows = conn.execute(stmt, {"quote_id": str(quote_id)}).mappings().all()
                for row in rows:
                    extracted = row.get("extracted_text")
                    if extracted:
                        chunks.append(str(extracted))
                if not chunks:
                    quote_row = conn.execute(quote_stmt, {"quote_id": str(quote_id)}).mappings().first()
                    if quote_row and quote_row.get("notes"):
                        chunks.append(str(quote_row.get("notes")))
            return "\n\n".join(chunks).strip()
        except SQLAlchemyError as exc:
            logger.error("Failed to load quote source text", exc_info=exc)
            raise DatabaseError("Unable to load quote source text") from exc

    def create_analysis_run(self, quote_id: UUID, *, model_name: str, stage: str = "routing") -> UUID:
        if not self._engine:
            raise DatabaseError("Cedule database not configured")
        run_id = uuid4()
        stmt = text(
            """
            INSERT INTO [Cedule].[dbo].[40_VENTES_SOUSTRAITANCE_llm_runs]
            (
                [run_id], [quote_id], [stage], [model_name], [input_json], [status]
            )
            VALUES
            (
                :run_id, :quote_id, :stage, :model_name, :input_json, 'ok'
            )
            """
        )
        try:
            with self._engine.begin() as conn:
                conn.execute(
                    stmt,
                    {
                        "run_id": str(run_id),
                        "quote_id": str(quote_id),
                        "stage": stage,
                        "model_name": model_name,
                        "input_json": "{}",
                    },
                )
            return run_id
        except SQLAlchemyError as exc:
            logger.error("Failed to create analysis run", exc_info=exc)
            raise DatabaseError("Unable to create analysis run") from exc

    def complete_analysis_run(self, run_id: UUID, output: dict[str, Any]) -> None:
        if not self._engine:
            raise DatabaseError("Cedule database not configured")
        stmt = text(
            """
            UPDATE [Cedule].[dbo].[40_VENTES_SOUSTRAITANCE_llm_runs]
            SET [output_json] = :output_json, [ended_at] = SYSUTCDATETIME(), [status] = 'ok'
            WHERE [run_id] = :run_id
            """
        )
        try:
            with self._engine.begin() as conn:
                conn.execute(stmt, {"run_id": str(run_id), "output_json": json.dumps(output, ensure_ascii=True)})
        except SQLAlchemyError as exc:
            logger.error("Failed to complete analysis run", exc_info=exc)
            raise DatabaseError("Unable to complete analysis run") from exc

    def fail_analysis_run(self, run_id: UUID, error_text: str) -> None:
        if not self._engine:
            raise DatabaseError("Cedule database not configured")
        stmt = text(
            """
            UPDATE [Cedule].[dbo].[40_VENTES_SOUSTRAITANCE_llm_runs]
            SET [error_text] = :error_text, [ended_at] = SYSUTCDATETIME(), [status] = 'error'
            WHERE [run_id] = :run_id
            """
        )
        try:
            with self._engine.begin() as conn:
                conn.execute(stmt, {"run_id": str(run_id), "error_text": error_text[:4000]})
        except SQLAlchemyError as exc:
            logger.error("Failed to mark analysis run as failed", exc_info=exc)
            raise DatabaseError("Unable to update failed analysis run") from exc

    def upsert_part_from_analysis(self, quote_id: UUID, metadata: dict[str, Any], classification: dict[str, Any], complexity: dict[str, Any]) -> UUID:
        if not self._engine:
            raise DatabaseError("Cedule database not configured")
        find_stmt = text(
            """
            SELECT TOP 1 [part_id]
            FROM [Cedule].[dbo].[40_VENTES_SOUSTRAITANCE_quote_parts]
            WHERE [quote_id] = :quote_id
            ORDER BY [created_at]
            """
        )
        update_stmt = text(
            """
            UPDATE [Cedule].[dbo].[40_VENTES_SOUSTRAITANCE_quote_parts]
            SET
                [customer_part_number] = :customer_part_number,
                [internal_part_number] = :internal_part_number,
                [quantity] = :quantity,
                [material] = :material,
                [thickness_mm] = :thickness_mm,
                [weight_kg] = :weight_kg,
                [envelope_x_mm] = :envelope_x_mm,
                [envelope_y_mm] = :envelope_y_mm,
                [envelope_z_mm] = :envelope_z_mm,
                [shape] = :shape,
                [complexity_score] = :complexity_score,
                [updated_at] = SYSUTCDATETIME()
            WHERE [part_id] = :part_id
            """
        )
        insert_stmt = text(
            """
            INSERT INTO [Cedule].[dbo].[40_VENTES_SOUSTRAITANCE_quote_parts]
            (
                [part_id], [quote_id], [customer_part_number], [internal_part_number], [quantity], [material],
                [thickness_mm], [weight_kg], [envelope_x_mm], [envelope_y_mm], [envelope_z_mm], [shape], [complexity_score]
            )
            VALUES
            (
                :part_id, :quote_id, :customer_part_number, :internal_part_number, :quantity, :material,
                :thickness_mm, :weight_kg, :envelope_x_mm, :envelope_y_mm, :envelope_z_mm, :shape, :complexity_score
            )
            """
        )

        envelope = classification.get("overall_envelope_mm") or {}
        params = {
            "quote_id": str(quote_id),
            "customer_part_number": metadata.get("customer_part_number"),
            "internal_part_number": metadata.get("internal_part_number"),
            "quantity": _safe_int(metadata.get("quantity_requested"), default=1),
            "material": metadata.get("material_spec"),
            "thickness_mm": metadata.get("thickness_mm"),
            "weight_kg": classification.get("weight_estimate_kg"),
            "envelope_x_mm": envelope.get("x"),
            "envelope_y_mm": envelope.get("y"),
            "envelope_z_mm": envelope.get("z"),
            "shape": str(classification.get("shape_class") or "unknown"),
            "complexity_score": complexity.get("complexity_score"),
        }

        try:
            with self._engine.begin() as conn:
                existing = conn.execute(find_stmt, {"quote_id": str(quote_id)}).scalar()
                if existing:
                    conn.execute(update_stmt, {"part_id": str(existing), **params})
                    return UUID(str(existing))
                new_part_id = uuid4()
                conn.execute(insert_stmt, {"part_id": str(new_part_id), **params})
                return new_part_id
        except SQLAlchemyError as exc:
            logger.error("Failed to upsert quote part from analysis", exc_info=exc)
            raise DatabaseError("Unable to upsert quote part") from exc

    def save_part_extraction(self, part_id: UUID, *, model_name: str, prompt_version: str, payload: dict[str, Any], confidence: float | None) -> None:
        if not self._engine:
            raise DatabaseError("Cedule database not configured")
        extraction_id = uuid4()
        stmt = text(
            """
            INSERT INTO [Cedule].[dbo].[40_VENTES_SOUSTRAITANCE_part_extractions]
            (
                [extraction_id], [part_id], [model_name], [prompt_version], [extracted_json], [confidence]
            )
            VALUES
            (
                :extraction_id, :part_id, :model_name, :prompt_version, :extracted_json, :confidence
            )
            """
        )
        try:
            with self._engine.begin() as conn:
                conn.execute(
                    stmt,
                    {
                        "extraction_id": str(extraction_id),
                        "part_id": str(part_id),
                        "model_name": model_name,
                        "prompt_version": prompt_version,
                        "extracted_json": json.dumps(payload, ensure_ascii=True),
                        "confidence": confidence,
                    },
                )
        except SQLAlchemyError as exc:
            logger.error("Failed to save part extraction", exc_info=exc)
            raise DatabaseError("Unable to save part extraction") from exc

    def ensure_operation_catalog_entry(self, operation_code: str) -> UUID:
        if not self._engine:
            raise DatabaseError("Cedule database not configured")
        normalized = (operation_code or "OP_GENERIC").strip().upper()[:50]
        select_stmt = text(
            """
            SELECT [operation_id]
            FROM [Cedule].[dbo].[40_VENTES_SOUSTRAITANCE_operation_catalog]
            WHERE [code] = :code
            """
        )
        insert_stmt = text(
            """
            INSERT INTO [Cedule].[dbo].[40_VENTES_SOUSTRAITANCE_operation_catalog]
            ([operation_id], [code], [name], [default_unit])
            VALUES
            (:operation_id, :code, :name, 'min')
            """
        )
        try:
            with self._engine.begin() as conn:
                existing = conn.execute(select_stmt, {"code": normalized}).scalar()
                if existing:
                    return UUID(str(existing))
                operation_id = uuid4()
                conn.execute(
                    insert_stmt,
                    {
                        "operation_id": str(operation_id),
                        "code": normalized,
                        "name": normalized.replace("_", " ").title(),
                    },
                )
                return operation_id
        except SQLAlchemyError as exc:
            logger.error("Failed to ensure operation catalog entry", exc_info=exc)
            raise DatabaseError("Unable to ensure operation catalog entry") from exc

    def save_generated_routings(self, part_id: UUID, scenarios_payload: dict[str, Any]) -> list[RoutingResponse]:
        scenarios = scenarios_payload.get("scenarios") if isinstance(scenarios_payload, dict) else None
        if not isinstance(scenarios, list):
            return []

        created: list[RoutingResponse] = []
        for index, scenario in enumerate(scenarios[:3]):
            if not isinstance(scenario, dict):
                continue
            routing = self.create_routing(
                part_id,
                RoutingCreateRequest(
                    scenario_name=str(scenario.get("scenario_name") or f"Scenario {index + 1}")[:200],
                    created_by="llm",
                    selected=index == 0,
                    rationale=str(scenario.get("rationale") or "")[:4000] or None,
                ),
            )
            steps = scenario.get("steps") or []
            if not isinstance(steps, list):
                steps = []
            for step_index, step in enumerate(steps):
                if not isinstance(step, dict):
                    continue
                op_code = str(step.get("operation_code") or f"OP_{step_index + 1}")
                operation_id = self.ensure_operation_catalog_entry(op_code)
                self.create_routing_step(
                    routing.routing_id,
                    RoutingStepCreateRequest(
                        step_no=step_index + 1,
                        operation_id=operation_id,
                        machine_group_id=step.get("machine_group_id"),
                        description=step.get("description"),
                        setup_time_min=Decimal(str(step.get("setup_time_min") or "0")),
                        cycle_time_min=Decimal(str(step.get("cycle_time_min") or "0")),
                        handling_time_min=Decimal(str(step.get("handling_time_min") or "0")),
                        inspection_time_min=Decimal(str(step.get("inspection_time_min") or "0")),
                        qty_basis=1,
                        estimator_note=None,
                        time_confidence=Decimal(str(step.get("time_confidence") or "0")) if step.get("time_confidence") is not None else None,
                        source="llm",
                    ),
                )
            created.append(routing)
        return created

    def start_analysis(self, quote_id: UUID) -> UUID:
        if not self._engine:
            raise DatabaseError("Cedule database not configured")
        # Backward-compatible fallback used by older service code paths.
        return self.create_analysis_run(quote_id, model_name="manual-trigger")

    def get_job(self, job_id: UUID) -> Optional[JobStatusResponse]:
        if not self._engine:
            raise DatabaseError("Cedule database not configured")
        stmt = text(
            """
            SELECT [run_id], [stage], [status], [started_at], [ended_at], [error_text], [output_json]
            FROM [Cedule].[dbo].[40_VENTES_SOUSTRAITANCE_llm_runs]
            WHERE [run_id] = :run_id
            """
        )
        try:
            with self._engine.connect() as conn:
                row = conn.execute(stmt, {"run_id": str(job_id)}).mappings().first()
        except SQLAlchemyError as exc:
            logger.error("Failed to fetch analysis job", exc_info=exc)
            raise DatabaseError("Unable to fetch job status") from exc
        if not row:
            return None
        status = str(row.get("status") or "ok")
        progress = 1.0 if row.get("ended_at") else 0.5
        if status == "error":
            progress = 1.0
        return JobStatusResponse(
            job_id=UUID(str(row.get("run_id"))),
            status=status,
            stage=str(row.get("stage") or "routing"),
            progress=progress,
            started_at=row.get("started_at"),
            ended_at=row.get("ended_at"),
            error_text=row.get("error_text"),
            output_json=row.get("output_json"),
        )

    def _to_quote(self, row: dict[str, Any]) -> QuoteSummary:
        return QuoteSummary(
            quote_id=UUID(str(row.get("quote_id"))),
            quote_number=row.get("quote_number"),
            customer_id=UUID(str(row.get("customer_id"))),
            status=row.get("status"),
            currency=str(row.get("currency") or "CAD"),
            due_date=row.get("due_date"),
            sent_at=row.get("sent_at"),
            closed_at=row.get("closed_at"),
            loss_reason_code=row.get("loss_reason_code"),
            loss_reason_note=row.get("loss_reason_note"),
            notes=row.get("notes"),
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at"),
        )

    def _to_customer(self, row: dict[str, Any]) -> CustomerSummary:
        return CustomerSummary(
            customer_id=UUID(str(row.get("customer_id"))),
            name=str(row.get("name") or ""),
            email=row.get("email"),
            phone=row.get("phone"),
            created_at=row.get("created_at"),
        )

    def _to_routing(self, row: dict[str, Any]) -> RoutingResponse:
        return RoutingResponse(
            routing_id=UUID(str(row.get("routing_id"))),
            part_id=UUID(str(row.get("part_id"))),
            scenario_name=str(row.get("scenario_name") or ""),
            created_by=row.get("created_by"),
            selected=bool(row.get("selected")),
            rationale=row.get("rationale"),
            created_at=row.get("created_at"),
        )

    def _to_step(self, row: dict[str, Any]) -> RoutingStepResponse:
        return RoutingStepResponse(
            step_id=UUID(str(row.get("step_id"))),
            routing_id=UUID(str(row.get("routing_id"))),
            step_no=int(row.get("step_no") or 0),
            operation_id=UUID(str(row.get("operation_id"))),
            machine_group_id=row.get("machine_group_id"),
            description=row.get("description"),
            setup_time_min=Decimal(str(row.get("setup_time_min") or "0")),
            cycle_time_min=Decimal(str(row.get("cycle_time_min") or "0")),
            handling_time_min=Decimal(str(row.get("handling_time_min") or "0")),
            inspection_time_min=Decimal(str(row.get("inspection_time_min") or "0")),
            qty_basis=int(row.get("qty_basis") or 1),
            user_override=bool(row.get("user_override")),
            estimator_note=row.get("estimator_note"),
            time_confidence=Decimal(str(row["time_confidence"])) if row.get("time_confidence") is not None else None,
            source=row.get("source") or "llm",
        )

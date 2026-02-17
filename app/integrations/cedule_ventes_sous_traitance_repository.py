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
    CustomerCreateRequest,
    CustomerSummary,
    CustomerUpdateRequest,
    JobStatusResponse,
    MachineCapabilityCatalogItem,
    MachineCapabilityInput,
    MachineCapabilityOption,
    MachineCapabilityOptionCreateRequest,
    MachineCapabilityOptionEntry,
    MachineCapabilityOptionUpdateRequest,
    MachineCapabilityResponse,
    MachineCreateRequest,
    MachineGroupCreateRequest,
    MachineGroupSummary,
    MachineGroupUpdateRequest,
    MachineResponse,
    MachineUpdateRequest,
    PartFeatureCreateRequest,
    PartFeatureResponse,
    PartFeatureSetResponse,
    PartFeatureSetUpsertRequest,
    PartFeatureUpdateRequest,
    QuotePartSummary,
    QuotePartUpdateRequest,
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


def _safe_float(value: Any, default: float | None = None) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _clean_json_string(value: str) -> str:
    # Keep common whitespace controls; escape other control chars as literal unicode escapes.
    chars: list[str] = []
    for ch in value:
        code = ord(ch)
        if code < 32 and ch not in ("\n", "\r", "\t"):
            chars.append(f"\\u{code:04x}")
        else:
            chars.append(ch)
    return "".join(chars)


def _sanitize_json_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _sanitize_json_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_sanitize_json_value(v) for v in value]
    if isinstance(value, str):
        return _clean_json_string(value)
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return _clean_json_string(str(value))


def _is_missing_table_error(exc: Exception) -> bool:
    text_value = str(exc).lower()
    return "invalid object name" in text_value or "42s02" in text_value


def _is_fk_conflict_error(exc: Exception) -> bool:
    text_value = str(exc).lower()
    return "reference constraint" in text_value or "foreign key constraint" in text_value or "(547)" in text_value


def _is_missing_column_error(exc: Exception) -> bool:
    text_value = str(exc).lower()
    return "invalid column name" in text_value


ALLOWED_PART_SHAPES = {"round", "sheet", "prismatic", "weldment", "assembly", "unknown"}


def _normalize_shape(value: Any) -> str:
    raw = str(value or "").strip().lower()
    if not raw:
        return "unknown"
    synonyms = {
        "plate": "sheet",
        "sheet_metal": "sheet",
        "sheet metal": "sheet",
        "plaque": "sheet",
        "round_part": "round",
        "cylindrical": "round",
        "cylinder": "round",
        "tube": "round",
        "shaft": "round",
        "block": "prismatic",
        "prism": "prismatic",
        "welded": "weldment",
        "fabrication": "weldment",
        "assy": "assembly",
    }
    normalized = synonyms.get(raw, raw)
    if normalized in ALLOWED_PART_SHAPES:
        return normalized
    return "unknown"


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
            filters.append(
                "([name] LIKE :search OR [email] LIKE :search OR [phone] LIKE :search OR [contact_name] LIKE :search)"
            )
            params["search"] = f"%{search.strip()}%"
        where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""

        stmt = text(
            f"""
            SELECT TOP (:limit)
                [customer_id], [name], [email], [phone], [ship_to_address], [contact_name], [global_quote_comment], [created_at]
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

    def create_customer(self, payload: CustomerCreateRequest) -> CustomerSummary:
        if not self._engine:
            raise DatabaseError("Cedule database not configured")
        customer_id = uuid4()
        stmt = text(
            """
            INSERT INTO [Cedule].[dbo].[40_VENTES_SOUSTRAITANCE_customers]
            ([customer_id], [name], [email], [phone], [ship_to_address], [contact_name], [global_quote_comment])
            VALUES
            (:customer_id, :name, :email, :phone, :ship_to_address, :contact_name, :global_quote_comment)
            """
        )
        try:
            with self._engine.begin() as conn:
                conn.execute(
                    stmt,
                    {
                        "customer_id": str(customer_id),
                        "name": payload.name.strip()[:200],
                        "email": payload.email.strip()[:200] if payload.email else None,
                        "phone": payload.phone.strip()[:50] if payload.phone else None,
                        "ship_to_address": payload.ship_to_address.strip() if payload.ship_to_address else None,
                        "contact_name": payload.contact_name.strip()[:200] if payload.contact_name else None,
                        "global_quote_comment": payload.global_quote_comment.strip()
                        if payload.global_quote_comment
                        else None,
                    },
                )
            created = self._get_customer(customer_id)
            if not created:
                raise DatabaseError("Customer created but not found afterwards")
            return created
        except SQLAlchemyError as exc:
            logger.error("Failed to create customer", exc_info=exc)
            raise DatabaseError("Unable to create customer") from exc

    def update_customer(self, customer_id: UUID, payload: CustomerUpdateRequest) -> Optional[CustomerSummary]:
        if not self._engine:
            raise DatabaseError("Cedule database not configured")
        updates: list[str] = []
        params: dict[str, Any] = {"customer_id": str(customer_id)}
        if payload.name is not None:
            updates.append("[name] = :name")
            params["name"] = payload.name.strip()[:200]
        if payload.email is not None:
            updates.append("[email] = :email")
            params["email"] = payload.email.strip()[:200] if payload.email else None
        if payload.phone is not None:
            updates.append("[phone] = :phone")
            params["phone"] = payload.phone.strip()[:50] if payload.phone else None
        if payload.ship_to_address is not None:
            updates.append("[ship_to_address] = :ship_to_address")
            params["ship_to_address"] = payload.ship_to_address.strip() if payload.ship_to_address else None
        if payload.contact_name is not None:
            updates.append("[contact_name] = :contact_name")
            params["contact_name"] = payload.contact_name.strip()[:200] if payload.contact_name else None
        if payload.global_quote_comment is not None:
            updates.append("[global_quote_comment] = :global_quote_comment")
            params["global_quote_comment"] = payload.global_quote_comment.strip() if payload.global_quote_comment else None
        if not updates:
            return self._get_customer(customer_id)
        stmt = text(
            f"""
            UPDATE [Cedule].[dbo].[40_VENTES_SOUSTRAITANCE_customers]
            SET {', '.join(updates)}
            WHERE [customer_id] = :customer_id
            """
        )
        try:
            with self._engine.begin() as conn:
                result = conn.execute(stmt, params)
                if result.rowcount == 0:
                    return None
            return self._get_customer(customer_id)
        except SQLAlchemyError as exc:
            logger.error("Failed to update customer", exc_info=exc)
            raise DatabaseError("Unable to update customer") from exc

    def delete_customer(self, customer_id: UUID) -> bool:
        if not self._engine:
            raise DatabaseError("Cedule database not configured")
        stmt = text(
            """
            DELETE FROM [Cedule].[dbo].[40_VENTES_SOUSTRAITANCE_customers]
            WHERE [customer_id] = :customer_id
            """
        )
        try:
            with self._engine.begin() as conn:
                result = conn.execute(stmt, {"customer_id": str(customer_id)})
                return bool(result.rowcount)
        except SQLAlchemyError as exc:
            if _is_fk_conflict_error(exc):
                raise DatabaseError("Unable to delete customer because it is referenced by existing quotes.") from exc
            logger.error("Failed to delete customer", exc_info=exc)
            raise DatabaseError("Unable to delete customer") from exc

    def list_machine_groups(self, *, search: Optional[str], limit: int = 200) -> list[MachineGroupSummary]:
        if not self._engine:
            raise DatabaseError("Cedule database not configured")
        safe_limit = max(1, min(limit, 1000))
        filters: list[str] = []
        params: dict[str, Any] = {"limit": safe_limit}
        if search:
            filters.append("[name] LIKE :search OR [machine_group_id] LIKE :search")
            params["search"] = f"%{search.strip()}%"
        where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""
        stmt = text(
            f"""
            SELECT TOP (:limit)
                [machine_group_id], [name], [process_families_json], [config_json], [updated_at]
            FROM [Cedule].[dbo].[40_VENTES_SOUSTRAITANCE_machine_groups]
            {where_clause}
            ORDER BY [name] ASC
            """
        )
        try:
            with self._engine.connect() as conn:
                rows = conn.execute(stmt, params).mappings().all()
        except SQLAlchemyError as exc:
            logger.error("Failed to list machine groups", exc_info=exc)
            raise DatabaseError("Unable to list machine groups") from exc
        return [self._to_machine_group(row) for row in rows]

    def create_machine_group(self, payload: MachineGroupCreateRequest) -> MachineGroupSummary:
        if not self._engine:
            raise DatabaseError("Cedule database not configured")
        machine_group_id = self._normalize_machine_group_id(payload.machine_group_id)
        stmt = text(
            """
            INSERT INTO [Cedule].[dbo].[40_VENTES_SOUSTRAITANCE_machine_groups]
            ([machine_group_id], [name], [process_families_json], [config_json])
            VALUES
            (:machine_group_id, :name, :process_families_json, :config_json)
            """
        )
        try:
            with self._engine.begin() as conn:
                conn.execute(
                    stmt,
                    {
                        "machine_group_id": machine_group_id,
                        "name": payload.name.strip()[:200],
                        "process_families_json": payload.process_families_json,
                        "config_json": payload.config_json,
                    },
                )
            created = self._get_machine_group(machine_group_id)
            if not created:
                raise DatabaseError("Machine group created but not found afterwards")
            return created
        except SQLAlchemyError as exc:
            logger.error("Failed to create machine group", exc_info=exc)
            raise DatabaseError("Unable to create machine group") from exc

    def update_machine_group(self, machine_group_id: str, payload: MachineGroupUpdateRequest) -> Optional[MachineGroupSummary]:
        if not self._engine:
            raise DatabaseError("Cedule database not configured")
        normalized = self._normalize_machine_group_id(machine_group_id)
        updates: list[str] = []
        params: dict[str, Any] = {"machine_group_id": normalized}
        if payload.name is not None:
            updates.append("[name] = :name")
            params["name"] = payload.name.strip()[:200]
        if payload.process_families_json is not None:
            updates.append("[process_families_json] = :process_families_json")
            params["process_families_json"] = payload.process_families_json
        if payload.config_json is not None:
            updates.append("[config_json] = :config_json")
            params["config_json"] = payload.config_json
        if not updates:
            return self._get_machine_group(normalized)
        updates.append("[updated_at] = SYSUTCDATETIME()")
        stmt = text(
            f"""
            UPDATE [Cedule].[dbo].[40_VENTES_SOUSTRAITANCE_machine_groups]
            SET {', '.join(updates)}
            WHERE [machine_group_id] = :machine_group_id
            """
        )
        try:
            with self._engine.begin() as conn:
                result = conn.execute(stmt, params)
                if result.rowcount == 0:
                    return None
            return self._get_machine_group(normalized)
        except SQLAlchemyError as exc:
            logger.error("Failed to update machine group", exc_info=exc)
            raise DatabaseError("Unable to update machine group") from exc

    def delete_machine_group(self, machine_group_id: str) -> bool:
        if not self._engine:
            raise DatabaseError("Cedule database not configured")
        normalized = self._normalize_machine_group_id(machine_group_id)
        stmt = text(
            """
            DELETE FROM [Cedule].[dbo].[40_VENTES_SOUSTRAITANCE_machine_groups]
            WHERE [machine_group_id] = :machine_group_id
            """
        )
        try:
            with self._engine.begin() as conn:
                result = conn.execute(stmt, {"machine_group_id": normalized})
                return bool(result.rowcount)
        except SQLAlchemyError as exc:
            if _is_fk_conflict_error(exc):
                raise DatabaseError("Unable to delete machine group because it is referenced by existing machines or routings.") from exc
            logger.error("Failed to delete machine group", exc_info=exc)
            raise DatabaseError("Unable to delete machine group") from exc

    def list_machine_capability_options(
        self, *, search: Optional[str], capability_code: Optional[str], limit: int = 200
    ) -> list[MachineCapabilityOption]:
        if not self._engine:
            raise DatabaseError("Cedule database not configured")
        safe_limit = max(1, min(limit, 1000))
        filters: list[str] = ["[is_active] = 1"]
        params: dict[str, Any] = {"limit": safe_limit}
        if capability_code:
            filters.append("[capability_code] = :capability_code")
            params["capability_code"] = capability_code.strip().upper()
        if search:
            filters.append("([capability_code] LIKE :search OR [capability_value] LIKE :search OR [unit] LIKE :search)")
            params["search"] = f"%{search.strip()}%"
        where_clause = f"WHERE {' AND '.join(filters)}"
        table_stmt = text(
            f"""
            SELECT TOP (:limit)
                [capability_code],
                [capability_value],
                [unit],
                0 AS [usage_count]
            FROM [Cedule].[dbo].[40_VENTES_SOUSTRAITANCE_machine_capability_options]
            {where_clause}
            ORDER BY [capability_code] ASC, [capability_value] ASC
            """
        )
        fallback_filters: list[str] = []
        fallback_params: dict[str, Any] = {"limit": safe_limit}
        if capability_code:
            fallback_filters.append("[capability_code] = :capability_code")
            fallback_params["capability_code"] = capability_code.strip().upper()
        if search:
            fallback_filters.append("([capability_code] LIKE :search OR [capability_value] LIKE :search OR [unit] LIKE :search)")
            fallback_params["search"] = f"%{search.strip()}%"
        fallback_where = f"WHERE {' AND '.join(fallback_filters)}" if fallback_filters else ""
        fallback_stmt = text(
            f"""
            SELECT TOP (:limit)
                [capability_code],
                [capability_value],
                [unit],
                COUNT(1) AS [usage_count]
            FROM [Cedule].[dbo].[40_VENTES_SOUSTRAITANCE_machine_capabilities]
            {fallback_where}
            GROUP BY [capability_code], [capability_value], [unit]
            ORDER BY [capability_code] ASC, [usage_count] DESC, [capability_value] ASC
            """
        )
        try:
            with self._engine.connect() as conn:
                rows = conn.execute(table_stmt, params).mappings().all()
                if not rows:
                    rows = conn.execute(fallback_stmt, fallback_params).mappings().all()
        except SQLAlchemyError as exc:
            if _is_missing_table_error(exc):
                try:
                    with self._engine.connect() as conn:
                        rows = conn.execute(fallback_stmt, fallback_params).mappings().all()
                except SQLAlchemyError as fallback_exc:
                    if _is_missing_table_error(fallback_exc):
                        return []
                    logger.error("Failed to list machine capability options", exc_info=fallback_exc)
                    raise DatabaseError("Unable to list machine capability options") from fallback_exc
            else:
                logger.error("Failed to list machine capability options", exc_info=exc)
                raise DatabaseError("Unable to list machine capability options") from exc

        return [
            MachineCapabilityOption(
                capability_code=str(row.get("capability_code") or ""),
                capability_value=row.get("capability_value"),
                unit=row.get("unit"),
                usage_count=_safe_int(row.get("usage_count"), 0),
            )
            for row in rows
            if row.get("capability_code")
        ]

    def create_machine_capability_option(self, payload: MachineCapabilityOptionCreateRequest) -> MachineCapabilityOptionEntry:
        if not self._engine:
            raise DatabaseError("Cedule database not configured")
        option_id = uuid4()
        stmt = text(
            """
            INSERT INTO [Cedule].[dbo].[40_VENTES_SOUSTRAITANCE_machine_capability_options]
            ([option_id], [capability_code], [capability_value], [unit], [is_active], [notes])
            VALUES
            (:option_id, :capability_code, :capability_value, :unit, :is_active, :notes)
            """
        )
        try:
            with self._engine.begin() as conn:
                conn.execute(
                    stmt,
                    {
                        "option_id": str(option_id),
                        "capability_code": payload.capability_code.strip().upper()[:100],
                        "capability_value": payload.capability_value,
                        "unit": payload.unit,
                        "is_active": payload.is_active,
                        "notes": payload.notes,
                    },
                )
            created = self._get_machine_capability_option(option_id)
            if not created:
                raise DatabaseError("Machine capability option created but not found afterwards")
            return created
        except SQLAlchemyError as exc:
            if _is_missing_table_error(exc):
                raise DatabaseError(
                    "Machine capability option table is missing. Run docs/ventes_sous_traitance_machine_capability_options_schema.sql first."
                ) from exc
            logger.error("Failed to create machine capability option", exc_info=exc)
            raise DatabaseError("Unable to create machine capability option") from exc

    def update_machine_capability_option(
        self, option_id: UUID, payload: MachineCapabilityOptionUpdateRequest
    ) -> Optional[MachineCapabilityOptionEntry]:
        if not self._engine:
            raise DatabaseError("Cedule database not configured")
        updates: list[str] = []
        params: dict[str, Any] = {"option_id": str(option_id)}
        if payload.capability_code is not None:
            updates.append("[capability_code] = :capability_code")
            params["capability_code"] = payload.capability_code.strip().upper()[:100]
        if payload.capability_value is not None:
            updates.append("[capability_value] = :capability_value")
            params["capability_value"] = payload.capability_value
        if payload.unit is not None:
            updates.append("[unit] = :unit")
            params["unit"] = payload.unit
        if payload.is_active is not None:
            updates.append("[is_active] = :is_active")
            params["is_active"] = payload.is_active
        if payload.notes is not None:
            updates.append("[notes] = :notes")
            params["notes"] = payload.notes
        if not updates:
            return self._get_machine_capability_option(option_id)
        updates.append("[updated_at] = SYSUTCDATETIME()")
        stmt = text(
            f"""
            UPDATE [Cedule].[dbo].[40_VENTES_SOUSTRAITANCE_machine_capability_options]
            SET {', '.join(updates)}
            WHERE [option_id] = :option_id
            """
        )
        try:
            with self._engine.begin() as conn:
                result = conn.execute(stmt, params)
                if result.rowcount == 0:
                    return None
            return self._get_machine_capability_option(option_id)
        except SQLAlchemyError as exc:
            if _is_missing_table_error(exc):
                raise DatabaseError(
                    "Machine capability option table is missing. Run docs/ventes_sous_traitance_machine_capability_options_schema.sql first."
                ) from exc
            logger.error("Failed to update machine capability option", exc_info=exc)
            raise DatabaseError("Unable to update machine capability option") from exc

    def list_machine_capability_catalog(self, *, search: Optional[str], limit: int = 200) -> list[MachineCapabilityCatalogItem]:
        if not self._engine:
            raise DatabaseError("Cedule database not configured")
        safe_limit = max(1, min(limit, 1000))
        filters: list[str] = []
        params: dict[str, Any] = {"limit": safe_limit}
        if search:
            filters.append("[capability_code] LIKE :search")
            params["search"] = f"%{search.strip()}%"
        where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""
        summary_stmt = text(
            f"""
            SELECT TOP (:limit)
                [capability_code],
                COUNT(1) AS [usage_count],
                SUM(CASE WHEN [bool_value] IS NOT NULL THEN 1 ELSE 0 END) AS [bool_count],
                SUM(CASE WHEN [numeric_value] IS NOT NULL THEN 1 ELSE 0 END) AS [numeric_count],
                SUM(CASE WHEN [capability_value] IS NOT NULL AND LTRIM(RTRIM([capability_value])) <> '' THEN 1 ELSE 0 END) AS [text_count],
                MAX(NULLIF([unit], '')) AS [suggested_unit]
            FROM [Cedule].[dbo].[40_VENTES_SOUSTRAITANCE_machine_capabilities]
            {where_clause}
            GROUP BY [capability_code]
            ORDER BY [usage_count] DESC, [capability_code] ASC
            """
        )
        examples_stmt = text(
            """
            SELECT TOP (5)
                [capability_value]
            FROM [Cedule].[dbo].[40_VENTES_SOUSTRAITANCE_machine_capabilities]
            WHERE [capability_code] = :capability_code
              AND [capability_value] IS NOT NULL
              AND LTRIM(RTRIM([capability_value])) <> ''
            GROUP BY [capability_value]
            ORDER BY COUNT(1) DESC, [capability_value] ASC
            """
        )
        try:
            with self._engine.connect() as conn:
                rows = conn.execute(summary_stmt, params).mappings().all()
                items: list[MachineCapabilityCatalogItem] = []
                for row in rows:
                    code = str(row.get("capability_code") or "").strip()
                    if not code:
                        continue
                    bool_count = _safe_int(row.get("bool_count"), 0)
                    numeric_count = _safe_int(row.get("numeric_count"), 0)
                    text_count = _safe_int(row.get("text_count"), 0)
                    recommended_input_type = "text"
                    if bool_count >= numeric_count and bool_count >= text_count and bool_count > 0:
                        recommended_input_type = "boolean"
                    elif numeric_count >= bool_count and numeric_count >= text_count and numeric_count > 0:
                        recommended_input_type = "number"
                    examples = conn.execute(examples_stmt, {"capability_code": code}).scalars().all()
                    items.append(
                        MachineCapabilityCatalogItem(
                            capability_code=code,
                            recommended_input_type=recommended_input_type,
                            suggested_unit=row.get("suggested_unit"),
                            usage_count=_safe_int(row.get("usage_count"), 0),
                            example_values=[str(value) for value in examples if value is not None],
                        )
                    )
        except SQLAlchemyError as exc:
            if _is_missing_table_error(exc):
                return []
            logger.error("Failed to list machine capability catalog", exc_info=exc)
            raise DatabaseError("Unable to list machine capability catalog") from exc
        return items

    def list_machines(
        self,
        *,
        search: Optional[str],
        machine_group_id: Optional[str],
        active_only: bool,
        limit: int = 200,
    ) -> list[MachineResponse]:
        if not self._engine:
            raise DatabaseError("Cedule database not configured")
        safe_limit = max(1, min(limit, 1000))
        filters: list[str] = []
        params: dict[str, Any] = {"limit": safe_limit}
        if search:
            filters.append("([machine_name] LIKE :search OR [machine_code] LIKE :search)")
            params["search"] = f"%{search.strip()}%"
        if machine_group_id:
            filters.append("[machine_group_id] = :machine_group_id")
            params["machine_group_id"] = self._normalize_machine_group_id(machine_group_id)
        if active_only:
            filters.append("[is_active] = 1")
        where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""

        stmt = text(
            f"""
            SELECT TOP (:limit)
                [machine_id], [machine_code], [machine_name], [machine_group_id], [is_active],
                [default_setup_time_min], [default_runtime_min], [envelope_x_mm], [envelope_y_mm], [envelope_z_mm],
                [max_part_weight_kg], [notes], [created_at], [updated_at]
            FROM [Cedule].[dbo].[40_VENTES_SOUSTRAITANCE_machines]
            {where_clause}
            ORDER BY [machine_name] ASC
            """
        )
        try:
            with self._engine.connect() as conn:
                rows = conn.execute(stmt, params).mappings().all()
                machine_ids = [str(row.get("machine_id")) for row in rows if row.get("machine_id")]
                caps_by_machine = self._load_capabilities_map(conn, machine_ids)
        except SQLAlchemyError as exc:
            if _is_missing_table_error(exc):
                return []
            logger.error("Failed to list machines", exc_info=exc)
            raise DatabaseError("Unable to list machines") from exc

        return [self._to_machine(row, caps_by_machine.get(str(row.get("machine_id")), [])) for row in rows]

    def get_machine(self, machine_id: UUID) -> Optional[MachineResponse]:
        if not self._engine:
            raise DatabaseError("Cedule database not configured")
        stmt = text(
            """
            SELECT
                [machine_id], [machine_code], [machine_name], [machine_group_id], [is_active],
                [default_setup_time_min], [default_runtime_min], [envelope_x_mm], [envelope_y_mm], [envelope_z_mm],
                [max_part_weight_kg], [notes], [created_at], [updated_at]
            FROM [Cedule].[dbo].[40_VENTES_SOUSTRAITANCE_machines]
            WHERE [machine_id] = :machine_id
            """
        )
        try:
            with self._engine.connect() as conn:
                row = conn.execute(stmt, {"machine_id": str(machine_id)}).mappings().first()
                if not row:
                    return None
                caps_by_machine = self._load_capabilities_map(conn, [str(machine_id)])
        except SQLAlchemyError as exc:
            if _is_missing_table_error(exc):
                return None
            logger.error("Failed to get machine", exc_info=exc)
            raise DatabaseError("Unable to get machine") from exc
        return self._to_machine(row, caps_by_machine.get(str(machine_id), []))

    def create_machine(self, payload: MachineCreateRequest) -> MachineResponse:
        if not self._engine:
            raise DatabaseError("Cedule database not configured")
        machine_id = uuid4()
        stmt = text(
            """
            INSERT INTO [Cedule].[dbo].[40_VENTES_SOUSTRAITANCE_machines]
            (
                [machine_id], [machine_code], [machine_name], [machine_group_id], [is_active],
                [default_setup_time_min], [default_runtime_min], [envelope_x_mm], [envelope_y_mm], [envelope_z_mm],
                [max_part_weight_kg], [notes]
            )
            VALUES
            (
                :machine_id, :machine_code, :machine_name, :machine_group_id, :is_active,
                :default_setup_time_min, :default_runtime_min, :envelope_x_mm, :envelope_y_mm, :envelope_z_mm,
                :max_part_weight_kg, :notes
            )
            """
        )
        group_id = self._normalize_machine_group_id(payload.machine_group_id) if payload.machine_group_id else None
        try:
            with self._engine.begin() as conn:
                if group_id:
                    self._ensure_machine_group_entry(conn, group_id)
                conn.execute(
                    stmt,
                    {
                        "machine_id": str(machine_id),
                        "machine_code": payload.machine_code.strip().upper()[:100],
                        "machine_name": payload.machine_name.strip()[:200],
                        "machine_group_id": group_id,
                        "is_active": payload.is_active,
                        "default_setup_time_min": payload.default_setup_time_min,
                        "default_runtime_min": payload.default_runtime_min,
                        "envelope_x_mm": payload.envelope_x_mm,
                        "envelope_y_mm": payload.envelope_y_mm,
                        "envelope_z_mm": payload.envelope_z_mm,
                        "max_part_weight_kg": payload.max_part_weight_kg,
                        "notes": payload.notes,
                    },
                )
                self._replace_machine_capabilities(conn, machine_id, payload.capabilities)
            created = self.get_machine(machine_id)
            if not created:
                raise DatabaseError("Machine created but not found afterwards")
            return created
        except SQLAlchemyError as exc:
            if _is_missing_table_error(exc):
                raise DatabaseError("Machine config tables are missing. Run docs/ventes_sous_traitance_machine_config_schema.sql first.") from exc
            logger.error("Failed to create machine", exc_info=exc)
            raise DatabaseError("Unable to create machine") from exc

    def update_machine(self, machine_id: UUID, payload: MachineUpdateRequest) -> Optional[MachineResponse]:
        if not self._engine:
            raise DatabaseError("Cedule database not configured")
        updates: list[str] = []
        params: dict[str, Any] = {"machine_id": str(machine_id)}

        for field in (
            "machine_name",
            "is_active",
            "default_setup_time_min",
            "default_runtime_min",
            "envelope_x_mm",
            "envelope_y_mm",
            "envelope_z_mm",
            "max_part_weight_kg",
            "notes",
        ):
            value = getattr(payload, field)
            if value is not None:
                updates.append(f"[{field}] = :{field}")
                params[field] = value

        normalized_group: Optional[str] = None
        if payload.machine_group_id is not None:
            normalized_group = self._normalize_machine_group_id(payload.machine_group_id)
            updates.append("[machine_group_id] = :machine_group_id")
            params["machine_group_id"] = normalized_group

        if not updates and payload.capabilities is None:
            return self.get_machine(machine_id)
        updates.append("[updated_at] = SYSUTCDATETIME()")
        stmt = text(
            f"""
            UPDATE [Cedule].[dbo].[40_VENTES_SOUSTRAITANCE_machines]
            SET {', '.join(updates)}
            WHERE [machine_id] = :machine_id
            """
        )
        try:
            with self._engine.begin() as conn:
                if normalized_group:
                    self._ensure_machine_group_entry(conn, normalized_group)
                result = conn.execute(stmt, params)
                if result.rowcount == 0:
                    return None
                if payload.capabilities is not None:
                    self._replace_machine_capabilities(conn, machine_id, payload.capabilities)
            return self.get_machine(machine_id)
        except SQLAlchemyError as exc:
            if _is_missing_table_error(exc):
                raise DatabaseError("Machine config tables are missing. Run docs/ventes_sous_traitance_machine_config_schema.sql first.") from exc
            logger.error("Failed to update machine", exc_info=exc)
            raise DatabaseError("Unable to update machine") from exc

    def delete_machine(self, machine_id: UUID) -> bool:
        if not self._engine:
            raise DatabaseError("Cedule database not configured")
        stmt = text(
            """
            DELETE FROM [Cedule].[dbo].[40_VENTES_SOUSTRAITANCE_machines]
            WHERE [machine_id] = :machine_id
            """
        )
        try:
            with self._engine.begin() as conn:
                result = conn.execute(stmt, {"machine_id": str(machine_id)})
                return bool(result.rowcount)
        except SQLAlchemyError as exc:
            if _is_fk_conflict_error(exc):
                raise DatabaseError("Unable to delete machine because it is referenced by existing routing steps.") from exc
            if _is_missing_table_error(exc):
                raise DatabaseError("Machine config tables are missing. Run docs/ventes_sous_traitance_machine_config_schema.sql first.") from exc
            logger.error("Failed to delete machine", exc_info=exc)
            raise DatabaseError("Unable to delete machine") from exc

    def _get_customer(self, customer_id: UUID) -> Optional[CustomerSummary]:
        stmt = text(
            """
            SELECT [customer_id], [name], [email], [phone], [ship_to_address], [contact_name], [global_quote_comment], [created_at]
            FROM [Cedule].[dbo].[40_VENTES_SOUSTRAITANCE_customers]
            WHERE [customer_id] = :customer_id
            """
        )
        with self._engine.connect() as conn:  # type: ignore[union-attr]
            row = conn.execute(stmt, {"customer_id": str(customer_id)}).mappings().first()
        if not row:
            return None
        return self._to_customer(row)

    def _get_machine_group(self, machine_group_id: str) -> Optional[MachineGroupSummary]:
        stmt = text(
            """
            SELECT [machine_group_id], [name], [process_families_json], [config_json], [updated_at]
            FROM [Cedule].[dbo].[40_VENTES_SOUSTRAITANCE_machine_groups]
            WHERE [machine_group_id] = :machine_group_id
            """
        )
        with self._engine.connect() as conn:  # type: ignore[union-attr]
            row = conn.execute(stmt, {"machine_group_id": machine_group_id}).mappings().first()
        if not row:
            return None
        return self._to_machine_group(row)

    def _get_machine_capability_option(self, option_id: UUID) -> Optional[MachineCapabilityOptionEntry]:
        stmt = text(
            """
            SELECT
                [option_id], [capability_code], [capability_value], [unit], [is_active], [notes], [created_at], [updated_at]
            FROM [Cedule].[dbo].[40_VENTES_SOUSTRAITANCE_machine_capability_options]
            WHERE [option_id] = :option_id
            """
        )
        with self._engine.connect() as conn:  # type: ignore[union-attr]
            row = conn.execute(stmt, {"option_id": str(option_id)}).mappings().first()
        if not row:
            return None
        return self._to_machine_capability_option_entry(row)

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

    def list_quote_parts(self, quote_id: UUID) -> list[QuotePartSummary]:
        if not self._engine:
            raise DatabaseError("Cedule database not configured")
        stmt = text(
            """
            SELECT
                [part_id],
                [quote_id],
                [customer_part_number],
                [internal_part_number],
                [quantity],
                [material],
                [thickness_mm],
                [weight_kg],
                [envelope_x_mm],
                [envelope_y_mm],
                [envelope_z_mm],
                [shape],
                [complexity_score],
                [created_at],
                [updated_at]
            FROM [Cedule].[dbo].[40_VENTES_SOUSTRAITANCE_quote_parts]
            WHERE [quote_id] = :quote_id
            ORDER BY [created_at] ASC
            """
        )
        try:
            with self._engine.connect() as conn:
                rows = conn.execute(stmt, {"quote_id": str(quote_id)}).mappings().all()
        except SQLAlchemyError as exc:
            logger.error("Failed to list quote parts", exc_info=exc)
            raise DatabaseError("Unable to list quote parts") from exc
        return [self._to_quote_part(row) for row in rows]

    def get_quote_part(self, part_id: UUID) -> Optional[QuotePartSummary]:
        if not self._engine:
            raise DatabaseError("Cedule database not configured")
        stmt = text(
            """
            SELECT
                [part_id],
                [quote_id],
                [customer_part_number],
                [internal_part_number],
                [quantity],
                [material],
                [thickness_mm],
                [weight_kg],
                [envelope_x_mm],
                [envelope_y_mm],
                [envelope_z_mm],
                [shape],
                [complexity_score],
                [created_at],
                [updated_at]
            FROM [Cedule].[dbo].[40_VENTES_SOUSTRAITANCE_quote_parts]
            WHERE [part_id] = :part_id
            """
        )
        try:
            with self._engine.connect() as conn:
                row = conn.execute(stmt, {"part_id": str(part_id)}).mappings().first()
        except SQLAlchemyError as exc:
            logger.error("Failed to fetch quote part", exc_info=exc)
            raise DatabaseError("Unable to fetch quote part") from exc
        return self._to_quote_part(row) if row else None

    def update_quote_part(self, part_id: UUID, payload: QuotePartUpdateRequest) -> Optional[QuotePartSummary]:
        if not self._engine:
            raise DatabaseError("Cedule database not configured")
        updates: list[str] = []
        params: dict[str, Any] = {"part_id": str(part_id)}
        if payload.customer_part_number is not None:
            updates.append("[customer_part_number] = :customer_part_number")
            params["customer_part_number"] = payload.customer_part_number.strip()[:100] if payload.customer_part_number else None
        if payload.internal_part_number is not None:
            updates.append("[internal_part_number] = :internal_part_number")
            params["internal_part_number"] = payload.internal_part_number.strip()[:100] if payload.internal_part_number else None
        if payload.quantity is not None:
            updates.append("[quantity] = :quantity")
            params["quantity"] = payload.quantity
        if payload.material is not None:
            updates.append("[material] = :material")
            params["material"] = payload.material
        if payload.thickness_mm is not None:
            updates.append("[thickness_mm] = :thickness_mm")
            params["thickness_mm"] = payload.thickness_mm
        if payload.weight_kg is not None:
            updates.append("[weight_kg] = :weight_kg")
            params["weight_kg"] = payload.weight_kg
        if payload.envelope_x_mm is not None:
            updates.append("[envelope_x_mm] = :envelope_x_mm")
            params["envelope_x_mm"] = payload.envelope_x_mm
        if payload.envelope_y_mm is not None:
            updates.append("[envelope_y_mm] = :envelope_y_mm")
            params["envelope_y_mm"] = payload.envelope_y_mm
        if payload.envelope_z_mm is not None:
            updates.append("[envelope_z_mm] = :envelope_z_mm")
            params["envelope_z_mm"] = payload.envelope_z_mm
        if payload.shape is not None:
            updates.append("[shape] = :shape")
            params["shape"] = _normalize_shape(payload.shape)
        if payload.complexity_score is not None:
            updates.append("[complexity_score] = :complexity_score")
            params["complexity_score"] = payload.complexity_score

        if not updates:
            return self.get_quote_part(part_id)

        stmt = text(
            f"""
            UPDATE [Cedule].[dbo].[40_VENTES_SOUSTRAITANCE_quote_parts]
            SET {', '.join(updates)}, [updated_at] = SYSUTCDATETIME()
            WHERE [part_id] = :part_id
            """
        )
        try:
            with self._engine.begin() as conn:
                result = conn.execute(stmt, params)
                if result.rowcount == 0:
                    return None
        except SQLAlchemyError as exc:
            logger.error("Failed to update quote part", exc_info=exc)
            raise DatabaseError("Unable to update quote part") from exc
        return self.get_quote_part(part_id)

    def list_routings(self, part_id: UUID) -> list[RoutingResponse]:
        if not self._engine:
            raise DatabaseError("Cedule database not configured")
        stmt = text(
            """
            SELECT
                [routing_id],
                [part_id],
                [scenario_name],
                [created_by],
                [selected],
                [rationale],
                [confidence_score],
                [assumptions_json],
                [unknowns_json],
                [source_run_id],
                [created_at]
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
            SELECT
                [routing_id],
                [part_id],
                [scenario_name],
                [created_by],
                [selected],
                [rationale],
                [confidence_score],
                [assumptions_json],
                [unknowns_json],
                [source_run_id],
                [created_at]
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
                if payload.machine_group_id:
                    self._ensure_machine_group_entry(conn, payload.machine_group_id)
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

    def get_part_feature_set(self, part_id: UUID) -> PartFeatureSetResponse:
        if not self._engine:
            raise DatabaseError("Cedule database not configured")
        summary_stmt = text(
            """
            SELECT
                [feature_set_id],
                [part_id],
                [source],
                [source_run_id],
                [feature_confidence],
                [part_summary_json],
                [additional_operations_json],
                [general_notes_json],
                [created_at],
                [updated_at]
            FROM [Cedule].[dbo].[40_VENTES_SOUSTRAITANCE_part_feature_sets]
            WHERE [part_id] = :part_id
            """
        )
        features_stmt = text(
            """
            SELECT
                [feature_id],
                [part_id],
                [source],
                [source_run_id],
                [feature_ref],
                [feature_type],
                [description],
                [quantity],
                [width_mm],
                [length_mm],
                [depth_mm],
                [diameter_mm],
                [thread_spec],
                [tolerance_note],
                [surface_finish_ra_um],
                [location_note],
                [complexity_factors_json],
                [estimated_operation_time_min],
                [is_user_override],
                [created_at],
                [updated_at]
            FROM [Cedule].[dbo].[40_VENTES_SOUSTRAITANCE_part_features]
            WHERE [part_id] = :part_id
            ORDER BY [created_at], [feature_id]
            """
        )
        try:
            with self._engine.connect() as conn:
                summary_row = conn.execute(summary_stmt, {"part_id": str(part_id)}).mappings().first()
                feature_rows = conn.execute(features_stmt, {"part_id": str(part_id)}).mappings().all()
        except SQLAlchemyError as exc:
            if _is_missing_table_error(exc):
                raise DatabaseError(
                    "Part feature tables are missing. Run docs/ventes_sous_traitance_llm_feature_schema.sql first."
                ) from exc
            logger.error("Failed to load part feature set", exc_info=exc)
            raise DatabaseError("Unable to load part feature set") from exc

        features = [self._to_part_feature(row) for row in feature_rows]
        if not summary_row:
            return PartFeatureSetResponse(part_id=part_id, features=features)

        return PartFeatureSetResponse(
            feature_set_id=UUID(str(summary_row.get("feature_set_id"))),
            part_id=UUID(str(summary_row.get("part_id"))),
            source=summary_row.get("source"),
            source_run_id=UUID(str(summary_row.get("source_run_id"))) if summary_row.get("source_run_id") else None,
            feature_confidence=(
                Decimal(str(summary_row["feature_confidence"]))
                if summary_row.get("feature_confidence") is not None
                else None
            ),
            part_summary=self._json_load_object(summary_row.get("part_summary_json")),
            additional_operations=self._json_load_string_list(summary_row.get("additional_operations_json")),
            general_notes=self._json_load_string_list(summary_row.get("general_notes_json")),
            features=features,
            created_at=summary_row.get("created_at"),
            updated_at=summary_row.get("updated_at"),
        )

    def replace_part_feature_set(self, part_id: UUID, payload: PartFeatureSetUpsertRequest) -> PartFeatureSetResponse:
        if not self._engine:
            raise DatabaseError("Cedule database not configured")
        upsert_stmt = text(
            """
            MERGE [Cedule].[dbo].[40_VENTES_SOUSTRAITANCE_part_feature_sets] AS target
            USING (SELECT :part_id AS [part_id]) AS source
            ON target.[part_id] = source.[part_id]
            WHEN MATCHED THEN
                UPDATE SET
                    [source] = :source,
                    [source_run_id] = :source_run_id,
                    [feature_confidence] = :feature_confidence,
                    [part_summary_json] = :part_summary_json,
                    [additional_operations_json] = :additional_operations_json,
                    [general_notes_json] = :general_notes_json,
                    [updated_at] = SYSUTCDATETIME()
            WHEN NOT MATCHED THEN
                INSERT (
                    [feature_set_id],
                    [part_id],
                    [source],
                    [source_run_id],
                    [feature_confidence],
                    [part_summary_json],
                    [additional_operations_json],
                    [general_notes_json]
                )
                VALUES (
                    :feature_set_id,
                    :part_id,
                    :source,
                    :source_run_id,
                    :feature_confidence,
                    :part_summary_json,
                    :additional_operations_json,
                    :general_notes_json
                );
            """
        )
        delete_stmt = text(
            """
            DELETE FROM [Cedule].[dbo].[40_VENTES_SOUSTRAITANCE_part_features]
            WHERE [part_id] = :part_id
            """
        )
        insert_stmt = text(
            """
            INSERT INTO [Cedule].[dbo].[40_VENTES_SOUSTRAITANCE_part_features]
            (
                [feature_id],
                [part_id],
                [source],
                [source_run_id],
                [feature_ref],
                [feature_type],
                [description],
                [quantity],
                [width_mm],
                [length_mm],
                [depth_mm],
                [diameter_mm],
                [thread_spec],
                [tolerance_note],
                [surface_finish_ra_um],
                [location_note],
                [complexity_factors_json],
                [estimated_operation_time_min],
                [is_user_override]
            )
            VALUES
            (
                :feature_id,
                :part_id,
                :source,
                :source_run_id,
                :feature_ref,
                :feature_type,
                :description,
                :quantity,
                :width_mm,
                :length_mm,
                :depth_mm,
                :diameter_mm,
                :thread_spec,
                :tolerance_note,
                :surface_finish_ra_um,
                :location_note,
                :complexity_factors_json,
                :estimated_operation_time_min,
                :is_user_override
            )
            """
        )
        try:
            with self._engine.begin() as conn:
                conn.execute(
                    upsert_stmt,
                    {
                        "feature_set_id": str(uuid4()),
                        "part_id": str(part_id),
                        "source": payload.source,
                        "source_run_id": str(payload.source_run_id) if payload.source_run_id else None,
                        "feature_confidence": payload.feature_confidence,
                        "part_summary_json": json.dumps(payload.part_summary, ensure_ascii=True) if payload.part_summary is not None else None,
                        "additional_operations_json": json.dumps(payload.additional_operations, ensure_ascii=True),
                        "general_notes_json": json.dumps(payload.general_notes, ensure_ascii=True),
                    },
                )
                conn.execute(delete_stmt, {"part_id": str(part_id)})
                for feature in payload.features:
                    conn.execute(
                        insert_stmt,
                        {
                            "feature_id": str(uuid4()),
                            "part_id": str(part_id),
                            "source": feature.source,
                            "source_run_id": str(feature.source_run_id) if feature.source_run_id else None,
                            "feature_ref": feature.feature_ref,
                            "feature_type": feature.feature_type,
                            "description": feature.description,
                            "quantity": feature.quantity,
                            "width_mm": feature.width_mm,
                            "length_mm": feature.length_mm,
                            "depth_mm": feature.depth_mm,
                            "diameter_mm": feature.diameter_mm,
                            "thread_spec": feature.thread_spec,
                            "tolerance_note": feature.tolerance_note,
                            "surface_finish_ra_um": feature.surface_finish_ra_um,
                            "location_note": feature.location_note,
                            "complexity_factors_json": json.dumps(feature.complexity_factors, ensure_ascii=True),
                            "estimated_operation_time_min": feature.estimated_operation_time_min,
                            "is_user_override": feature.is_user_override,
                        },
                    )
        except SQLAlchemyError as exc:
            if _is_missing_table_error(exc):
                raise DatabaseError(
                    "Part feature tables are missing. Run docs/ventes_sous_traitance_llm_feature_schema.sql first."
                ) from exc
            logger.error("Failed to replace part feature set", exc_info=exc)
            raise DatabaseError("Unable to replace part feature set") from exc
        return self.get_part_feature_set(part_id)

    def create_part_feature(self, part_id: UUID, payload: PartFeatureCreateRequest) -> PartFeatureResponse:
        if not self._engine:
            raise DatabaseError("Cedule database not configured")
        self._upsert_part_feature_set_header(
            part_id=part_id,
            source=payload.source,
            source_run_id=payload.source_run_id,
            feature_confidence=None,
            part_summary=None,
            additional_operations=None,
            general_notes=None,
        )
        feature_id = uuid4()
        stmt = text(
            """
            INSERT INTO [Cedule].[dbo].[40_VENTES_SOUSTRAITANCE_part_features]
            (
                [feature_id],
                [part_id],
                [source],
                [source_run_id],
                [feature_ref],
                [feature_type],
                [description],
                [quantity],
                [width_mm],
                [length_mm],
                [depth_mm],
                [diameter_mm],
                [thread_spec],
                [tolerance_note],
                [surface_finish_ra_um],
                [location_note],
                [complexity_factors_json],
                [estimated_operation_time_min],
                [is_user_override]
            )
            VALUES
            (
                :feature_id,
                :part_id,
                :source,
                :source_run_id,
                :feature_ref,
                :feature_type,
                :description,
                :quantity,
                :width_mm,
                :length_mm,
                :depth_mm,
                :diameter_mm,
                :thread_spec,
                :tolerance_note,
                :surface_finish_ra_um,
                :location_note,
                :complexity_factors_json,
                :estimated_operation_time_min,
                :is_user_override
            )
            """
        )
        try:
            with self._engine.begin() as conn:
                conn.execute(
                    stmt,
                    {
                        "feature_id": str(feature_id),
                        "part_id": str(part_id),
                        "source": payload.source,
                        "source_run_id": str(payload.source_run_id) if payload.source_run_id else None,
                        "feature_ref": payload.feature_ref,
                        "feature_type": payload.feature_type,
                        "description": payload.description,
                        "quantity": payload.quantity,
                        "width_mm": payload.width_mm,
                        "length_mm": payload.length_mm,
                        "depth_mm": payload.depth_mm,
                        "diameter_mm": payload.diameter_mm,
                        "thread_spec": payload.thread_spec,
                        "tolerance_note": payload.tolerance_note,
                        "surface_finish_ra_um": payload.surface_finish_ra_um,
                        "location_note": payload.location_note,
                        "complexity_factors_json": json.dumps(payload.complexity_factors, ensure_ascii=True),
                        "estimated_operation_time_min": payload.estimated_operation_time_min,
                        "is_user_override": payload.is_user_override,
                    },
                )
        except SQLAlchemyError as exc:
            if _is_missing_table_error(exc):
                raise DatabaseError(
                    "Part feature tables are missing. Run docs/ventes_sous_traitance_llm_feature_schema.sql first."
                ) from exc
            logger.error("Failed to create part feature", exc_info=exc)
            raise DatabaseError("Unable to create part feature") from exc
        created = self._get_part_feature(feature_id)
        if not created:
            raise DatabaseError("Part feature created but not found afterwards")
        return created

    def update_part_feature(self, feature_id: UUID, payload: PartFeatureUpdateRequest) -> Optional[PartFeatureResponse]:
        if not self._engine:
            raise DatabaseError("Cedule database not configured")
        updates: list[str] = []
        params: dict[str, Any] = {"feature_id": str(feature_id)}
        for field in (
            "source",
            "source_run_id",
            "feature_ref",
            "feature_type",
            "description",
            "quantity",
            "width_mm",
            "length_mm",
            "depth_mm",
            "diameter_mm",
            "thread_spec",
            "tolerance_note",
            "surface_finish_ra_um",
            "location_note",
            "estimated_operation_time_min",
            "is_user_override",
        ):
            value = getattr(payload, field)
            if value is not None:
                updates.append(f"[{field}] = :{field}")
                params[field] = str(value) if field == "source_run_id" and value is not None else value
        if payload.complexity_factors is not None:
            updates.append("[complexity_factors_json] = :complexity_factors_json")
            params["complexity_factors_json"] = json.dumps(payload.complexity_factors, ensure_ascii=True)
        if not updates:
            return self._get_part_feature(feature_id)

        stmt = text(
            f"""
            UPDATE [Cedule].[dbo].[40_VENTES_SOUSTRAITANCE_part_features]
            SET {', '.join(updates)}, [updated_at] = SYSUTCDATETIME()
            WHERE [feature_id] = :feature_id
            """
        )
        try:
            with self._engine.begin() as conn:
                result = conn.execute(stmt, params)
                if result.rowcount == 0:
                    return None
        except SQLAlchemyError as exc:
            if _is_missing_table_error(exc):
                raise DatabaseError(
                    "Part feature tables are missing. Run docs/ventes_sous_traitance_llm_feature_schema.sql first."
                ) from exc
            logger.error("Failed to update part feature", exc_info=exc)
            raise DatabaseError("Unable to update part feature") from exc
        return self._get_part_feature(feature_id)

    def save_part_feature_set_from_llm(self, *, part_id: UUID, run_id: UUID, payload: dict[str, Any]) -> UUID | None:
        if not payload:
            return None
        features_input: list[PartFeatureCreateRequest] = []
        raw_features = payload.get("machining_features")
        if isinstance(raw_features, list):
            for item in raw_features:
                if not isinstance(item, dict):
                    continue
                dims = item.get("dimensions") if isinstance(item.get("dimensions"), dict) else {}
                try:
                    features_input.append(
                        PartFeatureCreateRequest(
                            source="llm",
                            source_run_id=run_id,
                            feature_ref=(str(item.get("feature_id"))[:50] if item.get("feature_id") is not None else None),
                            feature_type=str(item.get("type") or "unknown")[:100] or "unknown",
                            description=item.get("description"),
                            quantity=max(1, _safe_int(item.get("quantity"), default=1)),
                            width_mm=dims.get("width_mm"),
                            length_mm=dims.get("length_mm"),
                            depth_mm=dims.get("depth_mm"),
                            diameter_mm=dims.get("diameter_mm"),
                            thread_spec=dims.get("thread_spec"),
                            tolerance_note=item.get("tolerance"),
                            surface_finish_ra_um=item.get("surface_finish_ra"),
                            location_note=item.get("location"),
                            complexity_factors=[
                                str(v) for v in (item.get("complexity_factors") or []) if isinstance(v, (str, int, float, bool))
                            ],
                            estimated_operation_time_min=item.get("estimated_operation_time_min"),
                            is_user_override=False,
                        )
                    )
                except Exception:
                    continue
        upsert = PartFeatureSetUpsertRequest(
            source="llm",
            source_run_id=run_id,
            feature_confidence=payload.get("confidence"),
            part_summary=payload.get("part_summary") if isinstance(payload.get("part_summary"), dict) else None,
            additional_operations=[str(v) for v in (payload.get("additional_operations") or []) if v is not None],
            general_notes=[str(v) for v in (payload.get("general_notes") or []) if v is not None],
            features=features_input,
        )
        saved = self.replace_part_feature_set(part_id, upsert)
        return saved.feature_set_id

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
        sanitized_output = _sanitize_json_value(output)
        stmt = text(
            """
            UPDATE [Cedule].[dbo].[40_VENTES_SOUSTRAITANCE_llm_runs]
            SET [output_json] = :output_json, [ended_at] = SYSUTCDATETIME(), [status] = 'ok'
            WHERE [run_id] = :run_id
            """
        )
        try:
            with self._engine.begin() as conn:
                conn.execute(
                    stmt,
                    {
                        "run_id": str(run_id),
                        "output_json": json.dumps(sanitized_output, ensure_ascii=True, default=str),
                    },
                )
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

    def upsert_part_from_analysis(
        self,
        quote_id: UUID,
        metadata: dict[str, Any],
        classification: dict[str, Any],
        complexity: dict[str, Any],
        *,
        target_part_ref: str | None = None,
    ) -> UUID:
        if not self._engine:
            raise DatabaseError("Cedule database not configured")
        find_by_ref_stmt = text(
            """
            SELECT TOP 1 [part_id]
            FROM [Cedule].[dbo].[40_VENTES_SOUSTRAITANCE_quote_parts]
            WHERE [quote_id] = :quote_id
              AND (
                [customer_part_number] = :part_ref
                OR [internal_part_number] = :part_ref
              )
            ORDER BY [created_at]
            """
        )
        find_by_metadata_stmt = text(
            """
            SELECT TOP 1 [part_id]
            FROM [Cedule].[dbo].[40_VENTES_SOUSTRAITANCE_quote_parts]
            WHERE [quote_id] = :quote_id
              AND (
                (:customer_part_number IS NOT NULL AND [customer_part_number] = :customer_part_number)
                OR
                (:internal_part_number IS NOT NULL AND [internal_part_number] = :internal_part_number)
              )
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
        normalized_part_ref = str(target_part_ref).strip()[:100] if target_part_ref else None
        customer_part_number = metadata.get("customer_part_number")
        internal_part_number = metadata.get("internal_part_number")
        if normalized_part_ref:
            if not customer_part_number and not internal_part_number:
                customer_part_number = normalized_part_ref
            elif customer_part_number and customer_part_number != normalized_part_ref and not internal_part_number:
                internal_part_number = normalized_part_ref

        params = {
            "quote_id": str(quote_id),
            "customer_part_number": customer_part_number,
            "internal_part_number": internal_part_number,
            "quantity": max(1, _safe_int(metadata.get("quantity_requested"), default=1)),
            "material": metadata.get("material_spec"),
            "thickness_mm": metadata.get("thickness_mm"),
            "weight_kg": classification.get("weight_estimate_kg"),
            "envelope_x_mm": envelope.get("x"),
            "envelope_y_mm": envelope.get("y"),
            "envelope_z_mm": envelope.get("z"),
            "shape": _normalize_shape(classification.get("shape_class")),
            "complexity_score": complexity.get("complexity_score"),
        }

        try:
            with self._engine.begin() as conn:
                existing = None
                if normalized_part_ref:
                    existing = conn.execute(
                        find_by_ref_stmt,
                        {"quote_id": str(quote_id), "part_ref": normalized_part_ref},
                    ).scalar()
                if not existing and (params["customer_part_number"] or params["internal_part_number"]):
                    existing = conn.execute(find_by_metadata_stmt, params).scalar()
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

    def ensure_machine_group_entry(self, machine_group_id: str) -> str:
        if not self._engine:
            raise DatabaseError("Cedule database not configured")
        try:
            with self._engine.begin() as conn:
                return self._ensure_machine_group_entry(conn, machine_group_id)
        except SQLAlchemyError as exc:
            logger.error("Failed to ensure machine group entry", exc_info=exc)
            raise DatabaseError("Unable to ensure machine group entry") from exc

    @staticmethod
    def _normalize_machine_group_id(machine_group_id: str) -> str:
        return (machine_group_id or "UNKNOWN_MACHINE_GROUP").strip().upper()[:100]

    def _ensure_machine_group_entry(self, conn, machine_group_id: str) -> str:
        normalized = self._normalize_machine_group_id(machine_group_id)
        select_stmt = text(
            """
            SELECT [machine_group_id]
            FROM [Cedule].[dbo].[40_VENTES_SOUSTRAITANCE_machine_groups]
            WHERE [machine_group_id] = :machine_group_id
            """
        )
        insert_stmt = text(
            """
            INSERT INTO [Cedule].[dbo].[40_VENTES_SOUSTRAITANCE_machine_groups]
            (
                [machine_group_id], [name], [process_families_json], [config_json]
            )
            VALUES
            (
                :machine_group_id, :name, :process_families_json, :config_json
            )
            """
        )
        existing = conn.execute(select_stmt, {"machine_group_id": normalized}).scalar()
        if existing:
            return normalized
        conn.execute(
            insert_stmt,
            {
                "machine_group_id": normalized,
                "name": normalized.replace("_", " ").title(),
                "process_families_json": None,
                "config_json": None,
            },
        )
        return normalized

    def _replace_machine_capabilities(
        self,
        conn,
        machine_id: UUID,
        capabilities: list[MachineCapabilityInput],
    ) -> None:
        delete_stmt = text(
            """
            DELETE FROM [Cedule].[dbo].[40_VENTES_SOUSTRAITANCE_machine_capabilities]
            WHERE [machine_id] = :machine_id
            """
        )
        insert_stmt = text(
            """
            INSERT INTO [Cedule].[dbo].[40_VENTES_SOUSTRAITANCE_machine_capabilities]
            (
                [capability_id], [machine_id], [capability_code], [capability_value], [numeric_value],
                [bool_value], [unit], [notes]
            )
            VALUES
            (
                :capability_id, :machine_id, :capability_code, :capability_value, :numeric_value,
                :bool_value, :unit, :notes
            )
            """
        )
        conn.execute(delete_stmt, {"machine_id": str(machine_id)})
        for cap in capabilities:
            conn.execute(
                insert_stmt,
                {
                    "capability_id": str(uuid4()),
                    "machine_id": str(machine_id),
                    "capability_code": cap.capability_code.strip().upper()[:100],
                    "capability_value": cap.capability_value,
                    "numeric_value": cap.numeric_value,
                    "bool_value": cap.bool_value,
                    "unit": cap.unit,
                    "notes": cap.notes,
                },
            )

    def _load_capabilities_map(self, conn, machine_ids: list[str]) -> dict[str, list[MachineCapabilityResponse]]:
        if not machine_ids:
            return {}
        quoted_ids = ", ".join(f"'{mid}'" for mid in machine_ids if mid)
        if not quoted_ids:
            return {}
        stmt = text(
            f"""
            SELECT
                [capability_id], [machine_id], [capability_code], [capability_value], [numeric_value],
                [bool_value], [unit], [notes], [created_at], [updated_at]
            FROM [Cedule].[dbo].[40_VENTES_SOUSTRAITANCE_machine_capabilities]
            WHERE [machine_id] IN ({quoted_ids})
            ORDER BY [capability_code] ASC
            """
        )
        rows = conn.execute(stmt).mappings().all()
        grouped: dict[str, list[MachineCapabilityResponse]] = {}
        for row in rows:
            machine_id = str(row.get("machine_id"))
            grouped.setdefault(machine_id, []).append(self._to_machine_capability(row))
        return grouped

    def save_generated_routings(
        self,
        part_id: UUID,
        scenarios_payload: dict[str, Any],
        *,
        run_id: UUID | None = None,
    ) -> list[RoutingResponse]:
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
            self._save_routing_llm_metadata(
                routing_id=routing.routing_id,
                run_id=run_id,
                scenario=scenario,
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

    def _save_routing_llm_metadata(self, *, routing_id: UUID, run_id: UUID | None, scenario: dict[str, Any]) -> None:
        if not self._engine:
            raise DatabaseError("Cedule database not configured")
        assumptions = scenario.get("assumptions")
        unknowns = scenario.get("unknowns")
        assumptions_payload = assumptions if isinstance(assumptions, (list, dict)) else None
        unknowns_payload = unknowns if isinstance(unknowns, (list, dict)) else None
        confidence_score = _safe_float(scenario.get("confidence_score"), default=None)
        if confidence_score is not None:
            if confidence_score > 1 and confidence_score <= 100:
                confidence_score = confidence_score / 100.0
            confidence_score = max(0.0, min(1.0, confidence_score))
        stmt = text(
            """
            UPDATE [Cedule].[dbo].[40_VENTES_SOUSTRAITANCE_part_routings]
            SET
                [confidence_score] = :confidence_score,
                [assumptions_json] = :assumptions_json,
                [unknowns_json] = :unknowns_json,
                [source_run_id] = :source_run_id
            WHERE [routing_id] = :routing_id
            """
        )
        try:
            with self._engine.begin() as conn:
                conn.execute(
                    stmt,
                    {
                        "routing_id": str(routing_id),
                        "confidence_score": confidence_score,
                        "assumptions_json": json.dumps(assumptions_payload, ensure_ascii=True)
                        if assumptions_payload is not None
                        else None,
                        "unknowns_json": json.dumps(unknowns_payload, ensure_ascii=True)
                        if unknowns_payload is not None
                        else None,
                        "source_run_id": str(run_id) if run_id else None,
                    },
                )
        except SQLAlchemyError as exc:
            if _is_missing_column_error(exc) or _is_missing_table_error(exc):
                logger.warning(
                    "Routing metadata columns are missing. Run docs/ventes_sous_traitance_llm_feature_schema.sql to enable scenario metadata."
                )
                return
            logger.error("Failed to save routing scenario metadata", exc_info=exc)
            raise DatabaseError("Unable to save routing scenario metadata") from exc

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
        output_json = row.get("output_json")
        output_json_text: str | None
        if output_json is None:
            output_json_text = None
        elif isinstance(output_json, str):
            output_json_text = output_json
        else:
            output_json_text = json.dumps(_sanitize_json_value(output_json), ensure_ascii=True, default=str)
        parsed_output: dict[str, Any] = {}
        if isinstance(output_json, dict):
            parsed_output = output_json
        elif isinstance(output_json, str):
            try:
                parsed = json.loads(output_json)
                if isinstance(parsed, dict):
                    parsed_output = parsed
            except json.JSONDecodeError:
                parsed_output = {}

        created_part_id = None
        raw_created_part_id = parsed_output.get("created_part_id")
        if raw_created_part_id:
            try:
                created_part_id = UUID(str(raw_created_part_id))
            except (TypeError, ValueError):
                created_part_id = None

        created_feature_set_id = None
        raw_feature_set_id = parsed_output.get("created_feature_set_id")
        if raw_feature_set_id:
            try:
                created_feature_set_id = UUID(str(raw_feature_set_id))
            except (TypeError, ValueError):
                created_feature_set_id = None

        created_routing_ids: list[UUID] = []
        raw_routing_ids = parsed_output.get("created_routing_ids")
        if isinstance(raw_routing_ids, list):
            for raw_routing_id in raw_routing_ids:
                try:
                    created_routing_ids.append(UUID(str(raw_routing_id)))
                except (TypeError, ValueError):
                    continue

        return JobStatusResponse(
            job_id=UUID(str(row.get("run_id"))),
            status=status,
            stage=str(row.get("stage") or "routing"),
            progress=progress,
            started_at=row.get("started_at"),
            ended_at=row.get("ended_at"),
            error_text=row.get("error_text"),
            output_json=output_json_text,
            created_part_id=created_part_id,
            created_routing_ids=created_routing_ids,
            created_feature_set_id=created_feature_set_id,
        )

    def _upsert_part_feature_set_header(
        self,
        *,
        part_id: UUID,
        source: str,
        source_run_id: UUID | None,
        feature_confidence: Decimal | None,
        part_summary: dict[str, Any] | None,
        additional_operations: list[str] | None,
        general_notes: list[str] | None,
    ) -> None:
        if not self._engine:
            raise DatabaseError("Cedule database not configured")
        stmt = text(
            """
            MERGE [Cedule].[dbo].[40_VENTES_SOUSTRAITANCE_part_feature_sets] AS target
            USING (SELECT :part_id AS [part_id]) AS source
            ON target.[part_id] = source.[part_id]
            WHEN MATCHED THEN
                UPDATE SET
                    [source] = COALESCE(:source, target.[source]),
                    [source_run_id] = COALESCE(:source_run_id, target.[source_run_id]),
                    [feature_confidence] = COALESCE(:feature_confidence, target.[feature_confidence]),
                    [part_summary_json] = COALESCE(:part_summary_json, target.[part_summary_json]),
                    [additional_operations_json] = COALESCE(:additional_operations_json, target.[additional_operations_json]),
                    [general_notes_json] = COALESCE(:general_notes_json, target.[general_notes_json]),
                    [updated_at] = SYSUTCDATETIME()
            WHEN NOT MATCHED THEN
                INSERT (
                    [feature_set_id],
                    [part_id],
                    [source],
                    [source_run_id],
                    [feature_confidence],
                    [part_summary_json],
                    [additional_operations_json],
                    [general_notes_json]
                )
                VALUES (
                    :feature_set_id,
                    :part_id,
                    :source,
                    :source_run_id,
                    :feature_confidence,
                    :part_summary_json,
                    :additional_operations_json,
                    :general_notes_json
                );
            """
        )
        try:
            with self._engine.begin() as conn:
                conn.execute(
                    stmt,
                    {
                        "feature_set_id": str(uuid4()),
                        "part_id": str(part_id),
                        "source": source,
                        "source_run_id": str(source_run_id) if source_run_id else None,
                        "feature_confidence": feature_confidence,
                        "part_summary_json": json.dumps(part_summary, ensure_ascii=True) if part_summary is not None else None,
                        "additional_operations_json": json.dumps(additional_operations, ensure_ascii=True)
                        if additional_operations is not None
                        else None,
                        "general_notes_json": json.dumps(general_notes, ensure_ascii=True) if general_notes is not None else None,
                    },
                )
        except SQLAlchemyError as exc:
            if _is_missing_table_error(exc):
                raise DatabaseError(
                    "Part feature tables are missing. Run docs/ventes_sous_traitance_llm_feature_schema.sql first."
                ) from exc
            logger.error("Failed to upsert part feature set header", exc_info=exc)
            raise DatabaseError("Unable to upsert part feature set header") from exc

    def _get_part_feature(self, feature_id: UUID) -> Optional[PartFeatureResponse]:
        if not self._engine:
            raise DatabaseError("Cedule database not configured")
        stmt = text(
            """
            SELECT
                [feature_id],
                [part_id],
                [source],
                [source_run_id],
                [feature_ref],
                [feature_type],
                [description],
                [quantity],
                [width_mm],
                [length_mm],
                [depth_mm],
                [diameter_mm],
                [thread_spec],
                [tolerance_note],
                [surface_finish_ra_um],
                [location_note],
                [complexity_factors_json],
                [estimated_operation_time_min],
                [is_user_override],
                [created_at],
                [updated_at]
            FROM [Cedule].[dbo].[40_VENTES_SOUSTRAITANCE_part_features]
            WHERE [feature_id] = :feature_id
            """
        )
        try:
            with self._engine.connect() as conn:
                row = conn.execute(stmt, {"feature_id": str(feature_id)}).mappings().first()
        except SQLAlchemyError as exc:
            if _is_missing_table_error(exc):
                raise DatabaseError(
                    "Part feature tables are missing. Run docs/ventes_sous_traitance_llm_feature_schema.sql first."
                ) from exc
            logger.error("Failed to fetch part feature", exc_info=exc)
            raise DatabaseError("Unable to fetch part feature") from exc
        return self._to_part_feature(row) if row else None

    @staticmethod
    def _json_load_object(value: Any) -> Optional[dict[str, Any]]:
        if not value:
            return None
        if isinstance(value, dict):
            return value
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
            except json.JSONDecodeError:
                return None
            return parsed if isinstance(parsed, dict) else None
        return None

    @staticmethod
    def _json_load_string_list(value: Any) -> list[str]:
        if not value:
            return []
        if isinstance(value, list):
            return [str(v) for v in value if v is not None]
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
            except json.JSONDecodeError:
                return []
            if isinstance(parsed, list):
                return [str(v) for v in parsed if v is not None]
        return []

    @staticmethod
    def _json_load_any(value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, (dict, list)):
            return value
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return value

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
            ship_to_address=row.get("ship_to_address"),
            contact_name=row.get("contact_name"),
            global_quote_comment=row.get("global_quote_comment"),
            created_at=row.get("created_at"),
        )

    def _to_machine_group(self, row: dict[str, Any]) -> MachineGroupSummary:
        return MachineGroupSummary(
            machine_group_id=str(row.get("machine_group_id") or ""),
            name=str(row.get("name") or ""),
            process_families_json=row.get("process_families_json"),
            config_json=row.get("config_json"),
            updated_at=row.get("updated_at"),
        )

    def _to_machine_capability(self, row: dict[str, Any]) -> MachineCapabilityResponse:
        return MachineCapabilityResponse(
            capability_id=UUID(str(row.get("capability_id"))),
            machine_id=UUID(str(row.get("machine_id"))),
            capability_code=str(row.get("capability_code") or ""),
            capability_value=row.get("capability_value"),
            numeric_value=Decimal(str(row["numeric_value"])) if row.get("numeric_value") is not None else None,
            bool_value=bool(row.get("bool_value")) if row.get("bool_value") is not None else None,
            unit=row.get("unit"),
            notes=row.get("notes"),
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at"),
        )

    def _to_machine_capability_option_entry(self, row: dict[str, Any]) -> MachineCapabilityOptionEntry:
        return MachineCapabilityOptionEntry(
            option_id=UUID(str(row.get("option_id"))),
            capability_code=str(row.get("capability_code") or ""),
            capability_value=row.get("capability_value"),
            unit=row.get("unit"),
            is_active=bool(row.get("is_active")),
            notes=row.get("notes"),
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at"),
        )

    def _to_machine(self, row: dict[str, Any], capabilities: list[MachineCapabilityResponse]) -> MachineResponse:
        return MachineResponse(
            machine_id=UUID(str(row.get("machine_id"))),
            machine_code=str(row.get("machine_code") or ""),
            machine_name=str(row.get("machine_name") or ""),
            machine_group_id=row.get("machine_group_id"),
            is_active=bool(row.get("is_active")),
            default_setup_time_min=Decimal(str(row.get("default_setup_time_min") or "0")),
            default_runtime_min=Decimal(str(row.get("default_runtime_min") or "0")),
            envelope_x_mm=Decimal(str(row["envelope_x_mm"])) if row.get("envelope_x_mm") is not None else None,
            envelope_y_mm=Decimal(str(row["envelope_y_mm"])) if row.get("envelope_y_mm") is not None else None,
            envelope_z_mm=Decimal(str(row["envelope_z_mm"])) if row.get("envelope_z_mm") is not None else None,
            max_part_weight_kg=Decimal(str(row["max_part_weight_kg"])) if row.get("max_part_weight_kg") is not None else None,
            notes=row.get("notes"),
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at"),
            capabilities=capabilities,
        )

    def _to_quote_part(self, row: dict[str, Any]) -> QuotePartSummary:
        return QuotePartSummary(
            part_id=UUID(str(row.get("part_id"))),
            quote_id=UUID(str(row.get("quote_id"))),
            customer_part_number=row.get("customer_part_number"),
            internal_part_number=row.get("internal_part_number"),
            quantity=_safe_int(row.get("quantity"), default=1),
            material=row.get("material"),
            thickness_mm=Decimal(str(row["thickness_mm"])) if row.get("thickness_mm") is not None else None,
            weight_kg=Decimal(str(row["weight_kg"])) if row.get("weight_kg") is not None else None,
            envelope_x_mm=Decimal(str(row["envelope_x_mm"])) if row.get("envelope_x_mm") is not None else None,
            envelope_y_mm=Decimal(str(row["envelope_y_mm"])) if row.get("envelope_y_mm") is not None else None,
            envelope_z_mm=Decimal(str(row["envelope_z_mm"])) if row.get("envelope_z_mm") is not None else None,
            shape=row.get("shape"),
            complexity_score=_safe_int(row.get("complexity_score"), default=0) or None,
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at"),
        )

    def _to_part_feature(self, row: dict[str, Any]) -> PartFeatureResponse:
        source = str(row.get("source") or "llm").lower()
        if source not in {"llm", "rules", "user"}:
            source = "llm"
        return PartFeatureResponse(
            feature_id=UUID(str(row.get("feature_id"))),
            part_id=UUID(str(row.get("part_id"))),
            source=source,
            source_run_id=UUID(str(row.get("source_run_id"))) if row.get("source_run_id") else None,
            feature_ref=row.get("feature_ref"),
            feature_type=str(row.get("feature_type") or "unknown"),
            description=row.get("description"),
            quantity=int(row.get("quantity") or 1),
            width_mm=Decimal(str(row["width_mm"])) if row.get("width_mm") is not None else None,
            length_mm=Decimal(str(row["length_mm"])) if row.get("length_mm") is not None else None,
            depth_mm=Decimal(str(row["depth_mm"])) if row.get("depth_mm") is not None else None,
            diameter_mm=Decimal(str(row["diameter_mm"])) if row.get("diameter_mm") is not None else None,
            thread_spec=row.get("thread_spec"),
            tolerance_note=row.get("tolerance_note"),
            surface_finish_ra_um=Decimal(str(row["surface_finish_ra_um"])) if row.get("surface_finish_ra_um") is not None else None,
            location_note=row.get("location_note"),
            complexity_factors=self._json_load_string_list(row.get("complexity_factors_json")),
            estimated_operation_time_min=(
                Decimal(str(row["estimated_operation_time_min"]))
                if row.get("estimated_operation_time_min") is not None
                else None
            ),
            is_user_override=bool(row.get("is_user_override")),
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at"),
        )

    def _to_routing(self, row: dict[str, Any]) -> RoutingResponse:
        return RoutingResponse(
            routing_id=UUID(str(row.get("routing_id"))),
            part_id=UUID(str(row.get("part_id"))),
            scenario_name=str(row.get("scenario_name") or ""),
            created_by=row.get("created_by"),
            selected=bool(row.get("selected")),
            rationale=row.get("rationale"),
            confidence_score=Decimal(str(row["confidence_score"])) if row.get("confidence_score") is not None else None,
            assumptions_json=self._json_load_any(row.get("assumptions_json")),
            unknowns_json=self._json_load_any(row.get("unknowns_json")),
            source_run_id=UUID(str(row.get("source_run_id"))) if row.get("source_run_id") else None,
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

"""Repository for Cedule Service tables."""

from __future__ import annotations

from typing import List, Optional
from datetime import date, datetime
import logging

from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from app.domain.service.models import (
    ServiceDivision,
    ServiceEquipement,
    ServiceModele,
    ServiceItem,
    ServiceItemCreateRequest,
    ServiceItemCreateResponse,
    ServiceItemOptionalField,
    ServiceItemOptionalFieldType,
)
from app.errors import DatabaseError
from app.integrations.cedule_repository import get_cedule_engine

logger = logging.getLogger(__name__)


class CeduleServiceRepository:
    """Read-only access to Cedule Service_* tables."""

    def __init__(self, engine: Optional[Engine] = None) -> None:
        self._engine = engine or get_cedule_engine()

    @property
    def is_configured(self) -> bool:
        return self._engine is not None

    def list_divisions(self) -> List[ServiceDivision]:
        if not self._engine:
            raise DatabaseError("Cedule database not configured")

        query = text(
            """
            SELECT
                Id AS id,
                Descr AS description
            FROM [Cedule].[dbo].[Service_Division]
            ORDER BY Id
            """
        )
        try:
            with self._engine.connect() as connection:
                rows = connection.execute(query).mappings().all()
        except SQLAlchemyError as exc:
            logger.error("Failed to query Service_Division", exc_info=exc)
            raise DatabaseError("Unable to query Service_Division") from exc

        return [
            ServiceDivision(
                id=_safe_int(row.get("id")) or 0,
                description=_clean_str(row.get("description")),
            )
            for row in rows
        ]

    def list_equipements(self, division_id: Optional[int] = None) -> List[ServiceEquipement]:
        if not self._engine:
            raise DatabaseError("Cedule database not configured")

        params = {}
        where_clause = ""
        if division_id is not None:
            where_clause = "WHERE DivisionId = :division_id"
            params["division_id"] = division_id

        query = text(
            f"""
            SELECT
                Id AS id,
                DescEquipement AS description,
                DivisionId AS division_id
            FROM [Cedule].[dbo].[Service_Equipement]
            {where_clause}
            ORDER BY Id
            """
        )
        try:
            with self._engine.connect() as connection:
                rows = connection.execute(query, params).mappings().all()
        except SQLAlchemyError as exc:
            logger.error("Failed to query Service_Equipement", exc_info=exc)
            raise DatabaseError("Unable to query Service_Equipement") from exc

        return [
            ServiceEquipement(
                id=_clean_str(row.get("id")) or "",
                description=_clean_str(row.get("description")),
                division_id=_safe_int(row.get("division_id")),
            )
            for row in rows
        ]

    def list_modeles(self, equipement_id: Optional[int] = None) -> List[ServiceModele]:
        if not self._engine:
            raise DatabaseError("Cedule database not configured")

        params = {}
        where_clause = ""
        if equipement_id is not None:
            where_clause = "WHERE EquipementId = :equipement_id"
            params["equipement_id"] = equipement_id

        query = text(
            f"""
            SELECT
                Id AS id,
                DescModele AS description,
                EquipementId AS equipement_id
            FROM [Cedule].[dbo].[Service_Modele]
            {where_clause}
            ORDER BY Id
            """
        )
        try:
            with self._engine.connect() as connection:
                rows = connection.execute(query, params).mappings().all()
        except SQLAlchemyError as exc:
            logger.error("Failed to query Service_Modele", exc_info=exc)
            raise DatabaseError("Unable to query Service_Modele") from exc

        return [
            ServiceModele(
                id=_clean_str(row.get("id")) or "",
                description=_clean_str(row.get("description")),
                equipement_id=_clean_str(row.get("equipement_id")),
            )
            for row in rows
        ]

    def list_service_items(
        self,
        customer_id: Optional[str] = None,
        service_item_id: Optional[int] = None,
    ) -> List[ServiceItem]:
        if not self._engine:
            raise DatabaseError("Cedule database not configured")

        params = {}
        filters = []
        if customer_id:
            params["customer_id"] = customer_id.strip()
            filters.append("RTRIM(LTRIM(CustomerID)) = :customer_id")
        if service_item_id is not None:
            params["service_item_id"] = service_item_id
            filters.append("ServiceItemID = :service_item_id")

        where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""

        query = text(
            f"""
            SELECT
                ServiceItemID AS service_item_id,
                CustomerID AS customer_id,
                ShipToID AS ship_to_id,
                Equipement AS equipement_id,
                Modele AS modele_id,
                NoSerie AS no_serie,
                GIM AS gim,
                DateLivraison AS date_livraison,
                DateConfirmee AS date_confirmee,
                Manuel AS manuel,
                DateStartup AS date_startup,
                GarantieMois AS garantie_mois,
                RapportISO AS rapport_iso
            FROM [Cedule].[dbo].[Service_ServiceItem]
            {where_clause}
            ORDER BY ServiceItemID
            """
        )
        try:
            with self._engine.connect() as connection:
                rows = connection.execute(query, params).mappings().all()
        except SQLAlchemyError as exc:
            logger.error("Failed to query Service_ServiceItem", exc_info=exc)
            raise DatabaseError("Unable to query Service_ServiceItem") from exc

        items: List[ServiceItem] = []
        for row in rows:
            items.append(
                ServiceItem(
                    service_item_id=row.get("service_item_id"),
                    customer_id=_clean_str(row.get("customer_id")) or "",
                    ship_to_id=_clean_str(row.get("ship_to_id")),
                    equipement_id=_clean_str(row.get("equipement_id")),
                    modele_id=_clean_str(row.get("modele_id")),
                    no_serie=_clean_str(row.get("no_serie")),
                    gim=_clean_str(row.get("gim")),
                    date_livraison=_safe_date(row.get("date_livraison")),
                    date_confirmee=_safe_bool(row.get("date_confirmee")),
                    manuel=_clean_str(row.get("manuel")),
                    date_startup=_safe_date(row.get("date_startup")),
                    garantie_mois=_safe_int(row.get("garantie_mois")),
                    rapport_iso=_clean_str(row.get("rapport_iso")),
                )
            )
        return items

    def list_optional_fields(
        self,
        service_item_id: Optional[int] = None,
        field_type: Optional[str] = None,
    ) -> List[ServiceItemOptionalField]:
        if not self._engine:
            raise DatabaseError("Cedule database not configured")

        params = {}
        filters = []
        if service_item_id is not None:
            params["service_item_id"] = service_item_id
            filters.append("ServiceItemId = :service_item_id")
        if field_type:
            params["field_type"] = field_type.strip()
            filters.append("Type = :field_type")

        where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""

        query = text(
            f"""
            SELECT
                Id AS id,
                ServiceItemId AS service_item_id,
                Type AS field_type,
                Attribut1 AS attribute1,
                Attribut2 AS attribute2,
                Attribut3 AS attribute3,
                Attribut4 AS attribute4
            FROM [Cedule].[dbo].[Service_ServItemOptionalFields]
            {where_clause}
            ORDER BY Id
            """
        )
        try:
            with self._engine.connect() as connection:
                rows = connection.execute(query, params).mappings().all()
        except SQLAlchemyError as exc:
            logger.error("Failed to query Service_ServItemOptionalFields", exc_info=exc)
            raise DatabaseError("Unable to query Service_ServItemOptionalFields") from exc

        return [
            ServiceItemOptionalField(
                id=row.get("id"),
                service_item_id=row.get("service_item_id"),
                field_type=_clean_str(row.get("field_type")),
                attribute1=_clean_str(row.get("attribute1")),
                attribute2=_clean_str(row.get("attribute2")),
                attribute3=_clean_str(row.get("attribute3")),
                attribute4=_clean_str(row.get("attribute4")),
            )
            for row in rows
        ]

    def list_optional_field_types(
        self,
        equipment: Optional[str] = None,
        field_type: Optional[str] = None,
    ) -> List[ServiceItemOptionalFieldType]:
        if not self._engine:
            raise DatabaseError("Cedule database not configured")

        params = {}
        filters = []
        if equipment:
            params["equipment"] = equipment.strip()
            filters.append("Equipment = :equipment")
        if field_type:
            params["field_type"] = field_type.strip()
            filters.append("Type = :field_type")

        where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""

        query = text(
            f"""
            SELECT
                Type AS field_type,
                Attribut1Header AS attribute1_header,
                Attribut2Header AS attribute2_header,
                Attibut3Header AS attribute3_header,
                Attribut4Header AS attribute4_header,
                Equipment AS equipment
            FROM [Cedule].[dbo].[Service_ServItemOptionalFTypes]
            {where_clause}
            ORDER BY Type
            """
        )
        try:
            with self._engine.connect() as connection:
                rows = connection.execute(query, params).mappings().all()
        except SQLAlchemyError as exc:
            logger.error("Failed to query Service_ServItemOptionalFTypes", exc_info=exc)
            raise DatabaseError("Unable to query Service_ServItemOptionalFTypes") from exc

        return [
            ServiceItemOptionalFieldType(
                field_type=_clean_str(row.get("field_type")) or "",
                attribute1_header=_clean_str(row.get("attribute1_header")),
                attribute2_header=_clean_str(row.get("attribute2_header")),
                attribute3_header=_clean_str(row.get("attribute3_header")),
                attribute4_header=_clean_str(row.get("attribute4_header")),
                equipment=_clean_str(row.get("equipment")),
            )
            for row in rows
        ]

    def create_service_item(self, payload: ServiceItemCreateRequest) -> ServiceItemCreateResponse:
        if not self._engine:
            raise DatabaseError("Cedule database not configured")

        params = {
            "customer_id": payload.customer_id.strip(),
            "ship_to_id": _clean_str(payload.ship_to_id),
            "equipement_id": payload.equipement_id.strip(),
            "modele_id": _clean_str(payload.modele_id),
            "no_serie": _clean_str(payload.no_serie),
            "gim": _clean_str(payload.gim),
            "date_livraison": payload.date_livraison,
            "date_confirmee": 1 if payload.date_confirmee else 0,
            "manuel": _clean_str(payload.manuel),
            "date_startup": payload.date_startup,
            "garantie_mois": payload.garantie_mois,
            "rapport_iso": _clean_str(payload.rapport_iso),
        }

        insert_item_query = text(
            """
            INSERT INTO [Cedule].[dbo].[Service_ServiceItem] (
                CustomerID,
                ShipToID,
                Equipement,
                Modele,
                NoSerie,
                GIM,
                DateLivraison,
                DateConfirmee,
                Manuel,
                DateStartup,
                GarantieMois,
                RapportISO
            )
            OUTPUT
                INSERTED.ServiceItemID AS service_item_id,
                INSERTED.CustomerID AS customer_id,
                INSERTED.ShipToID AS ship_to_id,
                INSERTED.Equipement AS equipement_id,
                INSERTED.Modele AS modele_id,
                INSERTED.NoSerie AS no_serie,
                INSERTED.GIM AS gim,
                INSERTED.DateLivraison AS date_livraison,
                INSERTED.DateConfirmee AS date_confirmee,
                INSERTED.Manuel AS manuel,
                INSERTED.DateStartup AS date_startup,
                INSERTED.GarantieMois AS garantie_mois,
                INSERTED.RapportISO AS rapport_iso
            VALUES (
                :customer_id,
                :ship_to_id,
                :equipement_id,
                :modele_id,
                :no_serie,
                :gim,
                :date_livraison,
                :date_confirmee,
                :manuel,
                :date_startup,
                :garantie_mois,
                :rapport_iso
            )
            """
        )

        optional_fields: List[ServiceItemOptionalField] = []

        try:
            with self._engine.begin() as connection:
                item_row = connection.execute(insert_item_query, params).mappings().first()
                if not item_row:
                    raise DatabaseError("Failed to create service item")

                service_item_id = item_row.get("service_item_id")
                for entry in payload.optional_fields:
                    field_params = {
                        "service_item_id": service_item_id,
                        "field_type": entry.field_type.strip(),
                        "attribute1": _clean_str(entry.attribute1),
                        "attribute2": _clean_str(entry.attribute2),
                        "attribute3": _clean_str(entry.attribute3),
                        "attribute4": _clean_str(entry.attribute4),
                    }
                    insert_field_query = text(
                        """
                        INSERT INTO [Cedule].[dbo].[Service_ServItemOptionalFields] (
                            Attribut1,
                            Attribut2,
                            Attribut3,
                            Attribut4,
                            ServiceItemId,
                            Type
                        )
                        OUTPUT
                            INSERTED.Id AS id,
                            INSERTED.ServiceItemId AS service_item_id,
                            INSERTED.Type AS field_type,
                            INSERTED.Attribut1 AS attribute1,
                            INSERTED.Attribut2 AS attribute2,
                            INSERTED.Attribut3 AS attribute3,
                            INSERTED.Attribut4 AS attribute4
                        VALUES (
                            :attribute1,
                            :attribute2,
                            :attribute3,
                            :attribute4,
                            :service_item_id,
                            :field_type
                        )
                        """
                    )
                    field_row = connection.execute(insert_field_query, field_params).mappings().first()
                    if field_row:
                        optional_fields.append(
                            ServiceItemOptionalField(
                                id=field_row.get("id"),
                                service_item_id=field_row.get("service_item_id"),
                                field_type=_clean_str(field_row.get("field_type")),
                                attribute1=_clean_str(field_row.get("attribute1")),
                                attribute2=_clean_str(field_row.get("attribute2")),
                                attribute3=_clean_str(field_row.get("attribute3")),
                                attribute4=_clean_str(field_row.get("attribute4")),
                            )
                        )
        except SQLAlchemyError as exc:
            logger.error("Failed to create service item", exc_info=exc, extra={"customer_id": payload.customer_id})
            raise DatabaseError("Unable to create service item") from exc

        created_item = ServiceItem(
            service_item_id=item_row.get("service_item_id"),
            customer_id=_clean_str(item_row.get("customer_id")) or "",
            ship_to_id=_clean_str(item_row.get("ship_to_id")),
            equipement_id=_clean_str(item_row.get("equipement_id")),
            modele_id=_clean_str(item_row.get("modele_id")),
            no_serie=_clean_str(item_row.get("no_serie")),
            gim=_clean_str(item_row.get("gim")),
            date_livraison=_safe_date(item_row.get("date_livraison")),
            date_confirmee=_safe_bool(item_row.get("date_confirmee")),
            manuel=_clean_str(item_row.get("manuel")),
            date_startup=_safe_date(item_row.get("date_startup")),
            garantie_mois=_safe_int(item_row.get("garantie_mois")),
            rapport_iso=_clean_str(item_row.get("rapport_iso")),
        )

        return ServiceItemCreateResponse(service_item=created_item, optional_fields=optional_fields)

    def fetch_customer_asset_rows(self, customer_id: str) -> List[dict]:
        if not self._engine:
            raise DatabaseError("Cedule database not configured")

        cleaned_customer = customer_id.strip()
        query = text(
            """
            SELECT
                s.ServiceItemID AS service_item_id,
                s.CustomerID AS customer_id,
                s.ShipToID AS ship_to_id,
                s.Equipement AS equipement_id,
                e.DescEquipement AS equipement_description,
                e.DivisionId AS division_id,
                d.Descr AS division_description,
                s.Modele AS modele_id,
                m.DescModele AS modele_description,
                s.NoSerie AS no_serie,
                s.GIM AS gim,
                s.DateLivraison AS date_livraison,
                s.DateConfirmee AS date_confirmee,
                s.Manuel AS manuel,
                s.DateStartup AS date_startup,
                s.GarantieMois AS garantie_mois,
                s.RapportISO AS rapport_iso,
                o.Id AS optional_field_id,
                o.Type AS optional_field_type,
                o.Attribut1 AS attribute1,
                o.Attribut2 AS attribute2,
                o.Attribut3 AS attribute3,
                o.Attribut4 AS attribute4,
                t.Attribut1Header AS attribute1_header,
                t.Attribut2Header AS attribute2_header,
                t.Attibut3Header AS attribute3_header,
                t.Attribut4Header AS attribute4_header,
                t.Equipment AS optional_field_equipment
            FROM [Cedule].[dbo].[Service_ServiceItem] AS s
            LEFT JOIN [Cedule].[dbo].[Service_Equipement] AS e
                ON e.Id = s.Equipement
            LEFT JOIN [Cedule].[dbo].[Service_Division] AS d
                ON d.Id = e.DivisionId
            LEFT JOIN [Cedule].[dbo].[Service_Modele] AS m
                ON m.Id = s.Modele
            LEFT JOIN [Cedule].[dbo].[Service_ServItemOptionalFields] AS o
                ON o.ServiceItemId = s.ServiceItemID
            LEFT JOIN [Cedule].[dbo].[Service_ServItemOptionalFTypes] AS t
                ON t.Type = o.Type
            WHERE RTRIM(LTRIM(s.CustomerID)) = :customer_id
            ORDER BY s.ServiceItemID, o.Id
            """
        )

        try:
            with self._engine.connect() as connection:
                rows = connection.execute(query, {"customer_id": cleaned_customer}).mappings().all()
        except SQLAlchemyError as exc:
            logger.error(
                "Failed to query service assets by customer",
                exc_info=exc,
                extra={"customer_id": cleaned_customer},
            )
            raise DatabaseError("Unable to query service assets") from exc

        return [dict(row) for row in rows]


def _clean_str(value: Optional[object]) -> Optional[str]:
    if value is None:
        return None
    text_value = str(value).strip()
    return text_value or None


def _safe_int(value: Optional[object]) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _safe_date(value: Optional[object]) -> Optional[date]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        cleaned = value.strip()
        if not cleaned:
            return None
        if cleaned in {"0000-00-00", "0000-00-00 00:00:00"}:
            return None
        try:
            return datetime.fromisoformat(cleaned).date()
        except ValueError:
            pass
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f", "%m/%d/%Y"):
            try:
                return datetime.strptime(cleaned, fmt).date()
            except ValueError:
                continue
    return None


def _safe_bool(value: Optional[object]) -> Optional[bool]:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        cleaned = value.strip().lower()
        if cleaned in {"true", "t", "yes", "y", "1"}:
            return True
        if cleaned in {"false", "f", "no", "n", "0"}:
            return False
    return None


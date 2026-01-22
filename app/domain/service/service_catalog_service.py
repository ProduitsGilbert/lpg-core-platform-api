"""Service catalog and asset lookup for Cedule Service tables."""

from __future__ import annotations

from typing import Dict, List, Optional

from app.domain.service.models import (
    ServiceDivision,
    ServiceEquipement,
    ServiceModele,
    ServiceItem,
    ServiceItemCreateRequest,
    ServiceItemCreateResponse,
    ServiceItemAsset,
    ServiceItemOptionalField,
    ServiceItemOptionalFieldDetail,
    ServiceItemOptionalFieldType,
)
from app.integrations.cedule_service_repository import (
    CeduleServiceRepository,
    _clean_str,
    _safe_int,
    _safe_date,
    _safe_bool,
)


class ServiceCatalogService:
    def __init__(self, repository: Optional[CeduleServiceRepository] = None) -> None:
        self._repository = repository or CeduleServiceRepository()

    @property
    def is_configured(self) -> bool:
        return self._repository.is_configured

    def list_divisions(self) -> List[ServiceDivision]:
        return self._repository.list_divisions()

    def list_equipements(self, division_id: Optional[int] = None) -> List[ServiceEquipement]:
        return self._repository.list_equipements(division_id=division_id)

    def list_modeles(self, equipement_id: Optional[int] = None) -> List[ServiceModele]:
        return self._repository.list_modeles(equipement_id=equipement_id)

    def list_service_items(
        self,
        customer_id: Optional[str] = None,
        service_item_id: Optional[int] = None,
    ) -> List[ServiceItem]:
        return self._repository.list_service_items(
            customer_id=customer_id,
            service_item_id=service_item_id,
        )

    def list_optional_fields(
        self,
        service_item_id: Optional[int] = None,
        field_type: Optional[str] = None,
    ) -> List[ServiceItemOptionalField]:
        return self._repository.list_optional_fields(
            service_item_id=service_item_id,
            field_type=field_type,
        )

    def list_optional_field_types(
        self,
        equipment: Optional[str] = None,
        field_type: Optional[str] = None,
    ) -> List[ServiceItemOptionalFieldType]:
        return self._repository.list_optional_field_types(
            equipment=equipment,
            field_type=field_type,
        )

    def create_service_item(self, payload: ServiceItemCreateRequest) -> ServiceItemCreateResponse:
        return self._repository.create_service_item(payload)

    def get_customer_assets(self, customer_id: str) -> List[ServiceItemAsset]:
        rows = self._repository.fetch_customer_asset_rows(customer_id)
        assets: Dict[int, ServiceItemAsset] = {}

        for row in rows:
            service_item_id = row.get("service_item_id")
            if service_item_id is None:
                continue

            if service_item_id not in assets:
                assets[service_item_id] = ServiceItemAsset(
                    service_item_id=service_item_id,
                    customer_id=_clean_str(row.get("customer_id")) or "",
                    ship_to_id=_clean_str(row.get("ship_to_id")),
                    equipement_id=_clean_str(row.get("equipement_id")),
                    equipement_description=_clean_str(row.get("equipement_description")),
                    division_id=_safe_int(row.get("division_id")),
                    division_description=_clean_str(row.get("division_description")),
                    modele_id=_clean_str(row.get("modele_id")),
                    modele_description=_clean_str(row.get("modele_description")),
                    no_serie=_clean_str(row.get("no_serie")),
                    gim=_clean_str(row.get("gim")),
                    date_livraison=_safe_date(row.get("date_livraison")),
                    date_confirmee=_safe_bool(row.get("date_confirmee")),
                    manuel=_clean_str(row.get("manuel")),
                    date_startup=_safe_date(row.get("date_startup")),
                    garantie_mois=_safe_int(row.get("garantie_mois")),
                    rapport_iso=_clean_str(row.get("rapport_iso")),
                )

            optional_field_id = row.get("optional_field_id")
            if optional_field_id is None:
                continue

            assets[service_item_id].optional_fields.append(
                ServiceItemOptionalFieldDetail(
                    id=optional_field_id,
                    field_type=_clean_str(row.get("optional_field_type")),
                    equipment=_clean_str(row.get("optional_field_equipment")),
                    attribute1=_clean_str(row.get("attribute1")),
                    attribute2=_clean_str(row.get("attribute2")),
                    attribute3=_clean_str(row.get("attribute3")),
                    attribute4=_clean_str(row.get("attribute4")),
                    attribute1_header=_clean_str(row.get("attribute1_header")),
                    attribute2_header=_clean_str(row.get("attribute2_header")),
                    attribute3_header=_clean_str(row.get("attribute3_header")),
                    attribute4_header=_clean_str(row.get("attribute4_header")),
                )
            )

        return list(assets.values())


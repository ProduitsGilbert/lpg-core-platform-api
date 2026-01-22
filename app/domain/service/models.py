"""Service domain models for Cedule Service tables."""

from __future__ import annotations

from datetime import date
from typing import List, Optional

from pydantic import BaseModel, Field
from pydantic.config import ConfigDict


class ServiceDivision(BaseModel):
    id: int
    description: Optional[str] = None


class ServiceEquipement(BaseModel):
    id: str
    description: Optional[str] = None
    division_id: Optional[int] = None


class ServiceModele(BaseModel):
    id: str
    description: Optional[str] = None
    equipement_id: Optional[str] = None


class ServiceItem(BaseModel):
    service_item_id: int
    customer_id: str
    ship_to_id: Optional[str] = None
    equipement_id: Optional[str] = None
    modele_id: Optional[str] = None
    no_serie: Optional[str] = None
    gim: Optional[str] = None
    date_livraison: Optional[date] = None
    date_confirmee: Optional[bool] = None
    manuel: Optional[str] = None
    date_startup: Optional[date] = None
    garantie_mois: Optional[int] = None
    rapport_iso: Optional[str] = None


class ServiceItemOptionalField(BaseModel):
    id: int
    service_item_id: int
    field_type: Optional[str] = None
    attribute1: Optional[str] = None
    attribute2: Optional[str] = None
    attribute3: Optional[str] = None
    attribute4: Optional[str] = None


class ServiceItemOptionalFieldType(BaseModel):
    field_type: str
    attribute1_header: Optional[str] = None
    attribute2_header: Optional[str] = None
    attribute3_header: Optional[str] = None
    attribute4_header: Optional[str] = None
    equipment: Optional[str] = None


class ServiceItemOptionalFieldCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    field_type: str = Field(..., alias="type", min_length=1)
    attribute1: Optional[str] = None
    attribute2: Optional[str] = None
    attribute3: Optional[str] = None
    attribute4: Optional[str] = None


class ServiceItemCreateRequest(BaseModel):
    customer_id: str = Field(..., min_length=1)
    ship_to_id: Optional[str] = None
    equipement_id: str = Field(..., min_length=1)
    modele_id: Optional[str] = None
    no_serie: Optional[str] = None
    gim: Optional[str] = None
    date_livraison: date
    date_confirmee: bool
    manuel: Optional[str] = None
    date_startup: Optional[date] = None
    garantie_mois: Optional[int] = None
    rapport_iso: Optional[str] = None
    optional_fields: List[ServiceItemOptionalFieldCreate] = Field(default_factory=list)


class ServiceItemCreateResponse(BaseModel):
    service_item: ServiceItem
    optional_fields: List[ServiceItemOptionalField] = Field(default_factory=list)


class ServiceItemOptionalFieldDetail(BaseModel):
    id: int
    field_type: Optional[str] = None
    equipment: Optional[str] = None
    attribute1: Optional[str] = None
    attribute2: Optional[str] = None
    attribute3: Optional[str] = None
    attribute4: Optional[str] = None
    attribute1_header: Optional[str] = None
    attribute2_header: Optional[str] = None
    attribute3_header: Optional[str] = None
    attribute4_header: Optional[str] = None


class ServiceItemAsset(BaseModel):
    service_item_id: int
    customer_id: str
    ship_to_id: Optional[str] = None
    equipement_id: Optional[str] = None
    equipement_description: Optional[str] = None
    division_id: Optional[int] = None
    division_description: Optional[str] = None
    modele_id: Optional[str] = None
    modele_description: Optional[str] = None
    no_serie: Optional[str] = None
    gim: Optional[str] = None
    date_livraison: Optional[date] = None
    date_confirmee: Optional[bool] = None
    manuel: Optional[str] = None
    date_startup: Optional[date] = None
    garantie_mois: Optional[int] = None
    rapport_iso: Optional[str] = None
    optional_fields: List[ServiceItemOptionalFieldDetail] = Field(default_factory=list)


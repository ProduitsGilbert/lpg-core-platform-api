"""Service catalog endpoints backed by Cedule Service tables."""

from __future__ import annotations

from functools import lru_cache
from typing import Optional

from fastapi import APIRouter, Depends, Path, Query

from app.api.v1.models import CollectionResponse, ErrorResponse, SingleResponse
from app.domain.service.models import (
    ServiceDivision,
    ServiceEquipement,
    ServiceModele,
    ServiceItem,
    ServiceItemCreateRequest,
    ServiceItemCreateResponse,
    ServiceItemAsset,
    ServiceItemOptionalField,
    ServiceItemOptionalFieldType,
)
from app.domain.service.service_catalog_service import ServiceCatalogService
from app.errors import DatabaseError

router = APIRouter(prefix="/service", tags=["Service"])


@lru_cache(maxsize=1)
def _get_service() -> ServiceCatalogService:
    return ServiceCatalogService()


def get_service() -> ServiceCatalogService:
    service = _get_service()
    if not service.is_configured:
        raise DatabaseError("Cedule database not configured")
    return service


@router.get(
    "/divisions",
    response_model=CollectionResponse[ServiceDivision],
    responses={
        200: {"description": "Service divisions retrieved successfully"},
        503: {"description": "Cedule database unavailable", "model": ErrorResponse},
    },
    summary="List service divisions",
)
async def list_service_divisions(
    service: ServiceCatalogService = Depends(get_service),
) -> CollectionResponse[ServiceDivision]:
    divisions = service.list_divisions()
    return CollectionResponse(data=divisions)


@router.get(
    "/equipements",
    response_model=CollectionResponse[ServiceEquipement],
    responses={
        200: {"description": "Service equipments retrieved successfully"},
        503: {"description": "Cedule database unavailable", "model": ErrorResponse},
    },
    summary="List service equipments",
)
async def list_service_equipements(
    division_id: Optional[int] = Query(
        default=None,
        ge=1,
        description="Optional division id to filter equipments.",
    ),
    service: ServiceCatalogService = Depends(get_service),
) -> CollectionResponse[ServiceEquipement]:
    equipements = service.list_equipements(division_id=division_id)
    return CollectionResponse(data=equipements)


@router.get(
    "/modeles",
    response_model=CollectionResponse[ServiceModele],
    responses={
        200: {"description": "Service models retrieved successfully"},
        503: {"description": "Cedule database unavailable", "model": ErrorResponse},
    },
    summary="List service models",
)
async def list_service_modeles(
    equipement_id: Optional[str] = Query(
        default=None,
        description="Optional equipment id to filter models.",
    ),
    service: ServiceCatalogService = Depends(get_service),
) -> CollectionResponse[ServiceModele]:
    modeles = service.list_modeles(equipement_id=equipement_id)
    return CollectionResponse(data=modeles)


@router.get(
    "/items",
    response_model=CollectionResponse[ServiceItem],
    responses={
        200: {"description": "Service items retrieved successfully"},
        503: {"description": "Cedule database unavailable", "model": ErrorResponse},
    },
    summary="List service items",
)
async def list_service_items(
    customer_id: Optional[str] = Query(
        default=None,
        description="Optional customer id to filter service items.",
    ),
    service_item_id: Optional[int] = Query(
        default=None,
        ge=1,
        description="Optional service item id to filter service items.",
    ),
    service: ServiceCatalogService = Depends(get_service),
) -> CollectionResponse[ServiceItem]:
    items = service.list_service_items(customer_id=customer_id, service_item_id=service_item_id)
    return CollectionResponse(data=items)


@router.post(
    "/items",
    response_model=SingleResponse[ServiceItemCreateResponse],
    status_code=201,
    responses={
        201: {"description": "Service item created successfully"},
        503: {"description": "Cedule database unavailable", "model": ErrorResponse},
    },
    summary="Create a service item",
    description="Create a new service item and optional fields in Cedule.",
)
async def create_service_item(
    payload: ServiceItemCreateRequest,
    service: ServiceCatalogService = Depends(get_service),
) -> SingleResponse[ServiceItemCreateResponse]:
    created = service.create_service_item(payload)
    return SingleResponse(data=created)


@router.get(
    "/items/{service_item_id}/optional-fields",
    response_model=CollectionResponse[ServiceItemOptionalField],
    responses={
        200: {"description": "Service item optional fields retrieved successfully"},
        503: {"description": "Cedule database unavailable", "model": ErrorResponse},
    },
    summary="List optional fields for a service item",
)
async def list_service_item_optional_fields(
    service_item_id: int = Path(..., ge=1, description="Service item id."),
    service: ServiceCatalogService = Depends(get_service),
) -> CollectionResponse[ServiceItemOptionalField]:
    fields = service.list_optional_fields(service_item_id=service_item_id)
    return CollectionResponse(data=fields)


@router.get(
    "/optional-field-types",
    response_model=CollectionResponse[ServiceItemOptionalFieldType],
    responses={
        200: {"description": "Service item optional field types retrieved successfully"},
        503: {"description": "Cedule database unavailable", "model": ErrorResponse},
    },
    summary="List optional field types",
)
async def list_service_optional_field_types(
    equipment: Optional[str] = Query(
        default=None,
        description="Optional equipment description to filter field types.",
    ),
    field_type: Optional[str] = Query(
        default=None,
        description="Optional type to filter field types.",
    ),
    service: ServiceCatalogService = Depends(get_service),
) -> CollectionResponse[ServiceItemOptionalFieldType]:
    types = service.list_optional_field_types(equipment=equipment, field_type=field_type)
    return CollectionResponse(data=types)


@router.get(
    "/customers/{customer_id}/assets",
    response_model=CollectionResponse[ServiceItemAsset],
    responses={
        200: {"description": "Service assets retrieved successfully"},
        503: {"description": "Cedule database unavailable", "model": ErrorResponse},
    },
    summary="List service assets for a customer",
    description=(
        "Return service items for the customer, enriched with division/equipment/model "
        "details and optional field values."
    ),
)
async def list_customer_service_assets(
    customer_id: str = Path(..., min_length=1, description="Customer id."),
    service: ServiceCatalogService = Depends(get_service),
) -> CollectionResponse[ServiceItemAsset]:
    assets = service.get_customer_assets(customer_id)
    return CollectionResponse(data=assets)


from __future__ import annotations

from uuid import uuid4

from app.integrations.cedule_ventes_sous_traitance_repository import (
    CeduleVentesSousTraitanceRepository,
    _normalize_shape,
)


def test_derive_customer_name_from_notes() -> None:
    cid = uuid4()
    notes = "Customer: PRODUITS GILBERT INC.\nContact: Example"
    assert (
        CeduleVentesSousTraitanceRepository._derive_customer_name(cid, notes)
        == "PRODUITS GILBERT INC."
    )


def test_derive_customer_name_fallback() -> None:
    cid = uuid4()
    assert CeduleVentesSousTraitanceRepository._derive_customer_name(cid, None) == f"Customer {cid}"


def test_normalize_shape_maps_plate_to_sheet() -> None:
    assert _normalize_shape("plate") == "sheet"
    assert _normalize_shape("PLATE") == "sheet"


def test_normalize_shape_unknown_fallback() -> None:
    assert _normalize_shape("something-unsupported") == "unknown"


def test_normalize_machine_group_id() -> None:
    assert CeduleVentesSousTraitanceRepository._normalize_machine_group_id(" plasma_table_large ") == "PLASMA_TABLE_LARGE"

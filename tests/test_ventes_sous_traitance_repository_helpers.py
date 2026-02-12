from __future__ import annotations

from uuid import uuid4

from app.integrations.cedule_ventes_sous_traitance_repository import CeduleVentesSousTraitanceRepository


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

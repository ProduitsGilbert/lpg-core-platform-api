"""Ventes - Sous-Traitance API routers."""

from fastapi import APIRouter

from .router import router as ventes_sous_traitance_router

router = APIRouter()
router.include_router(ventes_sous_traitance_router)


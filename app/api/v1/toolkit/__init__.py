"""Toolkit API routers."""

from fastapi import APIRouter

from .ai import router as ai_router
from .mrp import router as mrp_router

# Expose AI and MRP routes without the legacy `/toolkit` prefix
router = APIRouter()
router.include_router(mrp_router)
router.include_router(ai_router)

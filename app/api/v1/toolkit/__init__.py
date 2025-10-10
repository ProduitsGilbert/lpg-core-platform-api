"""Toolkit API routers."""

from fastapi import APIRouter

from .ai import router as ai_router
from .mrp import router as mrp_router

router = APIRouter(prefix="/toolkit")
router.include_router(mrp_router)
router.include_router(ai_router)

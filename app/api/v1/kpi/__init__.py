"""KPI API routes."""

from fastapi import APIRouter

from .router import router as kpi_router

router = APIRouter()
router.include_router(kpi_router)



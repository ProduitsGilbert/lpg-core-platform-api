"""Service domain API router."""

from fastapi import APIRouter

from .router import router as service_router

router = APIRouter()
router.include_router(service_router)


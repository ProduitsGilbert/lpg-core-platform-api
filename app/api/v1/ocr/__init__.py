"""
OCR API endpoints
"""
from fastapi import APIRouter
from .documents import router as documents_router
from .assemblies import router as assemblies_router

# Create OCR router (no tags to avoid duplicates)
router = APIRouter()

# Include OCR sub-routers
router.include_router(documents_router)
router.include_router(assemblies_router)
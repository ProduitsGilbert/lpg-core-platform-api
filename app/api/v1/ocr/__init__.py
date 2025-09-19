"""
OCR API endpoints
"""
from fastapi import APIRouter
from .documents import router as documents_router

# Create OCR router (no tags to avoid duplicates)
router = APIRouter()

# Include OCR sub-routers
router.include_router(documents_router)
"""
API v1 router aggregation
"""
from fastapi import APIRouter

# Import domain routers
from .erp import router as erp_router
from .communications import router as communications_router
from .edi import router as edi_router
from .documents import router as documents_router
from .ocr import router as ocr_router

# Create main v1 router
router = APIRouter(prefix="/api/v1")

# Include all domain routers
router.include_router(erp_router)
router.include_router(communications_router)
router.include_router(edi_router)
router.include_router(documents_router)
router.include_router(ocr_router)

"""
Documents domain API routers
"""
from fastapi import APIRouter
from .file_share import router as file_share_router
from .technical_sheets import router as technical_sheets_router

router = APIRouter(prefix="/documents")

# Include sub-routers
router.include_router(file_share_router)
router.include_router(technical_sheets_router)
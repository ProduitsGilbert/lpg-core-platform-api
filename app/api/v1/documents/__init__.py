"""
Documents domain API routers
"""
from fastapi import APIRouter
from .file_share import router as file_share_router

router = APIRouter(prefix="/documents")

# Include sub-routers
router.include_router(file_share_router)
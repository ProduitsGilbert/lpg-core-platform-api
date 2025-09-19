"""
Communications domain API routers
"""
from fastapi import APIRouter
from .conversations import router as conversations_router

router = APIRouter(prefix="/communications")

# Include sub-routers
router.include_router(conversations_router)
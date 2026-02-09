"""
Communications domain API routers
"""
from fastapi import APIRouter
from .conversations import router as conversations_router
from .quote_requests import router as quote_requests_router

router = APIRouter(prefix="/communications")

# Include sub-routers
router.include_router(conversations_router)
router.include_router(quote_requests_router)
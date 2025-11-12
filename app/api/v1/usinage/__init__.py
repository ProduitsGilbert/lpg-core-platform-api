"""
Usinage domain API routers.

This package groups machining-related endpoints (Fastems, CNC, etc.) under
`/api/v1/usinage`.
"""

from fastapi import APIRouter

from .fastems1 import router as fastems1_router

router = APIRouter(prefix="/usinage")

router.include_router(fastems1_router)

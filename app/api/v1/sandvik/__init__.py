"""
Sandvik API endpoints.

This package provides REST endpoints for accessing Sandvik Machining Insights
data including machine history and live metrics.
"""

from fastapi import APIRouter

from .router import router as sandvik_router

router = APIRouter(prefix="/sandvik")

router.include_router(sandvik_router)

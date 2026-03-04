"""Tooling API v1 routes."""

from fastapi import APIRouter

from .router import router as tooling_router

router = APIRouter()

router.include_router(tooling_router)

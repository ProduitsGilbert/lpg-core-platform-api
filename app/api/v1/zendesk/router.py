"""Zendesk API router aggregation."""

from fastapi import APIRouter

# Import domain routers
from .tickets import router as tickets_router

# Create main Zendesk router
router = APIRouter(prefix="/zendesk")

# Include all domain routers
router.include_router(tickets_router)


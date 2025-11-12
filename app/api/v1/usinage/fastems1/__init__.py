"""
Fastems1 domain router bundle.

Currently hosts the Autopilot endpoints and can be extended later for other
Fastems1 services (telemetry, reporting, etc.).
"""

from fastapi import APIRouter

from .autopilot.router import router as autopilot_router

router = APIRouter(prefix="/fastems1")

router.include_router(autopilot_router)

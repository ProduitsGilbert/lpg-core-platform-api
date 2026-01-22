"""ClickUp API router aggregation."""

from fastapi import APIRouter

# Import domain routers
from .tasks import router as tasks_router

# Create main ClickUp router
router = APIRouter(prefix="/clickup")

# Include all domain routers
router.include_router(tasks_router)




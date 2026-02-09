"""
ERP domain API routers
"""
from fastapi import APIRouter
from .business_central import router as bc_router
from .items import router as items_router
from .purchase_orders import router as po_router
from .webhooks import router as webhooks_router
from .production import router as production_router
from .jobs import router as jobs_router

router = APIRouter(prefix="/erp")

# Include sub-routers
router.include_router(bc_router)
router.include_router(items_router)
router.include_router(po_router)
router.include_router(webhooks_router)
router.include_router(production_router)
router.include_router(jobs_router)

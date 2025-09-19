"""
ERP domain API routers
"""
from fastapi import APIRouter
from .items import router as items_router
from .purchase_orders import router as po_router

router = APIRouter(prefix="/erp")

# Include sub-routers
router.include_router(items_router)
router.include_router(po_router)
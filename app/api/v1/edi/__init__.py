"""EDI API router."""

from fastapi import APIRouter

from .eleknet import router as eleknet_router
from .purchase_orders import router as purchase_orders_router

router = APIRouter()
router.include_router(purchase_orders_router)
router.include_router(eleknet_router)

__all__ = ["router"]

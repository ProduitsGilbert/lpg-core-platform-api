"""EDI API router."""

from fastapi import APIRouter

from .purchase_orders import router as purchase_orders_router

router = APIRouter()
router.include_router(purchase_orders_router)

__all__ = ["router"]

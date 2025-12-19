"""
API v1 router aggregation
"""
from fastapi import APIRouter

# Import domain routers
from .erp import router as erp_router
from .communications import router as communications_router
from .edi import router as edi_router
from .documents import router as documents_router
from .ocr import router as ocr_router
from .toolkit import router as toolkit_router
from .usinage import router as usinage_router
from .sandvik import router as sandvik_router
from .clickup.router import router as clickup_router
from .zendesk.router import router as zendesk_router
from .finance.router import router as finance_router

# Create main v1 router
router = APIRouter(prefix="/api/v1")

# Include all domain routers
router.include_router(erp_router)
router.include_router(communications_router)
router.include_router(edi_router)
router.include_router(documents_router)
router.include_router(ocr_router)
router.include_router(toolkit_router)
router.include_router(usinage_router)
router.include_router(sandvik_router)
router.include_router(clickup_router)
router.include_router(zendesk_router)
router.include_router(finance_router)

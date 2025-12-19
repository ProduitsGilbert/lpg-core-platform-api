from fastapi import APIRouter, Depends, Query, Path, HTTPException, Header, status
from datetime import date
from typing import Optional, List
import os

from app.adapters.erp_client import ERPClient
from app.integrations.finance_repository import FinanceRepository
from app.integrations.bc_continia_repository import BusinessCentralContiniaRepository
from app.domain.finance.service import CashflowService
from app.domain.finance.models import CashflowProjection, ManualEntry, ManualEntryCreate, ManualEntryUpdate, CurrencyCode
from app.settings import settings

router = APIRouter(
    prefix="/finance",
    tags=["Finance"]
)

async def verify_finance_token(x_finance_token: str = Header(..., alias="X-Finance-Token")):
    """
    Verify the finance authentication token.
    Requires header X-Finance-Token to match environment variable FINANCE_API_TOKEN.
    """
    expected = os.getenv("FINANCE_API_TOKEN", "finance-secret")
    if x_finance_token != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid finance token"
        )
    return x_finance_token

# Initialize service
try:
    _erp_client = ERPClient()
    _repo = FinanceRepository()
    _continia_repo = BusinessCentralContiniaRepository()
    _service = CashflowService(_erp_client, _repo, _continia_repo)
except Exception as e:
    # Log error but don't crash app startup
    import logging
    logging.getLogger(__name__).error(f"Failed to initialize Finance service: {e}")
    _service = None

def get_service() -> CashflowService:
    if not _service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Finance service is not available (configuration error)"
        )
    return _service

@router.get("/cashflow", response_model=CashflowProjection)
async def get_cashflow_projection(
    start_date: date = Query(..., description="Start date for projection"),
    end_date: date = Query(..., description="End date for projection"),
    currency: Optional[CurrencyCode] = Query(None, description="Filter by currency"),
    token: str = Depends(verify_finance_token),
    svc: CashflowService = Depends(get_service)
):
    """
    Get cashflow projection for the specified period.
    Aggregates data from ERP (Sales, Purchasing, Jobs) and manual entries.
    """
    return await svc.get_projection(start_date, end_date, currency)

@router.get("/cashflow/entries", response_model=List[ManualEntry])
async def list_manual_entries(
    token: str = Depends(verify_finance_token),
    svc: CashflowService = Depends(get_service),
):
    """List all manual cashflow entries from [Cedule].[dbo].[Finance_Cashflow]."""
    # Directly using repository through service for consistent access path
    return svc.repo.get_all_entries()

@router.post("/cashflow/entries", response_model=ManualEntry, status_code=status.HTTP_201_CREATED)
async def create_manual_entry(
    entry: ManualEntryCreate,
    token: str = Depends(verify_finance_token),
    svc: CashflowService = Depends(get_service)
):
    """Create a manual cashflow entry (one-time or periodic)."""
    return svc.create_entry(entry)

@router.put("/cashflow/entries/{entry_id}", response_model=ManualEntry)
async def update_manual_entry(
    updates: ManualEntryUpdate,
    entry_id: int = Path(..., description="Entry ID"),
    token: str = Depends(verify_finance_token),
    svc: CashflowService = Depends(get_service)
):
    """Update a manual cashflow entry."""
    updated = svc.update_entry(entry_id, updates)
    if not updated:
        raise HTTPException(status_code=404, detail="Entry not found")
    return updated

@router.delete("/cashflow/entries/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_manual_entry(
    entry_id: int = Path(..., description="Entry ID"),
    token: str = Depends(verify_finance_token),
    svc: CashflowService = Depends(get_service)
):
    """Delete a manual cashflow entry."""
    success = svc.delete_entry(entry_id)
    if not success:
        raise HTTPException(status_code=404, detail="Entry not found")
    return None


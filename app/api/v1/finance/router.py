from fastapi import APIRouter, Depends, Query, Path, HTTPException, Header, status, BackgroundTasks
from datetime import date, datetime, timedelta
from typing import Optional, List, Dict, Any
import os
from urllib.parse import urlencode

from app.adapters.erp_client import ERPClient
from app.integrations.finance_repository import FinanceRepository
from app.integrations.bc_continia_repository import BusinessCentralContiniaRepository
from app.domain.finance.service import CashflowService
from app.domain.finance.accounts_receivable_service import AccountsReceivableService
from app.domain.finance.cashflow_projection_cache import cashflow_projection_cache
from app.domain.finance.models import (
    CashflowProjection,
    ManualEntry,
    ManualEntryCreate,
    ManualEntryUpdate,
    CurrencyCode,
    AccountsReceivableInvoice,
    AccountsReceivableInvoiceLine,
    AccountsReceivableCollectionItem,
    AccountsReceivableCacheStatus,
)
from app.integrations.ar_payment_stats_repository import ArPaymentStatsRepository
from app.integrations.ar_open_invoices_cache_repository import ArOpenInvoicesCacheRepository
from app.api.v1.models import CollectionResponse, PaginationMeta, Links, SingleResponse
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
    _ar_stats_repo = ArPaymentStatsRepository()
    _ar_cache_repo = ArOpenInvoicesCacheRepository()
    _ar_service = AccountsReceivableService(_erp_client, _ar_stats_repo, _ar_cache_repo)
except Exception as e:
    # Log error but don't crash app startup
    import logging
    logging.getLogger(__name__).error(f"Failed to initialize Finance service: {e}")
    _service = None
    _ar_service = None

def get_service() -> CashflowService:
    if not _service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Finance service is not available (configuration error)"
        )
    return _service

def get_ar_service() -> AccountsReceivableService:
    if not _ar_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Accounts receivable service is not available (configuration error)"
        )
    return _ar_service

def _require_cache(svc: AccountsReceivableService) -> None:
    if not svc.cache_available:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AR cache storage is not configured"
        )

def _pagination_links(path: str, params: Dict[str, Any], page: int, per_page: int, total_pages: int) -> Links:
    base_params = {k: v for k, v in params.items() if v is not None}
    base_params["per_page"] = per_page
    self_link = f"{path}?{urlencode({**base_params, 'page': page})}"
    next_link = (
        f"{path}?{urlencode({**base_params, 'page': page + 1})}" if page < total_pages else None
    )
    prev_link = (
        f"{path}?{urlencode({**base_params, 'page': page - 1})}" if page > 1 else None
    )
    last_link = f"{path}?{urlencode({**base_params, 'page': total_pages})}"
    return Links(self=self_link, next=next_link, prev=prev_link, last=last_link)

@router.get("/cashflow", response_model=CashflowProjection)
async def get_cashflow_projection(
    start_date: date = Query(..., description="Start date for projection"),
    end_date: date = Query(..., description="End date for projection"),
    currency: Optional[CurrencyCode] = Query(None, description="Filter by currency"),
    refresh: bool = Query(
        False,
        description="Force recomputing cashflow projection instead of using daily cache.",
    ),
    token: str = Depends(verify_finance_token),
    svc: CashflowService = Depends(get_service)
):
    """
    Get cashflow projection for the specified period.
    Aggregates data from ERP (Sales, Purchasing, Jobs) and manual entries.
    """
    cache_date = date.today().isoformat()
    start_iso = start_date.isoformat()
    end_iso = end_date.isoformat()
    currency_code = currency.value if currency else ""

    if not refresh and cashflow_projection_cache.is_configured:
        cached = cashflow_projection_cache.get_snapshot(
            cache_date=cache_date,
            start_date=start_iso,
            end_date=end_iso,
            currency_code=currency_code,
        )
        if cached:
            return CashflowProjection.model_validate(cached)
        stale = cashflow_projection_cache.get_latest_snapshot(
            start_date=start_iso,
            end_date=end_iso,
            currency_code=currency_code,
        )
        if stale:
            return CashflowProjection.model_validate(stale)

    projection = await svc.get_projection(start_date, end_date, currency)

    if cashflow_projection_cache.is_configured:
        cutoff_date = (date.today() - timedelta(days=settings.cashflow_projection_cache_retention_days)).isoformat()
        cashflow_projection_cache.upsert_snapshot(
            cache_date=cache_date,
            start_date=start_iso,
            end_date=end_iso,
            currency_code=currency_code,
            payload=projection.model_dump(mode="json"),
        )
        cashflow_projection_cache.prune_before(cutoff_date)

    return projection

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
    created = svc.create_entry(entry)
    cashflow_projection_cache.invalidate_cache_date(date.today().isoformat())
    return created

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
    cashflow_projection_cache.invalidate_cache_date(date.today().isoformat())
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
    cashflow_projection_cache.invalidate_cache_date(date.today().isoformat())
    return None


@router.get(
    "/accounts-receivable/invoices",
    response_model=CollectionResponse[AccountsReceivableInvoice],
    summary="List open accounts receivable invoices",
)
async def list_open_ar_invoices(
    due_from: Optional[date] = Query(None, description="Filter by Due_Date >= due_from"),
    due_to: Optional[date] = Query(None, description="Filter by Due_Date <= due_to"),
    customer_no: Optional[str] = Query(None, description="Filter by customer number"),
    invoice_no: Optional[str] = Query(None, description="Filter by invoice number"),
    use_cache: bool = Query(True, description="Use cached open invoices when available"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(50, ge=1, le=200, description="Items per page"),
    token: str = Depends(verify_finance_token),
    svc: AccountsReceivableService = Depends(get_ar_service),
) -> CollectionResponse[AccountsReceivableInvoice]:
    cache_key = "open_invoices"
    if use_cache:
        _require_cache(svc)
        cached = svc.get_cached_open_invoices(cache_key)
        if cached is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="AR open invoice cache not initialized; call /accounts-receivable/cache/refresh",
            )
        invoices = cached
    else:
        invoices = await svc.list_open_invoices(
            due_from=due_from,
            due_to=due_to,
            customer_no=customer_no,
            invoice_no=invoice_no,
        )

    if due_from:
        invoices = [inv for inv in invoices if inv.due_date and inv.due_date >= due_from]
    if due_to:
        invoices = [inv for inv in invoices if inv.due_date and inv.due_date <= due_to]
    if customer_no:
        invoices = [inv for inv in invoices if inv.customer_no == customer_no]
    if invoice_no:
        invoices = [inv for inv in invoices if inv.invoice_no == invoice_no]
    invoices = [inv for inv in invoices if not (inv.customer_no or "").upper().startswith("ZZ")]

    total_items = len(invoices)
    total_pages = max(1, (total_items + per_page - 1) // per_page)
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paginated = invoices[start_idx:end_idx]

    meta = PaginationMeta(
        pagination={
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
            "total_items": total_items,
        }
    )
    links = _pagination_links(
        "/api/v1/finance/accounts-receivable/invoices",
        {
            "due_from": due_from.isoformat() if due_from else None,
            "due_to": due_to.isoformat() if due_to else None,
            "customer_no": customer_no,
            "invoice_no": invoice_no,
        },
        page,
        per_page,
        total_pages,
    )
    return CollectionResponse(data=paginated, meta=meta, links=links)


@router.get(
    "/accounts-receivable/invoices/{invoice_no}/lines",
    response_model=CollectionResponse[AccountsReceivableInvoiceLine],
    summary="List lines for a posted sales invoice",
)
async def list_ar_invoice_lines(
    invoice_no: str = Path(..., description="Posted sales invoice number"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(100, ge=1, le=500, description="Items per page"),
    token: str = Depends(verify_finance_token),
    svc: AccountsReceivableService = Depends(get_ar_service),
) -> CollectionResponse[AccountsReceivableInvoiceLine]:
    lines = await svc.get_invoice_lines(invoice_no)

    total_items = len(lines)
    total_pages = max(1, (total_items + per_page - 1) // per_page)
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paginated = lines[start_idx:end_idx]

    meta = PaginationMeta(
        pagination={
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
            "total_items": total_items,
        }
    )
    links = _pagination_links(
        f"/api/v1/finance/accounts-receivable/invoices/{invoice_no}/lines",
        {},
        page,
        per_page,
        total_pages,
    )
    return CollectionResponse(data=paginated, meta=meta, links=links)


@router.get(
    "/accounts-receivable/collections",
    response_model=CollectionResponse[AccountsReceivableCollectionItem],
    summary="List open invoices prioritized by payment habit",
)
async def list_ar_collections(
    due_from: Optional[date] = Query(None, description="Filter by Due_Date >= due_from"),
    due_to: Optional[date] = Query(None, description="Filter by Due_Date <= due_to"),
    customer_no: Optional[str] = Query(None, description="Filter by customer number"),
    invoice_no: Optional[str] = Query(None, description="Filter by invoice number"),
    use_cache: bool = Query(True, description="Use cached open invoices when available"),
    min_avg_days_late: Optional[float] = Query(
        None, ge=0, description="Minimum average days late"
    ),
    min_late_ratio: Optional[float] = Query(
        None, ge=0, le=1, description="Minimum late ratio"
    ),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(50, ge=1, le=200, description="Items per page"),
    token: str = Depends(verify_finance_token),
    svc: AccountsReceivableService = Depends(get_ar_service),
) -> CollectionResponse[AccountsReceivableCollectionItem]:
    cache_key = "open_invoices"
    if use_cache:
        _require_cache(svc)
        cached = svc.get_cached_open_invoices(cache_key)
        if cached is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="AR open invoice cache not initialized; call /accounts-receivable/cache/refresh",
            )
        invoices = cached
    else:
        invoices = await svc.list_open_invoices(
            due_from=due_from,
            due_to=due_to,
            customer_no=customer_no,
            invoice_no=invoice_no,
        )

    if due_from:
        invoices = [inv for inv in invoices if inv.due_date and inv.due_date >= due_from]
    if due_to:
        invoices = [inv for inv in invoices if inv.due_date and inv.due_date <= due_to]
    if customer_no:
        invoices = [inv for inv in invoices if inv.customer_no == customer_no]
    if invoice_no:
        invoices = [inv for inv in invoices if inv.invoice_no == invoice_no]
    invoices = [inv for inv in invoices if not (inv.customer_no or "").upper().startswith("ZZ")]

    items = svc.list_priority_collections_from_invoices(
        invoices,
        min_avg_days_late=min_avg_days_late,
        min_late_ratio=min_late_ratio,
    )

    total_items = len(items)
    total_pages = max(1, (total_items + per_page - 1) // per_page)
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paginated = items[start_idx:end_idx]

    meta = PaginationMeta(
        pagination={
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
            "total_items": total_items,
        }
    )
    links = _pagination_links(
        "/api/v1/finance/accounts-receivable/collections",
        {
            "due_from": due_from.isoformat() if due_from else None,
            "due_to": due_to.isoformat() if due_to else None,
            "customer_no": customer_no,
            "invoice_no": invoice_no,
            "min_avg_days_late": min_avg_days_late,
            "min_late_ratio": min_late_ratio,
        },
        page,
        per_page,
        total_pages,
    )
    return CollectionResponse(data=paginated, meta=meta, links=links)


@router.post(
    "/accounts-receivable/cache/refresh",
    response_model=SingleResponse[AccountsReceivableCacheStatus],
    summary="Refresh cached open AR invoices",
)
async def refresh_ar_open_invoice_cache(
    due_from: Optional[date] = Query(None, description="Filter by Due_Date >= due_from"),
    due_to: Optional[date] = Query(None, description="Filter by Due_Date <= due_to"),
    customer_no: Optional[str] = Query(None, description="Filter by customer number"),
    invoice_no: Optional[str] = Query(None, description="Optional invoice number filter"),
    replace: bool = Query(False, description="Replace cache instead of merge"),
    async_refresh: bool = Query(
        False,
        description="Run the refresh in the background and return immediately",
    ),
    background_tasks: BackgroundTasks = None,
    token: str = Depends(verify_finance_token),
    svc: AccountsReceivableService = Depends(get_ar_service),
) -> SingleResponse[AccountsReceivableCacheStatus]:
    _require_cache(svc)
    cache_key = "open_invoices"
    if async_refresh:
        if background_tasks is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Background task runner unavailable",
            )
        background_tasks.add_task(
            svc.refresh_open_invoices_cache,
            cache_key,
            due_from=due_from,
            due_to=due_to,
            customer_no=customer_no,
            invoice_no=invoice_no,
            replace=replace,
        )
        cached_status = svc.get_cache_status(cache_key)
        if cached_status is None:
            cached_status = AccountsReceivableCacheStatus(
                cache_key=cache_key,
                invoice_count=0,
                updated_at=datetime.utcnow(),
            )
        return SingleResponse(data=cached_status)

    status = await svc.refresh_open_invoices_cache(
        cache_key,
        due_from=due_from,
        due_to=due_to,
        customer_no=customer_no,
        invoice_no=invoice_no,
        replace=replace,
    )
    return SingleResponse(data=status)

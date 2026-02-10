from __future__ import annotations

import logging
from datetime import date, timedelta

from dateutil.relativedelta import relativedelta

from app.adapters.erp_client import ERPClient
from app.domain.finance.cashflow_projection_cache import cashflow_projection_cache
from app.domain.finance.service import CashflowService
from app.integrations.bc_continia_repository import BusinessCentralContiniaRepository
from app.integrations.finance_repository import FinanceRepository
from app.settings import settings

logger = logging.getLogger(__name__)


async def refresh_cashflow_projection_default_window() -> None:
    """Refresh cashflow cache for the default UI period: last month to next 3 months."""
    if not cashflow_projection_cache.is_configured:
        return

    today = date.today()
    start_date = today + relativedelta(months=-1)
    end_date = today + relativedelta(months=3)

    service = CashflowService(
        ERPClient(),
        FinanceRepository(),
        BusinessCentralContiniaRepository(),
    )
    try:
        projection = await service.get_projection(start_date, end_date, currency_filter=None)
        cache_date = today.isoformat()
        cashflow_projection_cache.upsert_snapshot(
            cache_date=cache_date,
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            currency_code="",
            payload=projection.model_dump(mode="json"),
        )
        cutoff_date = (today - timedelta(days=settings.cashflow_projection_cache_retention_days)).isoformat()
        cashflow_projection_cache.prune_before(cutoff_date)
    except Exception as exc:
        logger.warning(
            "Failed to refresh cashflow projection default cache",
            extra={
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "error": str(exc),
            },
        )

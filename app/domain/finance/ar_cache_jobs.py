from __future__ import annotations

import logging

from app.adapters.erp_client import ERPClient
from app.domain.finance.accounts_receivable_service import AccountsReceivableService
from app.integrations.ar_open_invoices_cache_repository import ArOpenInvoicesCacheRepository
from app.integrations.ar_payment_stats_repository import ArPaymentStatsRepository

logger = logging.getLogger(__name__)


async def refresh_ar_open_invoices_cache() -> None:
    """Refresh the open invoices cache once per schedule."""
    cache_repo = ArOpenInvoicesCacheRepository()
    if not cache_repo.is_configured:
        logger.warning("AR open invoice cache not configured; skipping refresh")
        return

    erp = ERPClient()
    stats_repo = ArPaymentStatsRepository()
    svc = AccountsReceivableService(erp, stats_repo, cache_repo)

    status = await svc.refresh_open_invoices_cache("open_invoices")
    logger.info(
        "AR open invoice cache refreshed",
        extra={"invoice_count": status.invoice_count, "updated_at": status.updated_at},
    )

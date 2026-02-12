from __future__ import annotations

import asyncio
import datetime as dt
from decimal import Decimal
from typing import Any, Dict, Iterable, Optional

from app.adapters.erp_client import ERPClient
from app.domain.kpi.models import (
    ContiniaStatusStats,
    PayablesInvoiceStatsResponse,
    PayablesStageStats,
)
from app.domain.kpi.payables_invoice_stats_cache import payables_invoice_stats_cache
from app.integrations.bc_continia_repository import BusinessCentralContiniaRepository
from app.settings import settings


def _first_non_empty(row: Dict[str, Any], fields: Iterable[str]) -> Optional[Any]:
    for field in fields:
        value = row.get(field)
        if value not in (None, ""):
            return value
    return None


def _coerce_decimal(value: Any) -> Decimal:
    if value is None:
        return Decimal("0")
    try:
        return Decimal(str(value))
    except Exception:
        return Decimal("0")


def _to_stage_stats(invoice_count: int, total_amount: Decimal) -> PayablesStageStats:
    return PayablesStageStats(
        invoice_count=invoice_count,
        total_amount=round(float(total_amount), 2),
    )


class PayablesInvoiceStatsService:
    def __init__(
        self,
        client: Optional[ERPClient] = None,
        continia_repository: Optional[BusinessCentralContiniaRepository] = None,
    ) -> None:
        self._client = client or ERPClient()
        self._continia_repo = continia_repository or BusinessCentralContiniaRepository()

    async def get_snapshot(
        self,
        *,
        snapshot_date: dt.date,
        refresh: bool = False,
    ) -> PayablesInvoiceStatsResponse:
        snapshot_iso = snapshot_date.isoformat()
        if not refresh and payables_invoice_stats_cache.is_configured:
            cached = payables_invoice_stats_cache.get_snapshot(snapshot_iso)
            if cached:
                return PayablesInvoiceStatsResponse.model_validate(cached)

        response = await self._compute_snapshot()
        if payables_invoice_stats_cache.is_configured:
            retention_cutoff = snapshot_date - dt.timedelta(days=settings.payables_stats_cache_retention_days)
            payables_invoice_stats_cache.upsert_snapshot(snapshot_iso, response.model_dump())
            payables_invoice_stats_cache.prune_before(retention_cutoff.isoformat())
        return response

    async def get_latest_snapshot(self, *, refresh: bool = False) -> PayablesInvoiceStatsResponse:
        if not refresh and payables_invoice_stats_cache.is_configured:
            cached = payables_invoice_stats_cache.get_latest_snapshot()
            if cached:
                return PayablesInvoiceStatsResponse.model_validate(cached)
        return await self.get_snapshot(snapshot_date=dt.date.today(), refresh=True)

    async def get_stats(self, *, refresh: bool = False) -> PayablesInvoiceStatsResponse:
        return await self.get_latest_snapshot(refresh=refresh)

    async def _compute_snapshot(self) -> PayablesInvoiceStatsResponse:
        continia_rows, purchase_invoice_rows, posted_rows = await self._load_sources()
        continia_open_rows = [row for row in continia_rows if self._is_continia_open(row)]

        continia_amount_by_no = await self._load_continia_amounts(continia_open_rows)

        continia_total = Decimal("0")
        continia_status_totals: Dict[str, Dict[str, Decimal | int]] = {}
        for row in continia_open_rows:
            doc_no = self._invoice_no(row)
            amount = self._invoice_amount(row)
            if doc_no and amount == Decimal("0") and doc_no in continia_amount_by_no:
                amount = continia_amount_by_no[doc_no]

            continia_total += amount
            status = self._continia_status_code(row)
            bucket = continia_status_totals.setdefault(
                status,
                {"invoice_count": 0, "total_amount": Decimal("0")},
            )
            bucket["invoice_count"] = int(bucket["invoice_count"]) + 1
            bucket["total_amount"] = Decimal(bucket["total_amount"]) + amount

        purchase_total = sum((self._invoice_amount(row) for row in purchase_invoice_rows), start=Decimal("0"))
        posted_total = sum((self._invoice_amount(row) for row in posted_rows), start=Decimal("0"))

        statuses = [
            ContiniaStatusStats(
                status=status,
                invoice_count=int(values["invoice_count"]),
                total_amount=round(float(Decimal(values["total_amount"])), 2),
            )
            for status, values in sorted(continia_status_totals.items(), key=lambda item: item[0])
        ]

        return PayablesInvoiceStatsResponse(
            continia=_to_stage_stats(len(continia_open_rows), continia_total),
            purchase_invoice=_to_stage_stats(len(purchase_invoice_rows), purchase_total),
            posted_purchase_order=_to_stage_stats(len(posted_rows), posted_total),
            continia_statuses=statuses,
        )

    async def _load_sources(self) -> tuple[list[Dict[str, Any]], list[Dict[str, Any]], list[Dict[str, Any]]]:
        open_purchase_fields = ["No", "Amount"]
        posted_purchase_fields = ["No", "Amount", "Remaining_Amount"]
        continia_rows, purchase_invoice_rows, posted_rows = await asyncio.gather(
            self._client.get_continia_invoices(),
            self._client.get_open_purchase_invoices(select_fields=open_purchase_fields),
            self._client.get_posted_purchase_invoices(
                include_paid=True,
                select_fields=posted_purchase_fields,
            ),
        )
        return continia_rows, purchase_invoice_rows, posted_rows

    async def _load_continia_amounts(self, continia_rows: list[Dict[str, Any]]) -> Dict[str, Decimal]:
        if not self._continia_repo.is_configured:
            return {}
        doc_nos = [doc_no for doc_no in (self._invoice_no(row) for row in continia_rows) if doc_no]
        if not doc_nos:
            return {}
        values_map = await asyncio.to_thread(
            self._continia_repo.get_document_values_batch,
            doc_nos,
        )
        return {
            doc_no: values.decimal_values.get("AMOUNTINCLVAT", Decimal("0"))
            for doc_no, values in values_map.items()
        }

    @staticmethod
    def _invoice_no(row: Dict[str, Any]) -> Optional[str]:
        no = _first_non_empty(row, ["No", "Document_No", "DocumentNo", "Invoice_No", "InvoiceNo"])
        if no in (None, ""):
            return None
        return str(no).strip() or None

    @staticmethod
    def _invoice_amount(row: Dict[str, Any]) -> Decimal:
        return _coerce_decimal(
            _first_non_empty(
                row,
                [
                    "Amount_Including_VAT",
                    "AmountIncludingVAT",
                    "Remaining_Amount",
                    "RemainingAmount",
                    "Amount",
                    "Total_Amount",
                    "TotalAmount",
                ],
            )
        )

    @staticmethod
    def _is_continia_open(row: Dict[str, Any]) -> bool:
        raw = _first_non_empty(row, ["Status", "status"])
        if raw is None:
            return False
        return str(raw).strip().lower() == "open"

    @staticmethod
    def _continia_status_code(row: Dict[str, Any]) -> str:
        raw = _first_non_empty(
            row,
            [
                "Status_Code",
                "StatusCode",
                "status_code",
                "statusCode",
            ],
        )
        if raw in (None, ""):
            return "UNKNOWN"
        return str(raw).strip() or "UNKNOWN"

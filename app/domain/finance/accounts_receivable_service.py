from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Dict, List, Optional
import logging
from statistics import mean, median

from app.domain.finance.models import (
    AccountsReceivableInvoice,
    AccountsReceivableInvoiceLine,
    AccountsReceivableCollectionItem,
    AccountsReceivablePaymentStats,
    AccountsReceivableCacheStatus,
)
from app.integrations.ar_open_invoices_cache_repository import ArOpenInvoicesCacheRepository
from app.integrations.ar_payment_stats_repository import ArPaymentStatsRepository

logger = logging.getLogger(__name__)
from app.ports import ERPClientProtocol


class AccountsReceivableService:
    def __init__(
        self,
        erp_client: ERPClientProtocol,
        stats_repo: ArPaymentStatsRepository,
        cache_repo: Optional[ArOpenInvoicesCacheRepository] = None,
    ) -> None:
        self._erp = erp_client
        self._stats_repo = stats_repo
        self._cache_repo = cache_repo

    @property
    def cache_available(self) -> bool:
        return bool(self._cache_repo and self._cache_repo.is_configured)

    async def list_open_invoices(
        self,
        *,
        due_from: Optional[date] = None,
        due_to: Optional[date] = None,
        customer_no: Optional[str] = None,
        invoice_no: Optional[str] = None,
        top: Optional[int] = None,
    ) -> List[AccountsReceivableInvoice]:
        records = await self._erp.get_open_posted_sales_invoices(
            due_from=due_from,
            due_to=due_to,
            customer_no=customer_no,
            invoice_no=invoice_no,
            top=top,
        )
        invoices = [self._map_invoice(record) for record in records]
        return [inv for inv in invoices if not self._is_ignored_customer(inv.customer_no)]

    def get_cached_open_invoices(self, cache_key: str) -> Optional[List[AccountsReceivableInvoice]]:
        if not self._cache_repo or not self._cache_repo.is_configured:
            return None
        cached = self._cache_repo.get_cache(cache_key)
        if not cached:
            return None
        _, payload = cached
        return [AccountsReceivableInvoice(**item) for item in payload]

    def get_cache_status(self, cache_key: str) -> Optional[AccountsReceivableCacheStatus]:
        if not self._cache_repo or not self._cache_repo.is_configured:
            return None
        cached = self._cache_repo.get_cache(cache_key)
        if not cached:
            return None
        updated_at, payload = cached
        return AccountsReceivableCacheStatus(
            cache_key=cache_key,
            invoice_count=len(payload),
            updated_at=updated_at,
        )

    async def refresh_open_invoices_cache(
        self,
        cache_key: str,
        *,
        due_from: Optional[date] = None,
        due_to: Optional[date] = None,
        customer_no: Optional[str] = None,
        invoice_no: Optional[str] = None,
        replace: bool = False,
    ) -> AccountsReceivableCacheStatus:
        if not self._cache_repo or not self._cache_repo.is_configured:
            raise ValueError("Cache repository not configured")
        invoices = await self.list_open_invoices(
            due_from=due_from,
            due_to=due_to,
            customer_no=customer_no,
            invoice_no=invoice_no,
        )
        payload = [inv.model_dump(mode="json") for inv in invoices]
        if not replace:
            cached = self._cache_repo.get_cache(cache_key)
            if cached:
                _, existing_payload = cached
                merged: Dict[str, dict] = {}
                for item in existing_payload:
                    cache_key_value = self._cache_invoice_key(item)
                    if cache_key_value:
                        merged[cache_key_value] = item
                for item in payload:
                    cache_key_value = self._cache_invoice_key(item)
                    if cache_key_value:
                        merged[cache_key_value] = item
                payload = list(merged.values())
        updated_at = self._cache_repo.upsert_cache(cache_key, payload)
        return AccountsReceivableCacheStatus(
            cache_key=cache_key,
            invoice_count=len(payload),
            updated_at=updated_at,
        )

    async def get_invoice_lines(self, invoice_no: str) -> List[AccountsReceivableInvoiceLine]:
        records = await self._erp.get_posted_sales_invoice_lines(invoice_no)
        return [self._map_invoice_line(invoice_no, record) for record in records]

    async def list_priority_collections(
        self,
        *,
        due_from: Optional[date] = None,
        due_to: Optional[date] = None,
        customer_no: Optional[str] = None,
        min_avg_days_late: Optional[float] = None,
        min_late_ratio: Optional[float] = None,
        top: Optional[int] = None,
    ) -> List[AccountsReceivableCollectionItem]:
        invoices = await self.list_open_invoices(
            due_from=due_from, due_to=due_to, customer_no=customer_no, top=top
        )
        customer_nos = {inv.customer_no for inv in invoices if inv.customer_no}
        try:
            stats_by_customer = self._stats_repo.get_stats_by_customer_nos(customer_nos)
        except Exception as exc:
            logger.warning("Failed to load AR payment stats; continuing without stats", exc_info=exc)
            stats_by_customer = {}
        stats_by_customer = self._merge_fallback_delay_stats(stats_by_customer, invoices)

        items: List[AccountsReceivableCollectionItem] = []
        for inv in invoices:
            stats = stats_by_customer.get(inv.customer_no) if inv.customer_no else None
            if stats:
                if min_avg_days_late is not None and (stats.avg_days_late or 0) < min_avg_days_late:
                    continue
                if min_late_ratio is not None and (stats.late_ratio or 0) < min_late_ratio:
                    continue
            items.append(AccountsReceivableCollectionItem(invoice=inv, payment_stats=stats))

        items.sort(key=self._priority_sort_key)
        return items

    def list_priority_collections_from_invoices(
        self,
        invoices: List[AccountsReceivableInvoice],
        *,
        min_avg_days_late: Optional[float] = None,
        min_late_ratio: Optional[float] = None,
    ) -> List[AccountsReceivableCollectionItem]:
        invoices = [inv for inv in invoices if not self._is_ignored_customer(inv.customer_no)]
        customer_nos = {inv.customer_no for inv in invoices if inv.customer_no}
        try:
            stats_by_customer = self._stats_repo.get_stats_by_customer_nos(customer_nos)
        except Exception as exc:
            logger.warning("Failed to load AR payment stats; continuing without stats", exc_info=exc)
            stats_by_customer = {}
        stats_by_customer = self._merge_fallback_delay_stats(stats_by_customer, invoices)

        items: List[AccountsReceivableCollectionItem] = []
        for inv in invoices:
            stats = stats_by_customer.get(inv.customer_no) if inv.customer_no else None
            if stats:
                if min_avg_days_late is not None and (stats.avg_days_late or 0) < min_avg_days_late:
                    continue
                if min_late_ratio is not None and (stats.late_ratio or 0) < min_late_ratio:
                    continue
            items.append(AccountsReceivableCollectionItem(invoice=inv, payment_stats=stats))

        items.sort(key=self._priority_sort_key)
        return items

    @staticmethod
    def _priority_sort_key(item: AccountsReceivableCollectionItem):
        stats = item.payment_stats
        avg_days = stats.avg_days_late if stats and stats.avg_days_late is not None else -1
        due = item.invoice.due_date or date.max
        return (-avg_days, due)

    @staticmethod
    def _is_ignored_customer(customer_no: Optional[str]) -> bool:
        if not customer_no:
            return False
        return str(customer_no).upper().startswith("ZZ")

    def _merge_fallback_delay_stats(
        self,
        stats_by_customer: Dict[str, AccountsReceivablePaymentStats],
        invoices: List[AccountsReceivableInvoice],
    ) -> Dict[str, AccountsReceivablePaymentStats]:
        """
        Fill missing payment stats with delay metrics derived from currently open invoices.

        This avoids empty `avg_days_late` / `late_ratio` in collections when historical
        stats table is not yet populated.
        """
        merged = dict(stats_by_customer)
        missing_customers = {
            str(inv.customer_no)
            for inv in invoices
            if inv.customer_no and str(inv.customer_no) not in merged
        }
        if not missing_customers:
            return merged
        fallback = self._build_delay_stats_from_open_invoices(
            invoices=invoices,
            customer_filter=missing_customers,
        )
        merged.update(fallback)
        return merged

    @staticmethod
    def _build_delay_stats_from_open_invoices(
        *,
        invoices: List[AccountsReceivableInvoice],
        customer_filter: Optional[set[str]] = None,
    ) -> Dict[str, AccountsReceivablePaymentStats]:
        today = date.today()
        days_by_customer: Dict[str, List[int]] = {}
        due_dates_by_customer: Dict[str, List[date]] = {}

        for inv in invoices:
            if not inv.customer_no or not inv.due_date:
                continue
            customer_no = str(inv.customer_no)
            if customer_filter and customer_no not in customer_filter:
                continue
            days_late = max((today - inv.due_date).days, 0)
            days_by_customer.setdefault(customer_no, []).append(days_late)
            due_dates_by_customer.setdefault(customer_no, []).append(inv.due_date)

        stats: Dict[str, AccountsReceivablePaymentStats] = {}
        for customer_no, days in days_by_customer.items():
            if not days:
                continue
            late_count = sum(1 for value in days if value > 0)
            due_dates = due_dates_by_customer.get(customer_no, [])
            stats[customer_no] = AccountsReceivablePaymentStats(
                customer_no=customer_no,
                invoice_count=len(days),
                avg_days_late=round(mean(days), 2),
                median_days_late=round(float(median(days)), 2),
                late_ratio=round(late_count / len(days), 4),
                window_start=min(due_dates) if due_dates else None,
                window_end=max(due_dates) if due_dates else None,
                updated_at=datetime.utcnow(),
            )
        return stats

    @staticmethod
    def _parse_date(value: object) -> Optional[date]:
        if isinstance(value, date) and not isinstance(value, datetime):
            return value
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, str):
            parsed = AccountsReceivableService._parse_datetime(value)
            return parsed.date() if parsed else None
        return None

    @staticmethod
    def _parse_datetime(value: str) -> Optional[datetime]:
        try:
            cleaned = value.replace("Z", "+00:00")
            return datetime.fromisoformat(cleaned)
        except ValueError:
            return None

    @staticmethod
    def _to_decimal(value: object) -> Optional[Decimal]:
        if value is None:
            return None
        try:
            return Decimal(str(value))
        except Exception:
            return None

    @staticmethod
    def _to_bool(value: object) -> Optional[bool]:
        if isinstance(value, bool):
            return value
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return bool(value)
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"true", "1", "yes", "y"}:
                return True
            if normalized in {"false", "0", "no", "n"}:
                return False
        return None

    @staticmethod
    def _to_int(value: object) -> Optional[int]:
        if value is None:
            return None
        if isinstance(value, bool):
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return None
            try:
                return int(stripped)
            except ValueError:
                return None
        return None

    @staticmethod
    def _cache_invoice_key(payload_item: Dict[str, object]) -> Optional[str]:
        entry_no = payload_item.get("entry_no")
        if entry_no not in (None, ""):
            return f"entry:{entry_no}"

        invoice_no = str(payload_item.get("invoice_no") or "").strip()
        if not invoice_no:
            return None

        customer_no = str(payload_item.get("customer_no") or "").strip()
        document_type = str(payload_item.get("document_type") or "").strip()
        due_date = str(payload_item.get("due_date") or "").strip()
        posting_date = str(payload_item.get("posting_date") or "").strip()
        return "|".join(
            [invoice_no, customer_no, document_type, due_date, posting_date]
        )

    def _map_invoice(self, record: Dict[str, object]) -> AccountsReceivableInvoice:
        document_no = (
            record.get("Document_No")
            or record.get("DocumentNo")
            or record.get("No")
        )
        raw_entry_no = record.get("Entry_No") or record.get("EntryNo")
        entry_no = self._to_int(raw_entry_no)
        invoice_no = document_no or entry_no or raw_entry_no or ""
        open_flag = self._to_bool(record.get("Open"))
        return AccountsReceivableInvoice(
            invoice_no=str(invoice_no),
            entry_no=entry_no,
            document_no=str(document_no) if document_no is not None else None,
            document_type=record.get("Document_Type") or record.get("DocumentType"),
            description=record.get("Description"),
            division=record.get("Division")
            or record.get("Division_Code")
            or record.get("Global_Dimension_1_Code"),
            region_code=record.get("Region_Code")
            or record.get("RegionCode")
            or record.get("Region Code"),
            customer_no=record.get("Sell_to_Customer_No")
            or record.get("Bill_to_Customer_No")
            or record.get("Customer_No")
            or record.get("CustomerNo"),
            customer_name=record.get("Sell_to_Customer_Name")
            or record.get("Bill_to_Name")
            or record.get("Customer_Name")
            or record.get("CustomerName"),
            bill_to_customer_no=record.get("Bill_to_Customer_No") or record.get("Bill_to_CustomerNo"),
            bill_to_name=record.get("Bill_to_Name") or record.get("Bill_to_Name_"),
            due_date=self._parse_date(record.get("Due_Date")),
            posting_date=self._parse_date(record.get("Posting_Date") or record.get("Document_Date")),
            posted_batch_name=record.get("Posted_Batch_Name")
            or record.get("Posted_Batch_Name_")
            or record.get("PostedBatchName"),
            total_amount=self._to_decimal(
                record.get("Amount_Including_VAT")
                or record.get("Amount")
                or record.get("Original_Amount")
                or record.get("Original_Amt_LCY")
            ),
            remaining_amount=self._to_decimal(
                record.get("Remaining_Amount") or record.get("RemainingAmount")
            ),
            remaining_amt=self._to_decimal(
                record.get("Remaining_AMT")
                or record.get("RemainingAmt")
                or record.get("Remaining_Amount_LCY")
            ),
            external_document_no=record.get("External_Document_No"),
            currency_code=record.get("Currency_Code") or record.get("CurrencyCode"),
            closed=(not open_flag) if open_flag is not None else self._to_bool(record.get("Closed")),
            cancelled=self._to_bool(record.get("Cancelled")),
            system_modified_at=self._parse_datetime(str(record.get("SystemModifiedAt")))
            if record.get("SystemModifiedAt")
            else None,
        )

    def _map_invoice_line(
        self, invoice_no: str, record: Dict[str, object]
    ) -> AccountsReceivableInvoiceLine:
        return AccountsReceivableInvoiceLine(
            invoice_no=invoice_no,
            line_no=record.get("Line_No") or record.get("LineNo"),
            item_no=record.get("No") or record.get("Item_No"),
            description=record.get("Description"),
            quantity=self._to_decimal(record.get("Quantity")),
            unit_price=self._to_decimal(record.get("Unit_Price")),
            line_amount=self._to_decimal(record.get("Line_Amount") or record.get("Amount")),
            amount_including_vat=self._to_decimal(record.get("Amount_Including_VAT")),
            line_type=record.get("Type"),
        )

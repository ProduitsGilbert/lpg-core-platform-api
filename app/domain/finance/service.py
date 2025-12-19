import logging
import re
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Optional, Any
import asyncio
from dateutil.relativedelta import relativedelta
from app.errors import ERPError
from app.integrations.bc_continia_repository import BusinessCentralContiniaRepository

from app.adapters.erp_client import ERPClient
from app.integrations.finance_repository import FinanceRepository
from app.domain.finance.models import (
    CashflowEntry, CashflowProjection, DailyCashflow, 
    TransactionType, CurrencyCode, CashflowSource,
    ManualEntry, ManualEntryCreate, ManualEntryUpdate, RecurrenceFrequency
)

logger = logging.getLogger(__name__)

class PaymentTermCalculator:
    """Helper to calculate due dates based on BC payment terms formulas."""
    
    @staticmethod
    def calculate_due_date(base_date: date, formula: str) -> date:
        if not formula:
            return base_date
            
        # Basic parsing for BC formulas like "30D", "1M", "CM", "CM+30D"
        # This is a simplified implementation.
        try:
            target_date = base_date
            formula = formula.upper().strip()
            
            # Split by + if complex
            parts = formula.split('+')
            
            for part in parts:
                part = part.strip()
                if part == 'CM': # Current Month
                    # Go to end of month
                    next_month = target_date.replace(day=28) + timedelta(days=4)
                    target_date = next_month - timedelta(days=next_month.day)
                elif part == 'CW': # Current Week
                    # Go to end of week (Sunday)
                    target_date = target_date + timedelta(days=(6 - target_date.weekday()))
                else:
                    # Parse number and unit (D, M, Y, W)
                    match = re.match(r'(\d+)([DMWY])', part)
                    if match:
                        num = int(match.group(1))
                        unit = match.group(2)
                        if unit == 'D':
                            target_date += timedelta(days=num)
                        elif unit == 'M':
                            target_date += relativedelta(months=num)
                        elif unit == 'Y':
                            target_date += relativedelta(years=num)
                        elif unit == 'W':
                            target_date += timedelta(weeks=num)
                            
            return target_date
        except Exception:
            logger.warning(f"Could not parse payment term formula: {formula}, using base date")
            return base_date

    @staticmethod
    def conservative_max_days(formulas: List[Optional[str]]) -> int:
        """
        Return a conservative maximum number of days a payment term formula might add.
        Used to decide how far back we must fetch base documents so that due dates in the
        requested range are not missed (cross-year scenarios).
        """
        max_days = 0
        for raw in formulas:
            if not raw:
                continue
            f = str(raw).upper().strip()
            # CM/CW depend on calendar boundaries; treat as <= 31 / 7
            if "CM" in f:
                max_days = max(max_days, 31)
            if "CW" in f:
                max_days = max(max_days, 7)
            # Parse tokens like 30D, 2W, 1M, 1Y (and allow combos with '+')
            parts = [p.strip() for p in f.split("+") if p.strip()]
            for part in parts:
                m = re.match(r"(\d+)([DMWY])", part)
                if not m:
                    continue
                n = int(m.group(1))
                unit = m.group(2)
                if unit == "D":
                    max_days = max(max_days, n)
                elif unit == "W":
                    max_days = max(max_days, n * 7)
                elif unit == "M":
                    max_days = max(max_days, n * 31)
                elif unit == "Y":
                    max_days = max(max_days, n * 366)
        # At minimum, look back one month (handles common Net30 and CM terms)
        return max(max_days, 31)

class CashflowService:
    def __init__(
        self,
        erp_client: ERPClient,
        repository: FinanceRepository,
        continia_repository: Optional[BusinessCentralContiniaRepository] = None,
    ):
        self.erp = erp_client
        self.repo = repository
        self.continia_repo = continia_repository or BusinessCentralContiniaRepository()

    async def get_projection(
        self, 
        start_date: date, 
        end_date: date, 
        currency_filter: Optional[CurrencyCode] = None
    ) -> CashflowProjection:
        if start_date > end_date:
            raise ERPError("Invalid date range: start_date must be <= end_date")

        # FAIL-CLOSED: all ERP sources are mandatory. If anything fails, we error.
        # To make large ranges reliable, we fetch ERP data month-by-month with limited concurrency.
        customers, vendors, payment_terms, continia_invoices = await asyncio.gather(
            self.erp.get_customer_payment_terms(),
            self.erp.get_vendor_payment_terms(),
            self.erp.get_payment_terms_definitions(),
            self.erp.get_continia_invoices(),
        )
        manual_entries = await asyncio.to_thread(self.repo.get_all_entries)

        # Continia SQL is mandatory (fail-closed) for amounts.
        if not self.continia_repo.is_configured:
            raise ERPError(
                "Business Central SQL connection (Continia CDC) is not configured. "
                "Set BC_SQL_SERVER/BC_SQL_DATABASE/BC_SQL_USERNAME/BC_SQL_PASSWORD."
            )

        # Build term formulas map (needed both for due dates and for lookback window).
        customer_terms = {c['No']: c.get('Payment_Terms_Code') for c in customers}
        vendor_terms = {v['No']: v.get('Payment_Terms_Code') for v in vendors}
        term_formulas = {t['Code']: t.get('Due_Date_Calculation') for t in payment_terms}

        # Lookback is only needed for sources where due date must be computed from a base date
        # (e.g., job planning lines and open PO lines). For sources with an explicit Due Date
        # (PurchaseInvoices, Continia SQL DUEDATE, posted invoices), we filter directly by Due Date.
        lookback_days = PaymentTermCalculator.conservative_max_days(list(term_formulas.values()))
        fetch_start = start_date - timedelta(days=lookback_days)

        # Fetch Continia documents by DUEDATE directly (no lookback).
        continia_docs = await asyncio.to_thread(
            self.continia_repo.list_purchase_documents_by_due_date,
            due_from=start_date,
            due_to=end_date,
        )
        continia_doc_nos = [d.document_no for d in continia_docs]
        continia_values_by_doc = await asyncio.to_thread(
            self.continia_repo.get_document_values_batch,
            continia_doc_nos,
        )

        # We do two sets of month-ranges:
        # - "requested" range for sources already filtered by Due_Date
        # - "extended" range for sources that rely on base date + payment terms (computed due date)
        req_month_ranges = self._month_ranges(start_date, end_date)
        ext_month_ranges = self._month_ranges(fetch_start, end_date)
        semaphore = asyncio.Semaphore(4)  # concurrency cap

        async def fetch_month_posted(m_start: date, m_end: date):
            async with semaphore:
                return await asyncio.gather(
                    self.erp.get_posted_sales_invoices(m_start, m_end),
                    self.erp.get_posted_purchase_invoices(m_start, m_end),
                    self.erp.get_open_purchase_invoices(m_start, m_end),
                )

        async def fetch_month_base(m_start: date, m_end: date):
            async with semaphore:
                return await asyncio.gather(
                    self.erp.get_job_planning_lines(m_start, m_end),
                    self.erp.get_open_po_lines(m_start, m_end),
                )

        posted_results = await asyncio.gather(
            *(fetch_month_posted(m_start, m_end) for (m_start, m_end) in req_month_ranges)
        )
        base_results = await asyncio.gather(
            *(fetch_month_base(m_start, m_end) for (m_start, m_end) in ext_month_ranges)
        )

        sales_invoices: List[Dict[str, Any]] = []
        job_lines: List[Dict[str, Any]] = []
        open_purchase_invoices: List[Dict[str, Any]] = []
        posted_purchase_invoices: List[Dict[str, Any]] = []
        open_po_lines: List[Dict[str, Any]] = []

        for (m_sales, m_posted_pinv, m_open_pinv) in posted_results:
            sales_invoices.extend(m_sales)
            posted_purchase_invoices.extend(m_posted_pinv)
            open_purchase_invoices.extend(m_open_pinv)

        for (m_jobs, m_open_po) in base_results:
            job_lines.extend(m_jobs)
            open_po_lines.extend(m_open_po)

        # New: Vendor Currency Map for open POs that don't have currency on line
        vendor_currencies = {v['No']: v.get('Currency_Code') for v in vendors}

        all_entries: List[CashflowEntry] = []

        # 3. Process ERP Sales Invoices
        # Build ref->amount index for de-duplication with jobs (Your_Reference not exposed in OData here,
        # but External_Document_No often carries the same business reference).
        invoice_ref_amounts: Dict[str, set[Decimal]] = {}
        for inv in sales_invoices:
            # Skip cancelled invoices (credit applied / cancelled in BC)
            cancelled_val = inv.get("Cancelled")
            if cancelled_val in (True, "true", "True", "YES", "Yes", "yes", 1):
                continue

            # Use Due_Date if available, else calculate
            doc_date = self._parse_date(inv.get('Due_Date') or inv.get('Posting_Date'))
            if not doc_date:
                continue
                
            amount = Decimal(str(inv.get('Remaining_Amount', 0)))
            curr = self._map_currency(inv.get('Currency_Code'))

            ref = (
                (inv.get("Your_Reference") or inv.get("YourReference") or inv.get("External_Document_No"))
            )
            if isinstance(ref, str):
                ref = ref.strip()
            if ref:
                invoice_ref_amounts.setdefault(str(ref), set()).add(amount)
                # Also store amount incl. VAT when present (some job amounts may align differently)
                try:
                    amt_incl = Decimal(str(inv.get("Amount_Including_VAT") or 0))
                    if amt_incl:
                        invoice_ref_amounts[str(ref)].add(amt_incl)
                except Exception:
                    pass
            
            all_entries.append(CashflowEntry(
                date=doc_date,
                amount=amount,
                currency=curr,
                transaction_type=TransactionType.DEPOSIT,
                description=f"Posted Invoice {inv.get('No')}",
                source=CashflowSource.ERP_SALES,
                reference_id=inv.get('No')
            ))

        # 4. Process Job Planning Lines
        job_cache: Dict[str, Dict[str, Any]] = {}
        for job in job_lines:
            # Base date: Planned_Delivery_Date (per finance requirement) + Customer Term
            base_date = self._parse_date(job.get('Planned_Delivery_Date')) or self._parse_date(job.get('Planning_Date'))
            if not base_date:
                continue
                
            job_no = job.get('Job_No')
            cust_no = None
            if job_no:
                if job_no not in job_cache:
                    header = await self.erp.get_job(job_no)
                    job_cache[job_no] = header or {}
                header = job_cache.get(job_no) or {}
                cust_no = header.get('Bill_to_Customer_No') or header.get('Sell_to_Customer_No') or header.get('Customer_No')
            
            term_code = customer_terms.get(cust_no)
            formula = term_formulas.get(term_code)
            due_date = PaymentTermCalculator.calculate_due_date(base_date, formula)
            
            # Amount? "Line_Amount" or "Total_Price"
            amount = Decimal(str(job.get('Remaining_Line_Amount') or job.get('Line_Amount') or job.get('Total_Price') or 0))
            # Job planning lines often don't carry currency code; treat blank as CAD.
            curr = self._map_currency(job.get('Currency_Code'))

            # De-duplicate: if a posted sales invoice references this job and has the same amount, skip.
            # (BC UI field 'Your Reference' is not exposed here; we use External_Document_No fallback)
            if job_no and str(job_no) in invoice_ref_amounts:
                candidates = invoice_ref_amounts.get(str(job_no), set())
                # compare to 2 decimals
                try:
                    amt2 = amount.quantize(Decimal("0.01"))
                except Exception:
                    amt2 = amount
                if any((c.quantize(Decimal("0.01")) if hasattr(c, "quantize") else c) == amt2 for c in candidates):
                    continue

            all_entries.append(CashflowEntry(
                date=due_date,
                amount=amount,
                currency=curr,
                transaction_type=TransactionType.DEPOSIT,
                description=f"Job Project {job_no}",
                source=CashflowSource.ERP_JOB,
                reference_id=job.get('Document_No') or job_no
            ))

        # 5. Process Posted Purchase Invoices
        for pinv in posted_purchase_invoices:
            doc_date = self._parse_date(pinv.get('Due_Date') or pinv.get('Posting_Date'))
            if not doc_date:
                continue
            
            # Prefer Remaining_Amount when available; fallback to Amount_Including_VAT.
            amount = Decimal(str(pinv.get('Remaining_Amount') or pinv.get('Amount_Including_VAT') or 0))
            curr = self._map_currency(pinv.get('Currency_Code'))

            all_entries.append(CashflowEntry(
                date=doc_date,
                amount=amount,
                currency=curr,
                transaction_type=TransactionType.PAYMENT,
                description=f"Posted Purchase Inv {pinv.get('No')}",
                source=CashflowSource.ERP_PURCHASE,
                reference_id=pinv.get('No')
            ))

        # 6. Process Open Purchase Invoices (kept separate from Continia)
        for opinv in open_purchase_invoices:
            # "invoice being processed by payable department"
            # Prefer ERP-provided Due_Date when available; otherwise calculate from invoice date + payment terms.
            due_from_erp = self._parse_date(opinv.get('Due_Date'))
            doc_date = self._parse_date(opinv.get('Document_Date') or opinv.get('Posting_Date'))
            if not due_from_erp and not doc_date:
                continue
                
            vend_no = opinv.get('Buy_from_Vendor_No')
            term_code = vendor_terms.get(vend_no)
            formula = term_formulas.get(term_code)
            due_date = due_from_erp or PaymentTermCalculator.calculate_due_date(doc_date, formula)
            
            amount = Decimal(str(opinv.get('Amount_Including_VAT') or opinv.get('Amount') or 0))
            curr = self._map_currency(opinv.get('Currency_Code'))

            all_entries.append(CashflowEntry(
                date=due_date,
                amount=amount,
                currency=curr,
                transaction_type=TransactionType.PAYMENT,
                description=f"Open Purchase Inv {opinv.get('No')}",
                source=CashflowSource.ERP_PURCHASE,
                reference_id=opinv.get('No')
            ))

        # 7. Continia endpoint is still mandatory (availability/consistency check),
        # but its payload does not expose amounts in this environment. Amounts are
        # taken from Business Central SQL CDC tables (see BusinessCentralContiniaRepository).
        for doc in continia_docs:
            values = continia_values_by_doc.get(doc.document_no)
            if not values:
                # Fail closed: document exists but we couldn't retrieve its values.
                raise ERPError(
                    f"Missing Continia CDC values for document {doc.document_no}",
                    context={"document_no": doc.document_no},
                )

            # Parse values (codes are uppercased in repository). Prefer DUEDATE from SQL when present.
            doc_date = values.date_values.get("DOCDATE") or values.date_values.get("POSTINGDATE")
            due_date = values.date_values.get("DUEDATE")
            amount_incl = values.decimal_values.get("AMOUNTINCLVAT")

            if doc_date is None:
                # Fallback: use SQL system created date if present
                if doc.system_created_at:
                    doc_date = doc.system_created_at.date()
                else:
                    raise ERPError(
                        f"Continia document {doc.document_no} missing DOCDATE/POSTINGDATE",
                        context={"document_no": doc.document_no},
                    )

            if due_date is None:
                # Fallback to payment term calculation using vendor card payment terms.
                vend_no = doc.vendor_code
                term_code = vendor_terms.get(vend_no)
                formula = term_formulas.get(term_code)
                due_date = PaymentTermCalculator.calculate_due_date(doc_date, formula)

            if amount_incl is None:
                raise ERPError(
                    f"Continia document {doc.document_no} missing AMOUNTINCLVAT",
                    context={"document_no": doc.document_no},
                )

            # Prefer currency from CDC values when present, else vendor currency, else CAD.
            cdc_currency = values.text_values.get("CURRCODE") if values else None
            curr = self._map_currency(cdc_currency or vendor_currencies.get(doc.vendor_code or ""))
            all_entries.append(
                CashflowEntry(
                    date=due_date,
                    amount=amount_incl,
                    currency=curr,
                    transaction_type=TransactionType.PAYMENT,
                    description=f"Continia Inv {doc.document_no}",
                    source=CashflowSource.ERP_PURCHASE,
                    reference_id=doc.document_no,
                )
            )

        # 8. Process Open Purchase Order Lines (To be received)
        for line in open_po_lines:
            # Use Expected Receipt Date as base
            base_date = self._parse_date(line.get('Expected_Receipt_Date') or line.get('Promised_Receipt_Date'))
            if not base_date:
                # Fallback to today if date missing, though unlikely for valid PO lines
                base_date = date.today()

            vend_no = line.get('Buy_from_Vendor_No')
            term_code = vendor_terms.get(vend_no)
            formula = term_formulas.get(term_code)
            
            # Calculate due date: Expected Receipt + Payment Terms
            due_date = PaymentTermCalculator.calculate_due_date(base_date, formula)
            
            # Uninvoiced quantity: Quantity - Quantity_Invoiced (per finance requirement)
            qty = Decimal(str(line.get('Quantity') or 0))
            qty_invoiced = Decimal(str(line.get('Quantity_Invoiced') or 0))
            outstanding_qty = qty - qty_invoiced
            
            if outstanding_qty <= 0:
                continue
                
            cost = Decimal(str(line.get('Direct_Unit_Cost') or 0))
            amount = outstanding_qty * cost
            
            # Currency: Use line currency if available, else vendor currency
            # Note: Line usually has Currency_Code but sometimes blank if LCY. 
            # If blank, we check vendor card.
            curr_code = line.get('Currency_Code')
            if not curr_code:
                curr_code = vendor_currencies.get(vend_no)
            
            curr = self._map_currency(curr_code)
            
            all_entries.append(CashflowEntry(
                date=due_date,
                amount=amount,
                currency=curr,
                transaction_type=TransactionType.PAYMENT,
                description=f"PO {line.get('Document_No')} Line {line.get('Line_No')}",
                source=CashflowSource.ERP_PURCHASE,
                reference_id=f"{line.get('Document_No')}-{line.get('Line_No')}"
            ))

        # 9. Process Manual Entries
        for entry in manual_entries:
            if entry.is_periodic:
                # Expand periodic
                expanded = self._expand_periodic_entry(entry, start_date, end_date)
                all_entries.extend(expanded)
            else:
                if entry.transaction_date and start_date <= entry.transaction_date <= end_date:
                    all_entries.append(self._map_manual_to_cashflow(entry, entry.transaction_date))

        # 10. Filter and Aggregate
        filtered_entries = [
            e for e in all_entries 
            if start_date <= e.date <= end_date 
            and (not currency_filter or e.currency == currency_filter)
        ]
        
        # Group by date
        daily_map: Dict[date, Dict[CurrencyCode, DailyCashflow]] = {}
        
        # Initialize range
        delta = end_date - start_date
        for i in range(delta.days + 1):
            d = start_date + timedelta(days=i)
            daily_map[d] = {}
            for c in CurrencyCode:
                daily_map[d][c] = DailyCashflow(date=d, currency=c)

        for e in filtered_entries:
            d_flow = daily_map.get(e.date)
            if not d_flow:
                # Should be covered by init unless date parsing went out of bounds
                continue
                
            flow_entry = d_flow.get(e.currency)
            if not flow_entry:
                flow_entry = DailyCashflow(date=e.date, currency=e.currency)
                d_flow[e.currency] = flow_entry
                
            if e.transaction_type == TransactionType.DEPOSIT:
                flow_entry.total_deposit += e.amount
                flow_entry.net_flow += e.amount
            else:
                flow_entry.total_payment += e.amount
                flow_entry.net_flow -= e.amount
            
            flow_entry.entries.append(e)

        # Flatten
        final_flows = []
        for d in sorted(daily_map.keys()):
            for c in CurrencyCode:
                if currency_filter and c != currency_filter:
                    continue
                final_flows.append(daily_map[d][c])

        return CashflowProjection(
            start_date=start_date,
            end_date=end_date,
            daily_flows=final_flows
        )

    # CRUD for Manual Entries
    def create_entry(self, entry: ManualEntryCreate) -> ManualEntry:
        return self.repo.create_entry(entry)

    def update_entry(self, entry_id: int, updates: ManualEntryUpdate) -> Optional[ManualEntry]:
        return self.repo.update_entry(entry_id, updates)

    def delete_entry(self, entry_id: int) -> bool:
        return self.repo.delete_entry(entry_id)

    # Helpers
    def _map_currency(self, code: Optional[str]) -> CurrencyCode:
        if not code or code.strip() == "":
            return CurrencyCode.CAD
        code = code.upper().strip()
        try:
            return CurrencyCode(code)
        except ValueError:
            logger.warning(f"Unknown currency code {code}, defaulting to CAD")
            return CurrencyCode.CAD

    def _parse_date(self, date_val: Any) -> Optional[date]:
        if not date_val:
            return None
        if isinstance(date_val, date):
            return date_val
        try:
            return datetime.fromisoformat(str(date_val).split('T')[0]).date()
        except Exception:
            return None

    def _map_manual_to_cashflow(self, entry: ManualEntry, date_val: date) -> CashflowEntry:
        return CashflowEntry(
            date=date_val,
            amount=entry.amount,
            currency=entry.currency_code,
            transaction_type=entry.transaction_type,
            description=entry.description,
            source=CashflowSource.MANUAL_PERIODIC if entry.is_periodic else CashflowSource.MANUAL,
            reference_id=str(entry.id)
        )

    def _expand_periodic_entry(self, entry: ManualEntry, start: date, end: date) -> List[CashflowEntry]:
        results = []
        if not entry.recurrence_frequency:
            return results
            
        current = entry.transaction_date # Start from the initial defined date
        if not current:
            # If no start date, can't expand.
            return results

        # Advance to start_date if needed (optimization)
        # But for simple logic, just generate and filter
        
        count = 0
        limit_count = entry.recurrence_count
        limit_date = entry.recurrence_end_date
        
        interval = entry.recurrence_interval or 1
        
        while True:
            # Check limits
            if limit_count is not None and count >= limit_count:
                break
            if limit_date and current > limit_date:
                break
            # Safety break for infinite loops if user sets bad data
            if current > end + timedelta(days=365): 
                break

            # Add if in range
            if start <= current <= end:
                results.append(self._map_manual_to_cashflow(entry, current))
            
            # If past end range, we can stop? 
            # Only if we are sure it won't come back (it won't, time moves forward)
            if current > end:
                break

            # Advance
            if entry.recurrence_frequency == RecurrenceFrequency.WEEKLY:
                current += timedelta(weeks=interval)
            elif entry.recurrence_frequency == RecurrenceFrequency.MONTHLY:
                current += relativedelta(months=interval)
            elif entry.recurrence_frequency == RecurrenceFrequency.YEARLY:
                current += relativedelta(years=interval)
            
            count += 1
            
        return results

    @staticmethod
    def _month_ranges(start: date, end: date) -> List[tuple[date, date]]:
        """Split [start, end] into month-sized inclusive ranges."""
        ranges: List[tuple[date, date]] = []
        current = start.replace(day=1)

        # align current to the month of start
        current = start.replace(day=1)
        while current <= end:
            next_month = (current + relativedelta(months=1)).replace(day=1)
            month_end = next_month - timedelta(days=1)
            m_start = max(start, current)
            m_end = min(end, month_end)
            ranges.append((m_start, m_end))
            current = next_month
        return ranges


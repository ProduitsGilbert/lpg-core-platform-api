# Finance AR UI PRD (Quick)

## Goal
Provide an accountant-friendly page to manage open Accounts Receivable (AR) invoices, prioritize collections using payment habit stats, and drill into invoice lines using the new Finance AR endpoints.

## API Host
Base URL: `http://192.168.0.192:7005`

All requests require the `X-Finance-Token` header (value provided by Finance).

## Endpoints and Returned Data

### 1) List Open AR Invoices
`GET /api/v1/finance/accounts-receivable/invoices`

Query params:
- `due_from` (date, optional)
- `due_to` (date, optional)
- `customer_no` (string, optional)
- `page` (int, default 1)
- `per_page` (int, default 50)

Returns (collection):
- `data[]` items (per invoice):
  - `invoice_no`
  - `customer_no`
  - `customer_name`
  - `bill_to_customer_no`
  - `bill_to_name`
  - `due_date`
  - `posting_date`
  - `total_amount`
  - `remaining_amount`
  - `external_document_no`
  - `currency_code`
  - `closed`
  - `cancelled`
  - `system_modified_at`
- `meta.pagination` (page, per_page, total_pages, total_items)
- `links` (self/next/prev/last)

Filtering rules (server-side):
- Only invoices with `closed = false` and `cancelled = false`.

### 2) Invoice Lines (Invoice Detail)
`GET /api/v1/finance/accounts-receivable/invoices/{invoice_no}/lines`

Query params:
- `page` (int, default 1)
- `per_page` (int, default 100)

Returns (collection):
- `data[]` items (per line):
  - `invoice_no`
  - `line_no`
  - `item_no`
  - `description`
  - `quantity`
  - `unit_price`
  - `line_amount`
  - `amount_including_vat`
  - `line_type`
- `meta.pagination`
- `links`

### 3) Collections Priority List
`GET /api/v1/finance/accounts-receivable/collections`

Query params:
- `due_from` (date, optional)
- `due_to` (date, optional)
- `customer_no` (string, optional)
- `min_avg_days_late` (float, optional)
- `min_late_ratio` (float, optional)
- `page` (int, default 1)
- `per_page` (int, default 50)

Returns (collection):
- `data[]` items:
  - `invoice` (same fields as Open AR Invoices)
  - `payment_stats` (nullable):
    - `customer_no`
    - `invoice_count`
    - `avg_days_late`
    - `median_days_late`
    - `late_ratio`
    - `window_start`
    - `window_end`
    - `updated_at`
- `meta.pagination`
- `links`

Notes:
- `payment_stats` is sourced from a weekly-refreshed cache and may be null if history is unavailable.

## Page Layout and UX

### A) AR Dashboard (Default View)
Sections:
1) **Priority Collections** (top panel)
   - Data source: `collections` endpoint.
   - Default sort: `avg_days_late` (desc), then `due_date` (asc).
   - Key columns:
     - Customer
     - Invoice No
     - Due Date
     - Remaining Amount
     - Avg Days Late
     - Late Ratio
     - Posting Date
     - External Doc No
   - Actions (row-level):
     - Open invoice detail (lines)
     - Contact customer (call/email link)
     - Mark for follow-up
     - Add internal note (frontend-only unless you add persistence later)

2) **Open Invoices** (secondary list)
   - Data source: `accounts-receivable/invoices`.
   - Default sort: `due_date` (asc), then `remaining_amount` (desc).
   - Key columns:
     - Customer
     - Invoice No
     - Due Date
     - Remaining Amount
     - Posting Date
     - Currency
     - External Doc No
   - Actions:
     - Open invoice detail
     - Contact customer

### B) Invoice Detail Drawer / Page
Triggered from any invoice row.
Sections:
1) **Invoice Summary**
   - Customer, invoice number, dates, remaining/total, external doc no.
2) **Invoice Lines**
   - Data source: `accounts-receivable/invoices/{invoice_no}/lines`.
   - Columns: line no, item no, description, quantity, unit price, line amount.

### C) Filters and Controls
Global filters (applied to both lists when possible):
- Due date range
- Customer number
- Minimum avg days late
- Minimum late ratio
- Page size

Refresh:
- Manual refresh button
- Show cache timestamp for payment stats (from `payment_stats.updated_at` when available)

## Accountant Usage and Actions

Primary workflow:
1) Start in **Priority Collections** list.
2) Sort by `avg_days_late` and `due_date` to focus on risky overdue invoices.
3) Open invoice details to verify line items before contacting customer.
4) Take action:
   - Call / email customer
   - Send reminder
   - Escalate to account manager
   - Add a follow-up date in a task system (front-end integration as needed)

Secondary workflow:
1) Review **Open Invoices** for near-due items.
2) Sort by `due_date` to prioritize upcoming collections.
3) Contact customers proactively to reduce late payments.

## Sorting and Ranking Rules (Recommended Defaults)
1) **Priority Collections**
   - `payment_stats.avg_days_late` desc
   - `invoice.due_date` asc
   - `invoice.remaining_amount` desc

2) **Open Invoices**
   - `invoice.due_date` asc
   - `invoice.remaining_amount` desc

## Error Handling
Display friendly errors for:
- `401 Unauthorized` (missing/invalid `X-Finance-Token`)
- `502/503` (ERP or service not available)

## Performance Notes
- Collections stats are cached weekly; show `payment_stats.updated_at` to clarify freshness.
- Use pagination for large invoice lists.

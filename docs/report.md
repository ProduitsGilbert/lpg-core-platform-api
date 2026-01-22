# Planner Daily Report (BC → Daily summary)

This document explains how `planner_daily_report/` builds the daily report that the planner used to assemble manually in Business Central.

The goal is to produce, **every day**, a simple summary:

- Per work center: **MO fait / MO reste**
- Factory-wide customer load: **GI###### hours done / hours remaining**

## 1) Data sources (Business Central OData)

The logic uses **two OData endpoints** (names are tenant-dependent but this tenant provides these):

### A) Past accomplished work (yesterday / last business day)

- Endpoint: `CapacityLedgerEntries`
- Purpose: what was accomplished on the posting date

Key fields used:
- `Posting_Date` (Edm.Date)
- `Work_Center_No`
- `Order_No` (manufacturing order no)
- `Quantity` (important: rows with `Quantity == 0` must **not** count for “MO fait”)
- `WSI_Job_No` (used to detect customer jobs `GI######`)
- `Setup_Time`, `Run_Time` (minutes; used for load)
- `Description` (used as best-effort work center label hint because `WorkCenters` master endpoint is not available in this tenant)

### B) Future schedule (“reste”)

- Endpoint: `WorkCenterTaskList`
- Purpose: what is coming next in the schedule per work center

Key fields used (from a probe on this tenant):
- `WorkCenterNo`
- `Prod_Order_No`
- `Operation_No`
- `Status` (we only keep `Released`)
- `WSI_Job_No_XXXXX` (tenant-specific suffix; we scan any key that starts with `WSI_Job_No`)
- `Setup_Time`, `Run_Time` (minutes)
- `Description` (best-effort label hint)
- `Starting_Date`, `Ending_Date` (available but not required for filtering in the planner’s current definition)

## 2) Filters and business rules

### “Yesterday” means last business day

The CLI treats `--date yesterday` as:
- Monday → Friday
- Sunday → Friday
- Saturday → Friday
- Tue–Fri → previous day

### Accomplished: exclude Quantity == 0

For `CapacityLedgerEntries`, **do not count** rows where:

- `Quantity == 0`

This prevents inflating “MO fait” with administrative/zero-output rows.

### Customer load: GI###### only (exclude GIM…)

Customer jobs are identified by:

- `WSI_Job_No` matching `GI\\d{6}` (case-insensitive)

Excluded:
- `GIM...` (project jobs)

### Future (“reste”): Released only

For `WorkCenterTaskList`, only include rows where:

- `Status == 'Released'`

This filter drives both:
- `RESTE X MO` counts
- GI###### hours remaining

## 3) Calculations

### MO fait (per work center)

From `CapacityLedgerEntries` on the report date:

- Group by `Work_Center_No`
- Count **unique `Order_No`** where at least one entry has `Quantity > 0`

### MO reste (per work center)

From `WorkCenterTaskList` (Released only):

- Group by `WorkCenterNo`
- Count **unique `Prod_Order_No`** (default behavior)

### Customer load GI###### (factory-wide)

We compute this factory-wide (not per work center):

- **Done**: sum of minutes from `CapacityLedgerEntries` (on the report date) where `WSI_Job_No` is `GI\\d{6}` and `Quantity > 0`
- **Remaining**: sum of minutes from `WorkCenterTaskList` (Released only) where the job no is `GI\\d{6}`

Minutes-to-hours:
- Hours = minutes / 60, displayed with 1–2 decimals in different outputs.

Minutes source:
- Prefer `Setup_Time + Run_Time` (both are in minutes)
- If not available, fall back to `(Ending_Time - Starting_Time)` (best effort)

## 4) Tenant quirks / implementation details

### Posting_Date filters may not be honored on CapacityLedgerEntries

In this tenant, server-side filters like:

- `Posting_Date eq 2026-01-13`

were not reliably applied (returned rows from other dates). To keep the report correct, we:

- Fetch recent rows ordered by `Posting_Date desc, Entry_No desc`
- Filter client-side to the desired date
- Stop when we pass the target date (performance)

### Work center master endpoint not available

`WorkCenters` returned 404 in this tenant, so the report uses best-effort name hints from:

- `WorkCenterTaskList.Description`
- `CapacityLedgerEntries.Description`

If a Work Center master endpoint becomes available later, update `planner_daily_report/bc_workcenters.py` to resolve No → Name reliably.

## 5) Outputs

### CLI (human text)

- `python3 -m planner_daily_report.cli report --env-file .env`

Shows:
- `CHARGE CLIENT (GI######)` as a single factory-wide line
- Per work center: `No - Name - X MO FAIT / RESTE Y MO`

### JSON (FastAPI-friendly)

- `python3 -m planner_daily_report.export_json --env-file .env --out /tmp/report.json`

Or call the service function:

- `planner_daily_report.service.generate_daily_planner_report(...)`

### FastAPI endpoint (Core Platform)

- `GET /api/v1/kpi/planning/daily-report?date=yesterday`
- Optional extra task list filter: `&tasklist_filter=WorkCenterNo%20eq%20'CNCT'`

## 6) FastAPI integration sketch

The core integration idea is: reuse the service function in an API route.

Pseudo-example:

```python
from fastapi import FastAPI
import datetime as dt
from planner_daily_report.service import generate_daily_planner_report

app = FastAPI()

@app.get("/planner/daily-report")
def daily_report(date: str = "yesterday"):
    # parse date like the CLI does (or accept YYYY-MM-DD only in the API)
    posting_date = dt.date.fromisoformat(date)  # simplest
    return generate_daily_planner_report(posting_date=posting_date)
```



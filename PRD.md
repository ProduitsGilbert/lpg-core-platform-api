 
🧠 EXECUTION PROMPT — 
Minimal FastAPI Core
 (single app, no Celery)

You are generating a production-ready but minimal FastAPI project that fronts an ERP (Business Central On-Prem v18 / MS SQL Server). It will:
•	Centralize reads/writes for Purchasing first (POs, lines, receipts, returns, vendors, items, quotes).
•	Call OCR and AI (local agent + OpenAI) via thin adapters.
•	Enforce type validation before any ERP write.
•	Provide idempotency + audit using MS SQL (no separate broker/queue).
•	Use Logfire for tracing/logs (no structlog).

Throughput is low (a few requests/min). Keep it simple:
•	One app container (FastAPI/Uvicorn).
•	Synchronous SQLAlchemy (MSSQL via pyodbc) with a threadpool.
•	Background work via FastAPI BackgroundTasks. (Optional: add APScheduler later.)
•	No Celery, no Redis, no Kafka.

Tech & packages
•	Python 3.11+, FastAPI, Uvicorn
•	Pydantic v2
•	SQLAlchemy 2.x + pyodbc (mssql +pyodbc)
•	httpx
•	tenacity (for adapter retries)
•	logfire (already in use)
•	(Optional but include stubs): APScheduler toggled off by default

Project layout (small, deliberate)
app/
  main.py               # FastAPI app init, Logfire init, routers include
  settings.py           # Pydantic Settings; feature flags; DSNs
  deps.py               # common deps: DB session, user/source, idempotency key
  db.py                 # SQLAlchemy engine/session; MSSQL
  errors.py             # typed exceptions, to-HTTP mapping
  audit.py              # simple audit writer (DB), helper for idempotency
  adapters/
    erp_client.py       # wraps current legacy write funcs; swap later to official API
    ocr_client.py       # tesseract/azure placeholder
    ai_client.py        # local agent + OpenAI wrapper
  domain/
    purchasing_service.py  # business rules for PO/lines/receipts/returns
    dtos.py                # Pydantic request/response & command models
  routers/
    health.py
    purchasing.py       # endpoints for key actions (date/price/qty update, post receipt, etc.)
  sql/
    migrations.sql      # minimal DDL for app tables (idempotency, audit)
tests/
  test_update_poline_date.py
Dockerfile
docker-compose.yml
.env.example
README.md
Configuration (env)
•	DB_DSN=mssql+pyodbc://user:pass@SERVER/DB?driver=ODBC+Driver+17+for+SQL+Server&TrustServerCertificate=yes
•	ERP_MODE=legacy|official|canary (default legacy)
•	ERP_BASE_URL= (if using official API later)
•	LOGFIRE_API_KEY=...
•	OPENAI_API_KEY= (optional)
•	LOCAL_AGENT_BASE_URL= (optional)

Database (only app state, 
not
 mirroring ERP)

Create two tiny tables in MSSQL (DDL in sql/migrations.sql):
CREATE TABLE platform-code-app_idempotency (
  key NVARCHAR(128) PRIMARY KEY,
  created_at DATETIME2 DEFAULT SYSUTCDATETIME(),
  response_json NVARCHAR(MAX) NULL
);

CREATE TABLE platform-code-app_audit (
  id BIGINT IDENTITY PRIMARY KEY,
  at DATETIME2 DEFAULT SYSUTCDATETIME(),
  actor NVARCHAR(100) NOT NULL,
  action NVARCHAR(100) NOT NULL,   -- e.g., POLine.PromiseDateChanged
  po_id NVARCHAR(50) NULL,
  line_no INT NULL,
  previous NVARCHAR(MAX) NULL,
  next NVARCHAR(MAX) NULL,
  reason NVARCHAR(200) NULL,
  trace_id NVARCHAR(64) NULL
);
Error mapping (keep it small)
•	ValidationError → 422
•	Unauthorized/Forbidden (if you add auth) → 401/403
•	ERPConflict, ERPUnavailable → 409 / 503
•	Fallback → 500

Logfire
•	Initialize early in main.py.
•	Add middleware to attach trace IDs.
•	For each service call, add span attrs: entity=POLine, po_id, line_no, action.

Core concepts (minimal layer responsibilities)
•	Router: HTTP in/out, auth (later), build Pydantic command, call service, return DTO.
•	Service: business rules (dates, quantities), idempotency check, call adapter, write audit, return result.
•	Adapter: single class that calls ERP (for now it calls your legacy Python functions; later switch to official API under a feature flag).
•	DB: only for app_idempotency + app_audit. No ERP mirroring.

Idempotency (simple & safe)
•	Extract Idempotency-Key from header or body.
•	If key exists in app_idempotency, return stored response_json.
•	After a successful write, store the serialized response under that key.
•	Enforce unique constraint via PK (already done).

Example: 
Update PO line promise date

domain/dtos.py
•	UpdatePOLineDateBody { new_date: date, reason: str, idempotency_key: str }
•	POLineDTO { po_id: str, line_no: int, promise_date: date, ... }

adapters/erp_client.py
•	Class ERPClient with:
o	get_poline(po_id, line_no) -> dict
o	update_poline_date(po_id, line_no, new_date) -> dict
•	Implement with your current legacy funcs (import and call).
•	Add tenacity retry stop_after_attempt(3) + wait_exponential_jitter.
•	Honor ERP_MODE for future swap (legacy|official|canary) but keep legacy working now.

domain/purchasing_service.py
•	Function update_poline_date(cmd, db_session) -> POLineDTO:
1.	Check idempotency (read app_idempotency).
2.	Fetch current line via erp.get_poline.
3.	Validate business rule: new_date >= order_date (if available) or at least >= today.
4.	Call erp.update_poline_date.
5.	Write audit row (include reason + old/new).
6.	Store response_json under idempotency key.
7.	Return POLineDTO.

routers/purchasing.py
•	POST /api/v1/purchasing/po/{po_id}/lines/{line_no}/date
o	Body: UpdatePOLineDateBody
o	Use BackgroundTasks optionally for side work (e.g., “recompute KPI”), but the ERP write itself runs inline so the client sees success/failure deterministically.

Background / periodic work (keep it tiny)
•	Use FastAPI BackgroundTasks for small follow-ups (e.g., recompute a cached report).
•	If you truly need a scheduler, add a disabled-by-default APScheduler block with DB-backed lock to avoid double runs:
o	Simple “leader election” via sp_getapplock or a row lock on an app_lock table.
o	Provide a commented example; do not enable by default.

Versioning
•	Use URI versioning: /api/v1/....
•	Only bump routers that break (/api/v2/purchasing/...).
•	Keep shared service/adapter code single-sourced; don’t duplicate items logic across departments.

Deliver 
actual code
 for these files (concise, runnable, typed):
1.	app/main.py
o	FastAPI init, Logfire init, include routers, health route, lifespan checks (DB ping).
2.	app/settings.py
o	Pydantic Settings with fields above + ERP_MODE + CANARY_PERCENT (unused now).
3.	app/db.py
o	SQLAlchemy engine (MSSQL pyodbc), sessionmaker, get_session() dependency.
4.	app/errors.py
o	Define ERPError, ERPConflict, ERPUnavailable; register exception handlers.
5.	app/audit.py
o	Functions: get_idem, save_idem, write_audit. Use plain SQLAlchemy Core for brevity.
6.	app/domain/dtos.py
o	Pydantic v2 models for request/response (strict types, extra='forbid').
7.	app/adapters/erp_client.py
o	Class with the two methods above; stub legacy calls (call into legacy_erp.py placeholder).
8.	app/domain/purchasing_service.py
o	Implement update_poline_date.
9.	app/routers/purchasing.py
o	Implement the POST endpoint with basic auth stub or none; returns POLineDTO.
10.	app/sql/migrations.sql

•	The two tables above.

11.	tests/test_update_poline_date.py

•	Happy path, idempotent replay, bad date → 422, adapter error → mapped HTTP.

Docker (simple)
•	Dockerfile: python:3.11-slim, install unixodbc + driver packages as needed, copy app, uvicorn app.main:app --host 0.0.0.0 --port 7003
•	docker-compose.yml: api only (you already have MSSQL). Provide an example service but comment out an MSSQL service block for local dev if needed.

README.md (short and practical)
•	How to create DSN, run migrations (sql/migrations.sql), run dev (uvicorn), sample curl for the date update with Idempotency-Key.
•	“How to swap ERP later”: set ERP_MODE=official after you implement it inside adapter; nothing else changes.

Coding rules (keep it light)
•	Small modules, docstrings, type hints.
•	Pydantic models with model_config = ConfigDict(extra='forbid').
•	Tenacity on outbound ERP I/O only.
•	Logfire span on service entry + adapter call.

End of minimal prompt. Generate all listed files with working code, not placeholders.
 



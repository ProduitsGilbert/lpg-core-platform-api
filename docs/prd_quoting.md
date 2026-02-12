3) Backend PRD (FastAPI + PDF extraction + LLM + configs)

3.1 Problem statement

Quoting from customer PDFs is slow because it requires:
	•	interpreting technical drawings,
	•	mapping features to feasible machine groups,
	•	building routing steps,
	•	estimating time per step (setup + cycle + handling + inspection),
	•	then pricing and tracking outcome.

3.2 Goals
	1.	Cut time-to-first-draft quote drastically (e.g., from hours to minutes).
	2.	Produce a credible routing scenario (or 2–3 scenarios) with:
	•	machine group selection,
	•	step sequence,
	•	time estimates per step,
	•	assumptions + unknowns,
	•	confidence levels.
	3.	Make it easy for an expert to tweak (swap machine group, adjust times).
	4.	Track lifecycle: draft → sent → won/lost (+ reason).

3.3 Non-goals (to keep you safe from scope creep)
	•	Perfect dimensional reconstruction or 3D model generation from PDF.
	•	Fully automatic quoting “no human in the loop.”
	•	Full CAM toolpath simulation.

3.4 Users
	•	Estimator (primary): wants fastest draft with minimal edits.
	•	Manufacturing engineer (secondary): reviews feasibility/routing.
	•	Sales (secondary): sends/updates quote status and reasons.

3.5 Key workflow
	1.	User creates quote (customer, due date, etc.)
	2.	Upload PDF(s)
	3.	System produces:
	•	extracted metadata (part number, revision, material, qty)
	•	per-page preview images
	4.	User clicks “Generate draft routing”
	5.	System returns 1–3 routing scenarios per part:
	•	steps, machine groups, time breakdown, confidence, highlighted unknowns
	6.	User edits steps/times
	7.	User finalizes and exports quote
	8.	Later: user marks quote won/lost + reason

3.6 Architecture (suggested)

FastAPI as orchestration + CRUD, plus a worker for heavy tasks.
	•	API service (FastAPI)
	•	Auth + RBAC
	•	Quote CRUD
	•	File upload + preview endpoints
	•	Starts analysis jobs
	•	Persists outputs
	•	Worker service (Celery/RQ/Arq)
	•	PDF rendering/extraction
	•	LLM calls (vision + reasoning)
	•	Validations + time calculation
	•	Storage
	•	PostgreSQL for entities + JSON outputs + PDFs (bytea) or object store
	•	Optional: Redis for job queue + caching
	•	Config
	•	machine_groups.yml, machines.yml, time_models.yml
	•	versioned (git) + also store “config_version_id” in the quote for auditability

3.7 PDF processing strategy

You want a two-lane extraction approach:

Lane A: PDF-native extraction (fast, cheap)
	•	Extract embedded text (title block notes often are real text).
	•	Extract tables (revision block, BOM if present).
	•	Pros: precise for typed text, tolerances in notes.
	•	Cons: dimensions often are “drawn text” and may not extract reliably.

Lane B: Vision extraction (LLM on images)
	•	Render each page to high DPI image (e.g., 300–600 DPI).
	•	Make smart crops:
	1.	full page,
	2.	title block crop,
	3.	notes/tolerances crop,
	4.	detail view crop(s) (optional).
	•	Feed these images to the LLM.

This is where Grok-style multimodal models shine: the xAI API is positioned for vision + structured outputs + tool calling.  ￼

3.8 LLM orchestration (recommended multi-step prompts)

Design it like a pipeline of narrow tasks, not one giant prompt.

Step 1 — Document metadata extraction (per PDF)

Input: title block crop + extracted text
Output JSON:
	•	customer part number, internal part number (if any)
	•	revision
	•	units (mm/inch)
	•	material spec
	•	thickness (if plate)
	•	qty requested
	•	general tolerances note
	•	surface finish requirements
	•	welding requirements note
	•	“drawing quality” score (clear / ok / bad)

Step 2 — Part classification & envelope

Input: full page image (+ maybe detail crops)
Output JSON:
	•	shape_class: round | prismatic | sheet | weldment | assembly | unknown
	•	overall envelope X/Y/Z (with confidence per dimension)
	•	key features counts:
	•	holes count (approx), threaded holes count (approx)
	•	machined faces count (approx)
	•	bores count (approx)
	•	pockets/slots count (approx)
	•	weight estimate (if possible from notes) else “unknown”

Step 3 — Complexity scoring (1–5)

Inputs: Step 2 outputs + tolerance notes
Output JSON:
	•	complexity_score (1–5)
	•	drivers: list of reasons
	•	risk flags: e.g., “tight GD&T”, “heavy handling”, “multiple setups likely”

Step 4 — Routing scenario generation (1–3)

Inputs:
	•	extracted features + complexity
	•	machine_groups.yml (retrieved as context)
	•	your routing rules (context doc)
Output JSON (per scenario):
	•	ordered list of steps: operation_code, machine_group_id, description
	•	per step: setup/cycle/handling/inspection time estimates
	•	assumptions + unknowns
	•	confidence score

Step 5 — Deterministic validation + recompute times

This step is not LLM.
	•	Check envelope and constraints vs machine configs.
	•	If LLM chose impossible machine → auto-repair (choose next best) and flag.
	•	Recompute time using your stored time models where possible.
	•	Preserve LLM-provided numbers as fallback if your model lacks coverage.

Step 6 — Human edit loop
	•	UI exposes:
	•	routing steps (editable order, machine group, times)
	•	assumptions list (checkbox “confirmed”)
	•	missing info prompts (e.g., “confirm thickness”, “confirm tolerance zone”)

3.9 Prompting requirements (to reduce hallucination)
	•	Always ask for structured outputs (JSON schema).
	•	Require the model to include evidence pointers:
	•	“I read thickness = 12 mm from title block note line …” (or “from image region title_block”)
	•	Force "unknown" when unclear.
	•	Use a “verification pass”:
	•	second call that checks: units, envelope plausibility, material present, etc.

3.10 Time estimation strategy (hybrid)

Don’t try to make the LLM a CAM simulator. Make it produce feature counts and dimensions; then compute times using:
	•	tables (thickness → plasma speed),
	•	formulas (holes → drilling time),
	•	baseline+modifiers (setup/handling),
	•	plus a small “uncertainty factor”.

Your UI can show:

“Estimated total machining time: 6.2h (confidence: 0.74). Biggest uncertainty: hole count and tolerance interpretation.”

3.11 FastAPI endpoints (suggested)
	•	POST /quotes create quote
	•	GET /quotes?status=&customer= list/search
	•	GET /quotes/{quote_id} details
	•	POST /quotes/{quote_id}/files upload PDF
	•	GET /quotes/{quote_id}/files/{file_id} stream PDF
	•	GET /quotes/{quote_id}/files/{file_id}/pages/{page_no} get rendered page image
	•	POST /quotes/{quote_id}/analyze start extraction pipeline → returns job_id
	•	GET /jobs/{job_id} status + progress + outputs
	•	POST /parts/{part_id}/generate-routings → scenarios
	•	PATCH /routing_steps/{step_id} override time / machine group
	•	PATCH /quotes/{quote_id}/status set won/lost + reason

3.12 Success metrics
	•	Median time from upload → first draft routing < X minutes
	•	% quotes that require only minor edits
	•	Error rate: “machine selected cannot fit part” < 1%
	•	Post-mortem delta: estimated vs actual time within ±20% for common part families (after calibration)

3.13 Risks & mitigations
	1.	Dimensions misread → require confidence + evidence + human confirmation for low confidence.
	2.	Routing hallucination → deterministic validation + machine constraints.
	3.	Time model drift → store actuals and recalibrate monthly.
	4.	Sensitive customer data → encryption, RBAC, audit logs.

3.14 Model choice note (Grok)

xAI’s API page explicitly lists grok-4-1-fast-reasoning and positions the platform around vision + tool-calling + structured outputs, with a 2M context window—which is ideal for “whole drawing + extracted text + configs + rules” in one request when needed.  ￼
(You can still keep the pipeline multi-step for reliability and cost.)

⸻


all those table were created sucessfully for this application, on the cedule MS SQL server, to create the needed endpoint to fetch, create, update, delete quote, routing, routing steps etc..  : 

/* ============================================================
   MS SQL Server DDL
   Prefix: 40_VENTES_SOUSTRAITANCE_
   Notes:
   - Uses UNIQUEIDENTIFIER + NEWID()
   - Uses DATETIME2 for timestamps
   - Uses VARBINARY(MAX) for PDF/image storage
   - Uses CHECK constraints instead of PostgreSQL ENUM types
   ============================================================ */

-- Optional (recommended): create a dedicated schema if you want
-- CREATE SCHEMA ventes_soustraitance AUTHORIZATION dbo;
-- GO

/* -------------------------
   1) Lookup tables
------------------------- */

IF OBJECT_ID('[dbo].[40_VENTES_SOUSTRAITANCE_loss_reasons]', 'U') IS NULL
BEGIN
  CREATE TABLE [dbo].[40_VENTES_SOUSTRAITANCE_loss_reasons] (
    [code] NVARCHAR(50) NOT NULL PRIMARY KEY,
    [label] NVARCHAR(200) NOT NULL
  );
END
GO

IF OBJECT_ID('[dbo].[40_VENTES_SOUSTRAITANCE_customers]', 'U') IS NULL
BEGIN
  CREATE TABLE [dbo].[40_VENTES_SOUSTRAITANCE_customers] (
    [customer_id] UNIQUEIDENTIFIER NOT NULL CONSTRAINT [DF_40VSS_customers_id] DEFAULT NEWID(),
    [name] NVARCHAR(200) NOT NULL,
    [email] NVARCHAR(320) NULL,
    [phone] NVARCHAR(50) NULL,
    [created_at] DATETIME2(3) NOT NULL CONSTRAINT [DF_40VSS_customers_created] DEFAULT SYSUTCDATETIME(),
    CONSTRAINT [PK_40VSS_customers] PRIMARY KEY ([customer_id])
  );
END
GO

IF OBJECT_ID('[dbo].[40_VENTES_SOUSTRAITANCE_operation_catalog]', 'U') IS NULL
BEGIN
  CREATE TABLE [dbo].[40_VENTES_SOUSTRAITANCE_operation_catalog] (
    [operation_id] UNIQUEIDENTIFIER NOT NULL CONSTRAINT [DF_40VSS_opcat_id] DEFAULT NEWID(),
    [code] NVARCHAR(50) NOT NULL,
    [name] NVARCHAR(200) NOT NULL,
    [default_unit] NVARCHAR(50) NULL,
    CONSTRAINT [PK_40VSS_opcat] PRIMARY KEY ([operation_id]),
    CONSTRAINT [UQ_40VSS_opcat_code] UNIQUE ([code])
  );
END
GO

IF OBJECT_ID('[dbo].[40_VENTES_SOUSTRAITANCE_machine_groups]', 'U') IS NULL
BEGIN
  CREATE TABLE [dbo].[40_VENTES_SOUSTRAITANCE_machine_groups] (
    [machine_group_id] NVARCHAR(100) NOT NULL,   -- e.g. "CNC_BORING_LARGE_4AX" (matches YAML)
    [name] NVARCHAR(200) NOT NULL,
    [process_families_json] NVARCHAR(MAX) NULL,  -- store as JSON text for flexibility
    [config_json] NVARCHAR(MAX) NULL,            -- store parsed YAML/config JSON for audit
    [updated_at] DATETIME2(3) NOT NULL CONSTRAINT [DF_40VSS_mg_updated] DEFAULT SYSUTCDATETIME(),
    CONSTRAINT [PK_40VSS_mg] PRIMARY KEY ([machine_group_id])
  );
END
GO

/* -------------------------
   2) Core entities
------------------------- */

IF OBJECT_ID('[dbo].[40_VENTES_SOUSTRAITANCE_quotes]', 'U') IS NULL
BEGIN
  CREATE TABLE [dbo].[40_VENTES_SOUSTRAITANCE_quotes] (
    [quote_id] UNIQUEIDENTIFIER NOT NULL CONSTRAINT [DF_40VSS_quotes_id] DEFAULT NEWID(),
    [quote_number] NVARCHAR(50) NULL, -- optional, can be generated
    [customer_id] UNIQUEIDENTIFIER NOT NULL,
    [status] NVARCHAR(20) NOT NULL CONSTRAINT [DF_40VSS_quotes_status] DEFAULT N'draft',
    [currency] NVARCHAR(10) NOT NULL CONSTRAINT [DF_40VSS_quotes_currency] DEFAULT N'CAD',
    [due_date] DATE NULL,

    [created_at] DATETIME2(3) NOT NULL CONSTRAINT [DF_40VSS_quotes_created] DEFAULT SYSUTCDATETIME(),
    [updated_at] DATETIME2(3) NOT NULL CONSTRAINT [DF_40VSS_quotes_updated] DEFAULT SYSUTCDATETIME(),

    [sent_at] DATETIME2(3) NULL,
    [closed_at] DATETIME2(3) NULL,
    [loss_reason_code] NVARCHAR(50) NULL,
    [loss_reason_note] NVARCHAR(MAX) NULL,

    [notes] NVARCHAR(MAX) NULL,

    CONSTRAINT [PK_40VSS_quotes] PRIMARY KEY ([quote_id]),
    CONSTRAINT [UQ_40VSS_quotes_number] UNIQUE ([quote_number]),
    CONSTRAINT [FK_40VSS_quotes_customer] FOREIGN KEY ([customer_id])
      REFERENCES [dbo].[40_VENTES_SOUSTRAITANCE_customers]([customer_id]),

    CONSTRAINT [FK_40VSS_quotes_lossreason] FOREIGN KEY ([loss_reason_code])
      REFERENCES [dbo].[40_VENTES_SOUSTRAITANCE_loss_reasons]([code]),

    CONSTRAINT [CK_40VSS_quotes_status] CHECK ([status] IN (N'draft', N'in_review', N'sent', N'won', N'lost', N'cancelled'))
  );
END
GO

IF OBJECT_ID('[dbo].[40_VENTES_SOUSTRAITANCE_quote_files]', 'U') IS NULL
BEGIN
  CREATE TABLE [dbo].[40_VENTES_SOUSTRAITANCE_quote_files] (
    [file_id] UNIQUEIDENTIFIER NOT NULL CONSTRAINT [DF_40VSS_files_id] DEFAULT NEWID(),
    [quote_id] UNIQUEIDENTIFIER NOT NULL,
    [filename] NVARCHAR(260) NOT NULL,
    [content_type] NVARCHAR(100) NOT NULL CONSTRAINT [DF_40VSS_files_ct] DEFAULT N'application/pdf',
    [sha256] NVARCHAR(64) NULL,
    [file_bytes] VARBINARY(MAX) NOT NULL,
    [uploaded_at] DATETIME2(3) NOT NULL CONSTRAINT [DF_40VSS_files_uploaded] DEFAULT SYSUTCDATETIME(),
    CONSTRAINT [PK_40VSS_files] PRIMARY KEY ([file_id]),
    CONSTRAINT [FK_40VSS_files_quote] FOREIGN KEY ([quote_id])
      REFERENCES [dbo].[40_VENTES_SOUSTRAITANCE_quotes]([quote_id]) ON DELETE CASCADE
  );
END
GO

IF OBJECT_ID('[dbo].[40_VENTES_SOUSTRAITANCE_quote_file_pages]', 'U') IS NULL
BEGIN
  CREATE TABLE [dbo].[40_VENTES_SOUSTRAITANCE_quote_file_pages] (
    [page_id] UNIQUEIDENTIFIER NOT NULL CONSTRAINT [DF_40VSS_pages_id] DEFAULT NEWID(),
    [file_id] UNIQUEIDENTIFIER NOT NULL,
    [page_no] INT NOT NULL,
    [dpi] INT NOT NULL CONSTRAINT [DF_40VSS_pages_dpi] DEFAULT (300),
    [width_px] INT NULL,
    [height_px] INT NULL,
    [image_png] VARBINARY(MAX) NULL,
    [extracted_text] NVARCHAR(MAX) NULL,
    CONSTRAINT [PK_40VSS_pages] PRIMARY KEY ([page_id]),
    CONSTRAINT [UQ_40VSS_pages_file_pageno] UNIQUE ([file_id], [page_no]),
    CONSTRAINT [FK_40VSS_pages_file] FOREIGN KEY ([file_id])
      REFERENCES [dbo].[40_VENTES_SOUSTRAITANCE_quote_files]([file_id]) ON DELETE CASCADE
  );
END
GO

IF OBJECT_ID('[dbo].[40_VENTES_SOUSTRAITANCE_quote_parts]', 'U') IS NULL
BEGIN
  CREATE TABLE [dbo].[40_VENTES_SOUSTRAITANCE_quote_parts] (
    [part_id] UNIQUEIDENTIFIER NOT NULL CONSTRAINT [DF_40VSS_parts_id] DEFAULT NEWID(),
    [quote_id] UNIQUEIDENTIFIER NOT NULL,

    [customer_part_number] NVARCHAR(100) NULL,
    [internal_part_number] NVARCHAR(100) NULL,
    [description] NVARCHAR(500) NULL,
    [quantity] INT NOT NULL CONSTRAINT [DF_40VSS_parts_qty] DEFAULT (1),

    [material] NVARCHAR(200) NULL,
    [thickness_mm] DECIMAL(18,4) NULL,
    [weight_kg] DECIMAL(18,4) NULL,

    [envelope_x_mm] DECIMAL(18,4) NULL,
    [envelope_y_mm] DECIMAL(18,4) NULL,
    [envelope_z_mm] DECIMAL(18,4) NULL,

    [shape] NVARCHAR(20) NOT NULL CONSTRAINT [DF_40VSS_parts_shape] DEFAULT N'unknown',
    [complexity_score] INT NULL,

    [source_file_id] UNIQUEIDENTIFIER NULL,
    [source_page_no] INT NULL,

    [created_at] DATETIME2(3) NOT NULL CONSTRAINT [DF_40VSS_parts_created] DEFAULT SYSUTCDATETIME(),
    [updated_at] DATETIME2(3) NOT NULL CONSTRAINT [DF_40VSS_parts_updated] DEFAULT SYSUTCDATETIME(),

    CONSTRAINT [PK_40VSS_parts] PRIMARY KEY ([part_id]),
    CONSTRAINT [FK_40VSS_parts_quote] FOREIGN KEY ([quote_id])
      REFERENCES [dbo].[40_VENTES_SOUSTRAITANCE_quotes]([quote_id]) ON DELETE CASCADE,

    CONSTRAINT [FK_40VSS_parts_sourcefile] FOREIGN KEY ([source_file_id])
      REFERENCES [dbo].[40_VENTES_SOUSTRAITANCE_quote_files]([file_id]),

    CONSTRAINT [CK_40VSS_parts_shape] CHECK ([shape] IN (N'round', N'sheet', N'prismatic', N'weldment', N'assembly', N'unknown')),
    CONSTRAINT [CK_40VSS_parts_complexity] CHECK ([complexity_score] IS NULL OR ([complexity_score] BETWEEN 1 AND 5))
  );
END
GO

IF OBJECT_ID('[dbo].[40_VENTES_SOUSTRAITANCE_part_extractions]', 'U') IS NULL
BEGIN
  CREATE TABLE [dbo].[40_VENTES_SOUSTRAITANCE_part_extractions] (
    [extraction_id] UNIQUEIDENTIFIER NOT NULL CONSTRAINT [DF_40VSS_extract_id] DEFAULT NEWID(),
    [part_id] UNIQUEIDENTIFIER NOT NULL,
    [model_name] NVARCHAR(100) NOT NULL,
    [prompt_version] NVARCHAR(50) NOT NULL,
    [extracted_json] NVARCHAR(MAX) NOT NULL,  -- store JSON as text; validate in app if desired
    [confidence] DECIMAL(5,4) NULL,
    [created_at] DATETIME2(3) NOT NULL CONSTRAINT [DF_40VSS_extract_created] DEFAULT SYSUTCDATETIME(),
    CONSTRAINT [PK_40VSS_extract] PRIMARY KEY ([extraction_id]),
    CONSTRAINT [FK_40VSS_extract_part] FOREIGN KEY ([part_id])
      REFERENCES [dbo].[40_VENTES_SOUSTRAITANCE_quote_parts]([part_id]) ON DELETE CASCADE
  );
END
GO

/* -------------------------
   3) Routing & steps
------------------------- */

IF OBJECT_ID('[dbo].[40_VENTES_SOUSTRAITANCE_part_routings]', 'U') IS NULL
BEGIN
  CREATE TABLE [dbo].[40_VENTES_SOUSTRAITANCE_part_routings] (
    [routing_id] UNIQUEIDENTIFIER NOT NULL CONSTRAINT [DF_40VSS_routing_id] DEFAULT NEWID(),
    [part_id] UNIQUEIDENTIFIER NOT NULL,
    [scenario_name] NVARCHAR(200) NOT NULL,     -- "Baseline", "Alt: 5-axis"
    [created_by] NVARCHAR(200) NULL,            -- username/id
    [selected] BIT NOT NULL CONSTRAINT [DF_40VSS_routing_selected] DEFAULT (0),
    [rationale] NVARCHAR(MAX) NULL,
    [created_at] DATETIME2(3) NOT NULL CONSTRAINT [DF_40VSS_routing_created] DEFAULT SYSUTCDATETIME(),
    CONSTRAINT [PK_40VSS_routings] PRIMARY KEY ([routing_id]),
    CONSTRAINT [FK_40VSS_routings_part] FOREIGN KEY ([part_id])
      REFERENCES [dbo].[40_VENTES_SOUSTRAITANCE_quote_parts]([part_id]) ON DELETE CASCADE
  );
END
GO

-- Enforce "only one selected routing per part"
IF NOT EXISTS (
  SELECT 1
  FROM sys.indexes
  WHERE name = 'UX_40VSS_routings_one_selected_per_part'
    AND object_id = OBJECT_ID('[dbo].[40_VENTES_SOUSTRAITANCE_part_routings]')
)
BEGIN
  CREATE UNIQUE INDEX [UX_40VSS_routings_one_selected_per_part]
  ON [dbo].[40_VENTES_SOUSTRAITANCE_part_routings]([part_id])
  WHERE [selected] = 1;
END
GO

IF OBJECT_ID('[dbo].[40_VENTES_SOUSTRAITANCE_routing_steps]', 'U') IS NULL
BEGIN
  CREATE TABLE [dbo].[40_VENTES_SOUSTRAITANCE_routing_steps] (
    [step_id] UNIQUEIDENTIFIER NOT NULL CONSTRAINT [DF_40VSS_step_id] DEFAULT NEWID(),
    [routing_id] UNIQUEIDENTIFIER NOT NULL,
    [step_no] INT NOT NULL,

    [operation_id] UNIQUEIDENTIFIER NOT NULL,
    [machine_group_id] NVARCHAR(100) NULL,

    [description] NVARCHAR(MAX) NULL,

    [setup_time_min] DECIMAL(18,4) NOT NULL CONSTRAINT [DF_40VSS_step_setup] DEFAULT (0),
    [cycle_time_min] DECIMAL(18,4) NOT NULL CONSTRAINT [DF_40VSS_step_cycle] DEFAULT (0),
    [handling_time_min] DECIMAL(18,4) NOT NULL CONSTRAINT [DF_40VSS_step_handling] DEFAULT (0),
    [inspection_time_min] DECIMAL(18,4) NOT NULL CONSTRAINT [DF_40VSS_step_insp] DEFAULT (0),

    [qty_basis] INT NOT NULL CONSTRAINT [DF_40VSS_step_qtybasis] DEFAULT (1),
    [user_override] BIT NOT NULL CONSTRAINT [DF_40VSS_step_override] DEFAULT (0),

    [estimator_note] NVARCHAR(MAX) NULL,
    [time_confidence] DECIMAL(5,4) NULL,
    [source] NVARCHAR(20) NOT NULL CONSTRAINT [DF_40VSS_step_source] DEFAULT N'llm',

    CONSTRAINT [PK_40VSS_steps] PRIMARY KEY ([step_id]),
    CONSTRAINT [UQ_40VSS_steps_routing_stepno] UNIQUE ([routing_id], [step_no]),

    CONSTRAINT [FK_40VSS_steps_routing] FOREIGN KEY ([routing_id])
      REFERENCES [dbo].[40_VENTES_SOUSTRAITANCE_part_routings]([routing_id]) ON DELETE CASCADE,

    CONSTRAINT [FK_40VSS_steps_operation] FOREIGN KEY ([operation_id])
      REFERENCES [dbo].[40_VENTES_SOUSTRAITANCE_operation_catalog]([operation_id]),

    CONSTRAINT [FK_40VSS_steps_machinegroup] FOREIGN KEY ([machine_group_id])
      REFERENCES [dbo].[40_VENTES_SOUSTRAITANCE_machine_groups]([machine_group_id]),

    CONSTRAINT [CK_40VSS_step_source] CHECK ([source] IN (N'llm', N'rules', N'user'))
  );
END
GO

/* -------------------------
   4) LLM run audit
------------------------- */

IF OBJECT_ID('[dbo].[40_VENTES_SOUSTRAITANCE_llm_runs]', 'U') IS NULL
BEGIN
  CREATE TABLE [dbo].[40_VENTES_SOUSTRAITANCE_llm_runs] (
    [run_id] UNIQUEIDENTIFIER NOT NULL CONSTRAINT [DF_40VSS_run_id] DEFAULT NEWID(),
    [quote_id] UNIQUEIDENTIFIER NULL,
    [part_id] UNIQUEIDENTIFIER NULL,
    [stage] NVARCHAR(50) NOT NULL,          -- "metadata", "features", "routing"
    [model_name] NVARCHAR(100) NOT NULL,
    [input_json] NVARCHAR(MAX) NULL,
    [output_json] NVARCHAR(MAX) NULL,
    [started_at] DATETIME2(3) NOT NULL CONSTRAINT [DF_40VSS_run_started] DEFAULT SYSUTCDATETIME(),
    [ended_at] DATETIME2(3) NULL,
    [status] NVARCHAR(20) NOT NULL CONSTRAINT [DF_40VSS_run_status] DEFAULT N'ok',
    [error_text] NVARCHAR(MAX) NULL,
    CONSTRAINT [PK_40VSS_runs] PRIMARY KEY ([run_id]),
    CONSTRAINT [CK_40VSS_run_status] CHECK ([status] IN (N'ok', N'error'))
  );
END
GO

/* -------------------------
   5) Indexes (performance)
------------------------- */

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_40VSS_quotes_customer' AND object_id = OBJECT_ID('[dbo].[40_VENTES_SOUSTRAITANCE_quotes]'))
  CREATE INDEX [IX_40VSS_quotes_customer] ON [dbo].[40_VENTES_SOUSTRAITANCE_quotes]([customer_id]);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_40VSS_parts_quote' AND object_id = OBJECT_ID('[dbo].[40_VENTES_SOUSTRAITANCE_quote_parts]'))
  CREATE INDEX [IX_40VSS_parts_quote] ON [dbo].[40_VENTES_SOUSTRAITANCE_quote_parts]([quote_id]);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_40VSS_routings_part' AND object_id = OBJECT_ID('[dbo].[40_VENTES_SOUSTRAITANCE_part_routings]'))
  CREATE INDEX [IX_40VSS_routings_part] ON [dbo].[40_VENTES_SOUSTRAITANCE_part_routings]([part_id]);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_40VSS_steps_routing' AND object_id = OBJECT_ID('[dbo].[40_VENTES_SOUSTRAITANCE_routing_steps]'))
  CREATE INDEX [IX_40VSS_steps_routing] ON [dbo].[40_VENTES_SOUSTRAITANCE_routing_steps]([routing_id]);
GO
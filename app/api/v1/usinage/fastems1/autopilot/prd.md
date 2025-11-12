Here we go: one clean PRD.md and then a separate checklist of data sources you’ll need to feed your agent.

⸻

PRD.md – Fastems1 Autopilot

1. Overview

Fastems1 is a palletized CNC cell with:
	•	4 identical CNC machines: DMC1, DMC2, DMC3, DMC4
	•	A Fastems crane system handling:
	•	Material pallets (raw material & WIP)
	•	Machine pallets (fixtures + parts)

Currently, operators spend significant time:
	•	Deciding which job to run next,
	•	Hunting through multiple databases (Fastems Oracle, SQL, CNC, tooling, fixtures),
	•	Managing setup vs. cutting time manually.

Fastems2 already behaves in a more “autopilot” way.
Goal: give Fastems1 the same kind of intelligence via a Python FastAPI “Autopilot” service.

The Autopilot should:
	•	Continuously maintain a short-horizon schedule (planned jobs per machine),
	•	Provide system-wide best-next-job suggestions across all 4 machines,
	•	Adapt behavior to time of day (morning restart vs normal day vs night prep),
	•	Log decisions, setups, and tool usage into fastems1.Autopilot.* tables for learning and analytics.

Note: the physical schema & columns of fastems1.Autopilot.* are documented separately in datastructure.md.

⸻

2. Objectives

2.1 Functional objectives
	1.	Global next job suggestion
	•	Given the current state of the cell, the Autopilot must return the best next job (WorkOrder + Part + Operation + Machine + Pallets), system-wide.
	•	It must decide which machine is best, prioritizing minimal tool changes and minimal overall penalty.
	2.	Time-aware behavior (shift windows)
	•	Use shift windows (MorningRestart / Day / EveningNightPrep) to change priorities:
	•	Morning: restart all machines quickly using short setup jobs.
	•	Day: balanced flow.
	•	End-of-shift: accept longer setups for long-running night programs.
	3.	Short-horizon schedule (planned jobs)
	•	Maintain a rolling schedule in fastems1.AutopilotPlannedJob for each machine:
	•	e.g., 3–5 planned jobs per machine.
	•	A separate scheduler (already existing) will periodically trigger a plan refresh endpoint.
	4.	Operator control & refusal
	•	Operator (or external service) can refuse a suggested job.
	•	That job (WorkOrder + Part + Operation, optionally pallet) must be ignored for at least 1 day.
	5.	Machine availability control
	•	Machines can be set to unavailable / available manually via an endpoint.
	•	Unavailable machines must not receive jobs in planning or suggestions.
	6.	Detailed action instructions
	•	Suggestion must include a structured action plan, such as:
	•	Unload finished part only.
	•	Or unload part and fixture 24B, then mount fixture 44C, then load raw material for part ABC.
	•	Include required fixture hardware & locations in the suggestion (where possible).
	7.	Automatic setup timing (from Oracle logs)
	•	Use your existing scheduling service (which watches Fastems1 Oracle logs) to:
	•	Detect loading station IN/OUT.
	•	Call Autopilot endpoints to mark start/end of setup sessions.
	•	This provides real setup times for analysis and tuning.

2.2 Non-functional objectives
	•	No changes to existing Fastems UI or application URLs.
	•	Reads data from existing production systems in read-only mode.
	•	Writes only to fastems1.Autopilot.* tables.
	•	Target interactive latency for /autopilot/next: < 1 second for current data scale.
	•	System must be observable & debuggable via logs and DB data (no opaque magic).

⸻

3. Scope

3.1 In scope
	•	FastAPI module under something like:
	•	Machining/Fastems1/Autopilot/…
	•	Candidate job generation and scoring.
	•	Short-horizon planning stored in fastems1.AutopilotPlannedJob.
	•	Endpoints for:
	•	Plan refresh
	•	Next suggestion
	•	Job refusal
	•	Machine status set/unset
	•	Fixture/setup start & end (called by your existing scheduler)
	•	Telemetry:
	•	Decision logging
	•	Setup session logging
	•	Tool usage events
	•	Pallet usage aggregation (via nightly batch)
	•	Integration of shift windows for behavior tuning.

3.2 Out of scope (v1)
	•	Direct insertion of jobs into Fastems control / queues (no direct command-and-control).
	•	Global multi-day optimization; v1 is a short-horizon rolling planner, not a full-blown MES.
	•	Tool wear / life prediction (can be added later, using tool events).

⸻

4. System context

4.1 Components
	•	Autopilot FastAPI service
	•	Implements endpoints, planning logic, logging, and uses the fastems1.Autopilot.* tables.
	•	Existing scheduling/orchestration service
	•	Periodically triggers /plan/refresh.
	•	Watches Fastems Oracle logs for loading-station IN/OUT and calls setup start/end endpoints.
	•	Existing data sources
	•	Fastems1 Oracle DB (pallets, crane moves, loading station events, WIP).
	•	SQL DB(s) with parts, operations, fixtures, tools, work orders, etc.
	•	CNC controllers / NC program registries.
	•	SQL Server DB for Autopilot
	•	Schema fastems1 with Autopilot tables (see datastructure.md).

4.2 Data flow (high-level)
	1.	External scheduler → /plan/refresh
→ Autopilot rebuilds AutopilotPlannedJob.
	2.	Operator / cell state changes → /autopilot/next
→ Autopilot reads:
	•	current plan batch,
	•	machine statuses,
	•	ignore list,
	•	latest tool/fixture/material state,
→ picks best candidate, logs to AutopilotDecision, and returns suggestion.
	3.	Oracle watcher → /fixture/setup/start & /fixture/setup/end
→ Autopilot writes timing to AutopilotSetupSession.
	4.	Operator refusal → /autopilot/refuse
→ Autopilot writes to AutopilotJobIgnore.
	5.	Manual machine availability change → /machine/status
→ Autopilot updates AutopilotMachineStatus.

⸻

5. Functional requirements

5.1 Plan refresh

Endpoint:
POST /machining/fastems1/autopilot/plan/refresh

Behavior:
	•	Reads current backlog of jobs:
	•	Work orders / parts / operations that still need to be machined on DMC machines.
	•	Reads current:
	•	Fixture availability / state (base + part fixtures).
	•	Raw/WIP material availability & locations.
	•	Machine statuses (from AutopilotMachineStatus).
	•	Tool/NC program availability (via data providers).
	•	Ignore list (AutopilotJobIgnore).
	•	Applies shift window from AutopilotShiftWindow to tune scoring.
	•	Builds a new plan batch (PlanBatchId) with:
	•	A sequence of AutopilotPlannedJob entries for each machine.
	•	For each job:
	•	MachineId, SequenceIndex
	•	WorkOrder, PartId, OperationId
	•	MachinePalletId, MaterialPalletId
	•	EstimatedSetupMinutes, EstimatedCycleMinutes
	•	Optionally mark older plan batches as obsolete (implementation detail).

5.2 Next suggestion

Endpoint:
POST /machining/fastems1/autopilot/next

Inputs:
	•	Optional:
	•	List of currently free machines (or Autopilot can derive it from its view/state).
	•	Max number of alternatives to return (max_alternatives).

Behavior:
	1.	Identify active PlanBatchId and retrieve next pending job per machine:
	•	For each available machine (AutopilotMachineStatus.IsAvailable = 1 and Status=available):
	•	Pick the lowest SequenceIndex where Status='planned'.
	2.	Filter out:
	•	Jobs matching any active ignore entry in AutopilotJobIgnore (WorkOrder + Part + Operation, and optionally pallet).
	•	Jobs whose constraints are now invalid (missing tools, no material, fixture no longer available).
	3.	For each remaining candidate (per-machine):
	•	Recompute a score using:
	•	ToolPenalty
	•	SetupPenalty
	•	MaterialPenalty (incl. crane/logistics)
	•	MachineBalancePenalty
	•	Shift window weights (AutopilotShiftWindow).
	4.	Select best candidate globally (not per machine).
	5.	Build detailed action plan:
	•	Determine what is currently on the chosen machine pallet.
	•	Determine needed fixture and hardware:
	•	Example:
	•	unload finished part only,
	•	or unload part + fixture 24B, then load fixture 44C,
	•	then load raw material from a specific material pallet.
	•	Include fixture hardware list and locations.
	6.	Write a row in AutopilotDecision:
	•	All basic fields (WorkOrder, MachineId, pallets, estimates, scores).
	•	Full suggestion in PayloadJson including action_plan.
	7.	Update the corresponding AutopilotPlannedJob row:
	•	Set Status = 'dispatched'.
	•	Set DecisionId to the newly created decision.

Outputs:
	•	decision_id
	•	MachineId, WorkOrder, Part, Operation, Pallets
	•	Estimated setup & cycle times
	•	Score and breakdown
	•	Action plan with structured steps and hardware list
	•	A list of alternatives (optional, top N next options)

5.3 Refusal / cooldown

Endpoint:
POST /machining/fastems1/autopilot/refuse

Inputs:
	•	decision_id
	•	Optional reason

Behavior:
	1.	Load the decision from AutopilotDecision (WorkOrder, PartId, OperationId, MachinePalletId).
	2.	Insert a row into AutopilotJobIgnore:
	•	copy those identifiers,
	•	set IgnoreUntilUtc = TsUtc + 1 day (configurable),
	•	store reason + decision_id.
	3.	Optionally, mark associated AutopilotPlannedJob as skipped.

Effect:
	•	Any job matching (WorkOrder, PartId, OperationId) (and optionally pallet) is excluded from suggestions until after IgnoreUntilUtc.

5.4 Machine status override

Endpoint:
POST /machining/fastems1/autopilot/machine/status

Inputs:
	•	machine_id (DMC1–DMC4)
	•	is_available (bool)
	•	status (e.g. "available", "down", "maintenance")
	•	Optional reason

Behavior:
	•	Upsert into AutopilotMachineStatus.
	•	Planner and plan refresh must honor this status and exclude unavailable machines.

5.5 Setup session tracking

Setup timing is driven by your existing service via Oracle logs.

Endpoints:
	•	POST /machining/fastems1/autopilot/fixture/setup/start
	•	POST /machining/fastems1/autopilot/fixture/setup/end/{setup_id}

Start input:
	•	MachineId
	•	MachinePalletId
	•	WorkOrder, PartId, OperationId (if known)
	•	SetupType ('auto_detected', 'fixture_change', 'part_fitting', etc.)
	•	DecisionId (if this setup comes from a specific suggestion)

Behavior:
	•	Insert into AutopilotSetupSession with TsStartUtc = now.

End behavior:
	•	Update TsEndUtc for the given setup_id.

Usage:
	•	Later analysis of real setup times vs. estimates.
	•	Tuning of SetupPenalty and shift-window weights.

⸻

6. Algorithm – scoring overview

Scoring is not rigidly specified but must respect these principles:
	•	Hard constraints (must be satisfied):
	•	Required tools exist in inventory.
	•	Required NC program is available.
	•	Required fixtures and compatible pallets exist.
	•	Raw/WIP material is available in at least one location.
	•	Machine status is available.
	•	Soft criteria (weighted by shift window):
	•	ToolPenalty: number and cost of tool changes.
	•	SetupPenalty: base + part fixture changes, part fitting effort.
	•	MaterialPenalty: crane moves, loading station time, distance.
	•	LongRun / ShortSetup: favor:
	•	short setups in restart window,
	•	long runs in night_prep.
	•	MachineBalancePenalty: avoid overloading one machine.

The exact numeric weights are configured per window in AutopilotShiftWindow.

⸻

7. Non-functional & phases

7.1 Phases
	•	Phase 1: plumbing
	•	Implement FastAPI skeleton.
	•	Implement data providers reading from your existing DBs.
	•	Implement basic logging to AutopilotDecision.
	•	Phase 2: basic planner
	•	Implement /plan/refresh and /next with minimal scoring.
	•	Implement AutopilotPlannedJob usage.
	•	Phase 3: refusal & machine status
	•	Implement /refuse, AutopilotJobIgnore.
	•	Implement /machine/status, AutopilotMachineStatus.
	•	Phase 4: setup timing from Oracle
	•	Integrate Oracle watcher with /fixture/setup/*.
	•	Use real times in analysis.
	•	Phase 5: shift windows & tuning
	•	Use AutopilotShiftWindow in scoring.
	•	Tune weights based on logged data.

⸻-------------

Data sources & structures you must provide

This is the “shopping list” for your data plumbing. Your agent will need these to implement reliable providers.

A. Core production data

A.1 Work orders & operations

Needed info:
	•	List of active work orders:
	•	WorkOrderId
	•	Customer / Project (optional)
	•	Priority / DueDate
	•	For each work order → parts & operations:
	•	WorkOrderId
	•	PartId, PartNumber, Description
	•	OperationId, OperationNumber (OP10, OP20…)
	•	MachineType (must match DMC family)
	•	RequiredQuantity, CompletedQuantity, RemainingQuantity
	•	PreviousOperationId (for multi-op flow)
	•	EstimatedCycleTime (from CAM or measured)
	•	AllowedMachines (if some ops should avoid a specific DMC)

those information will be available using that endpoint : curl -X 'GET' \
  'https://api.gilbert-tech.com:7776/api/v1/ProductionOrder/AllUnfinishedProductionOrderRoutingLine(40253)' \
  -H 'accept: */*' \
  -H 'RequesterUserID: girda01'
here's a data sample : [
  {
    "systemIdLine": "0cc0b81f-2967-f011-adbf-0050568b51e9",
    "order": 1,
    "noProdOrder": "M174461",
    "lineNo": 10000,
    "prodOrderNo": "M174461-1",
    "status": "Released",
    "sequenceNoForward": 13,
    "opCode": "000600-1OP",
    "workCenterNo": "40253",
    "wsiJobNo": "GIM0884",
    "jobType": "Projet",
    "wsiJobCustomerName": "INTERFOR U.S. INC.",
    "jobDescription": "GIM0884 GEORGETOWN Raboteuse",
    "routingNo": "8432017-03",
    "itemNo": "8432017",
    "description": "S3. prep ADAPTATEUR MOTEUR 75HP",
    "inputQuantity": 2,
    "qtyfait": 0,
    "expectedCapacityNeedMin": 63,
    "dueDate": "2025-10-08",
    "currentOPCptyCreationDateTime": "0001-01-01T00:00:00",
    "startingDateTime": "2025-10-01T04:00:00Z",
    "endingDateTime": "2025-10-01T05:36:49.847Z",
    "routingStatus": "Planned",
    "routingLinkCode": "",
    "previousOperationNo": "000530",
    "previousWorkCenterNo": "40300",
    "previousStatus": "Finished",
    "previousInputQuantity": 2,
    "previousQtyFait": 2,
    "nextOperationNo": "000600-2OP",
    "nextWorkCenterNo": "40253",
    "nextRoutingStatus": "Planned",
    "workcenterFlow": "DMC 100 → DMC 100",
    "currentLocation": "---",
    "prerequisitesMet": true,
    "prerequisites": [
      {
        "description": "MachineReady must be True",
        "isMet": true,
        "currentValue": "True"
      },
      {
        "description": "MaterialAvailable must be at least 50",
        "isMet": true,
        "currentValue": "100"
      }
    ],
    "productionRoutingTasks": {
      "bC_SystemId": "0cc0b81f-2967-f011-adbf-0050568b51e9",
      "bC_Instance": "ProductionBC",
      "statusId": 1,
      "priority": 0,
      "isRush": false,
      "itemNo": "8432017",
      "revision": "03",
      "isReserved": false,
      "currentlyWorkingEmployee": [],
      "currentCumulativeWorkTimer": 0,
      "status": {
        "id": 1,
        "name": "Attente",
        "description": "Étape en Attente",
        "typeName": "ProductionRoutingStatus"
      },
      "reservedOnMachine": {
        "id": 0,
        "workCentorNo": null,
        "machineNumber": 0,
        "description": null
      },
      "comments": [],
      "mainKey": null,
      "typeName": null
    },
    "workCenterCalendarPlannedEntry": [],
    "matchingCncPrograms": [],
    "advancedSchedulerTaskDueDate": "0001-01-01T00:00:00",
    "associatedComponents": [],
    "mainKey": "0cc0b81f-2967-f011-adbf-0050568b51e9",
    "typeName": "RoutingTask"
  }, .... 



A.2 NC program data

Needed info:

Per operation:
	•	ProgramId (unique)
	•	ProgramName (matches CNC naming)
	•	EstimatedRuntimeMinutes (CAM or measured average)
	•	MachineCompatibility (which DMCs can run it)
	•	ProgramStatus:
	•	available / not-generated / obsolete / blocked


⸻

B. Tooling data

B.1 Tool master list

Columns like:
	•	ToolId
	•	ToolNumber / ToolName
	•	Geometry / type (drill, endmill, etc.)
	•	HolderType, Length, Diameter
	•	InventoryLocation (magazine storage, offline storage, crib)
	•	Optional: DefaultMachine, ToolGroup

datasource : curl -X 'GET' \
  'https://api.gilbert-tech.com:7776/api/v1/CNCTooling/MachineTools?machineId=4' \
  -H 'accept: text/plain' \
  -H 'RequesterUserID: girda01'
  [
  {
    "toolId": null,
    "sisterId": 0,
    "deviceNumber": 4,
    "sectionNumber": 0,
    "potNumber": 0,
    "status": 0,
    "remainingLifetime": 0,
    "presetLifetime": 0,
    "usageStatus": "Required",
    "parlecToolDescription": {
      "name": "",
      "description": "",
      "toolType": "",
      "maxLife": 0
    }
  },
  {
    "toolId": 1071,
    "sisterId": 1,
    "deviceNumber": 4,
    "sectionNumber": 1,
    "potNumber": 1,
    "status": 1,
    "remainingLifetime": 1800,
    "presetLifetime": 3000,
    "usageStatus": "Required",
    "parlecToolDescription": {
      "name": "",
      "description": "",
      "toolType": "",
      "maxLife": 0
    }
  },


B.2 Tool requirements per operation

For each (Part, Operation):
	•	ToolId
	•	ToolUsageType (roughing, finishing, etc.)
	•	MinQuantity / PocketRequirement
	•	Optional: MustBeInMachineMagazine vs “can be loaded on demand”.

datasource will with programe example : 8432017-1OP (1OP is first operation)  : curl -X 'GET' \
  'http://lpgadoc03:8585/fastems1/nc_program_tools/8432017-1OP' \
  -H 'accept: application/json'
  Response body
Download
[
  {
    "NC_NAME": "8432017-1OP",
    "GROUP_NBR": 1,
    "TOOL_ID": "1057",
    "ORDER_INDEX": 8,
    "USE_TIME": 662,
    "DESCRIPTION": "FRAISE A RAYON 3/8 SANDVICK"
  },
  {
    "NC_NAME": "8432017-1OP",
    "GROUP_NBR": 1,
    "TOOL_ID": "1077",
    "ORDER_INDEX": 5,
    "USE_TIME": 43,
    "DESCRIPTION": "FRAISE EN BOUT 1/2 S.C. DEROF. KENNA"
  },

B.3 Tool state per machine

For each machine:
	•	Which tools are currently loaded:
	•	MachineId, ToolId, Pocket, LengthOffset, Wear, etc.
	•	Optional: last-used timestamp, tool-life counters.

⸻

C. Fixtures & pallets

C.1 Fixture definitions

Base fixtures (machine pallets):
	•	BaseFixtureId
	•	Name / Type (e.g. “Standard 400x400 plate”, “Vice 160mm”)
	•	CompatiblePartFixtureTypes (jaw families it accepts)
	•	MachinePalletId (if fixed or mapped)

Part fixtures (jaws, dedicated fixtures):
	•	PartFixtureId
	•	Code (e.g. 24B, 44C)
	•	Type / Family
	•	CompatibleBaseFixtureTypes
	•	HardwareBOM: list of required hardware:
	•	hardware item codes,
	•	quantities.

C.2 Fixture location

Where each part fixture and hardware item is:
	•	For each PartFixtureId:
	•	LocationType: rack / pallet / machine / station.
	•	LocationId / label: e.g. “Rack A2 / shelf 3”.
	•	For each hardware item:
	•	Location: bin, shelf, etc.
       
        ⸻

        1. Machine pallet configuration (what is on each pallet)

        Goal for Autopilot:
        Know, for each machine pallet:
            •	Which gabarit/fixture is currently installed (PlaqueReceveuse in Gabarit_PaletteUsinage).
            •	Which plaque model (base fixture class) that gabarit belongs to (from Gabarit_GabaritUsinage + Gabarit_PlaqueReceveuse).
            •	Whether it’s active, on which machine, and what operation is currently associated.

        SELECT
            pu.ID                        AS MachinePalletId,         -- internal ID
            pu.Numero                    AS MachinePalletNumber,     -- human number if used
            pu.Type                      AS MachinePalletType,       -- 0/1/2/3 etc. (vise/gabarit/table...)
            pu.PlaqueReceveuse           AS GabaritNumero,           -- fixture "numero" mounted on this pallet
            pu.Description               AS MachinePalletDescription,
            pu.IsPlaqueActive            AS IsFixtureActive,         -- 1 = active, 0 = inactive?

            -- From Gabarit_GabaritUsinage: definition of the gabarit mounted
            gu.ID                        AS GabaritId,
            gu.Description               AS GabaritDescription,
            gu.PlaqueReceveuse_Numro     AS PlaqueReceveuseModel,    -- foreign key to PlaqueReceveuse.numeroModel

            -- From Gabarit_PlaqueReceveuse: base fixture model info
            pr.description               AS PlaqueReceveuseDescription,
            pr.quantite                  AS PlaqueReceveuseQtyDefined,

            -- Cell status hints
            pu.OperationEnCours          AS CurrentOperationText,    -- e.g. '8317024-1OP' or 'AUCUNE'
            pu.machineEnCours            AS CurrentMachineRunning,   -- if used
            pu.MachinePourPalette        AS PreferredMachine        -- e.g. 'DMC100'

        FROM Cedule.dbo.Gabarit_PaletteUsinage      AS pu
        LEFT JOIN Cedule.dbo.Gabarit_GabaritUsinage AS gu
            ON pu.PlaqueReceveuse = gu.numero       -- PlaqueReceveuse holds the gabarit "numero"
        LEFT JOIN Cedule.dbo.Gabarit_PlaqueReceveuse AS pr
            ON gu.PlaqueReceveuse_Numro = pr.numeroModel;

        Your Autopilot “MachinePallet provider” can hydrate internal models like:
            •	MachinePallet(id, palletNumber, baseFixtureModel, installedFixture, machine, activeFlag, currentOp).

        ⸻

        2. Fixture inventory & locations

        Goal for Autopilot:
        Know:
            •	All available gabarits (fixtures).
            •	For each:
            •	Which plaque model they’re meant to sit on.
            •	Where they are stored (rack position).
            •	Quantity and how much is currently used.

        SELECT
            gu.ID                    AS GabaritId,
            gu.numero                AS GabaritNumero,            -- your "fixture number" like '0140337'
            gu.Description           AS GabaritDescription,
            gu.Quantite              AS GabaritQuantityTotal,
            gu.Quantite_Used         AS GabaritQuantityUsed,

            gu.PlaqueReceveuse_Numro AS PlaqueReceveuseModel,     -- FK to plaque model
            pr.description           AS PlaqueReceveuseDescription,
            pr.quantite              AS PlaqueReceveuseModelQty,  -- how many plaques defined for that model

            gu.Emplacement_Lettre    AS StorageRow,               -- e.g. rack letter
            gu.Emplacement_Chiffre   AS StorageColumn             -- e.g. shelf number
        FROM Cedule.dbo.Gabarit_GabaritUsinage      AS gu
        LEFT JOIN Cedule.dbo.Gabarit_PlaqueReceveuse AS pr
            ON gu.PlaqueReceveuse_Numro = pr.numeroModel;

        This becomes your Fixture Inventory provider:
            •	“gimme all fixtures, their base-model, and where to grab them”.

        ⸻

        3. Piece → fixture mapping (what fixture is needed for which part+op)

        Goal for Autopilot:
        Given a “piece code” like 8406040-1OP, find:
            •	Which gabarit (fixture) is needed.
            •	Its definition & plaque model.
            •	Security class (“Free to Run” vs “Locked”) – this can be used as a scheduling constraint.
            •	Machine type (MachineOperation, e.g. DMC100).

        3.1 All mappings (no filter)

        SELECT
            pg.ID                    AS PieceGabaritId,
            pg.Piece                 AS PieceCode,          -- e.g. '8406040-1OP'
            pg.Gabarit               AS GabaritNumero,      -- fixture number like '0140337'
            pg.FastemsSecurityClass  AS SecurityClass,      -- 'Free To Run', 'Locked', etc.
            pg.MachineOperation      AS MachineOperation,   -- e.g. 'DMC100'

            gu.ID                    AS GabaritId,
            gu.Description           AS GabaritDescription,
            gu.PlaqueReceveuse_Numro AS PlaqueReceveuseModel,
            pr.description           AS PlaqueReceveuseDescription

        FROM Cedule.dbo.Gabarit_PieceGabarit        AS pg
        LEFT JOIN Cedule.dbo.Gabarit_GabaritUsinage AS gu
            ON pg.Gabarit = gu.numero
        LEFT JOIN Cedule.dbo.Gabarit_PlaqueReceveuse AS pr
            ON gu.PlaqueReceveuse_Numro = pr.numeroModel;

        3.2 Parameterized for one piece

        DECLARE @PieceCode NVARCHAR(50) = '8406040-1OP';

        SELECT
            pg.ID                    AS PieceGabaritId,
            pg.Piece                 AS PieceCode,
            pg.Gabarit               AS GabaritNumero,
            pg.FastemsSecurityClass  AS SecurityClass,
            pg.MachineOperation      AS MachineOperation,

            gu.ID                    AS GabaritId,
            gu.Description           AS GabaritDescription,
            gu.PlaqueReceveuse_Numro AS PlaqueReceveuseModel,
            pr.description           AS PlaqueReceveuseDescription

        FROM Cedule.dbo.Gabarit_PieceGabarit        AS pg
        LEFT JOIN Cedule.dbo.Gabarit_GabaritUsinage AS gu
            ON pg.Gabarit = gu.numero
        LEFT JOIN Cedule.dbo.Gabarit_PlaqueReceveuse AS pr
            ON gu.PlaqueReceveuse_Numro = pr.numeroModel
        WHERE pg.Piece = @PieceCode;

        This feeds your PartFixture provider: “for this part+op, what fixture do I need, and on what plaque model?”.

        ⸻

        4. For a given piece, which pallets are already “ready”?

        This is gold for the Autopilot:
        Given a piece code (Piece = “Part + Op”), find any machine pallets that already have the right fixture (gabarit) installed.

        DECLARE @PieceCode NVARCHAR(50) = '8406040-1OP';

        SELECT
            pg.Piece                 AS PieceCode,
            pg.Gabarit               AS RequiredGabaritNumero,
            pg.MachineOperation      AS RequiredMachineOperation,   -- e.g. 'DMC100'

            pu.ID                    AS MachinePalletId,
            pu.Numero                AS MachinePalletNumber,
            pu.PlaqueReceveuse       AS InstalledGabaritNumero,
            pu.Description           AS MachinePalletDescription,
            pu.IsPlaqueActive        AS IsFixtureActive,
            pu.MachinePourPalette    AS MachineForPallet           -- which DMC this pallet is assigned to

        FROM Cedule.dbo.Gabarit_PieceGabarit   AS pg
        JOIN Cedule.dbo.Gabarit_PaletteUsinage AS pu
            ON pu.PlaqueReceveuse = pg.Gabarit   -- pallet currently has the required gabarit installed
        WHERE pg.Piece = @PieceCode;

        Autopilot can use this to give low setup penalty when the pallet is already configured for that part.

        ⸻

        5. Unified “fixture situation” view (recommended as a SQL view)

        If you want to make life easier for your Python agent, you can expose a single view that merges all fixture info into one coherent resultset.

        Example: Cedule.dbo.Autopilot_FixtureMatrix

        CREATE VIEW Cedule.dbo.Autopilot_FixtureMatrix
        AS
        SELECT
            -- Piece (Part+Op) side
            pg.Piece                 AS PieceCode,               -- '8406040-1OP'
            pg.FastemsSecurityClass  AS SecurityClass,
            pg.MachineOperation      AS RequiredMachineOperation,

            -- Required fixture (gabarit)
            pg.Gabarit               AS RequiredGabaritNumero,
            gu.ID                    AS GabaritId,
            gu.Description           AS GabaritDescription,
            gu.Quantite              AS GabaritQuantityTotal,
            gu.Quantite_Used         AS GabaritQuantityUsed,

            -- Required plaque model
            gu.PlaqueReceveuse_Numro AS PlaqueReceveuseModel,
            pr.description           AS PlaqueReceveuseDescription,

            -- Storage location of that fixture
            gu.Emplacement_Lettre    AS FixtureStorageRow,
            gu.Emplacement_Chiffre   AS FixtureStorageColumn,

            -- Where this fixture is currently mounted (if at all)
            pu.ID                    AS MachinePalletId,
            pu.Numero                AS MachinePalletNumber,
            pu.Type                  AS MachinePalletType,
            pu.PlaqueReceveuse       AS InstalledGabaritNumero,
            pu.Description           AS MachinePalletDescription,
            pu.IsPlaqueActive        AS IsFixtureActive,
            pu.MachinePourPalette    AS MachineForPallet,
            pu.OperationEnCours      AS PalletOperationEnCours,
            pu.machineEnCours        AS PalletMachineEnCours

        FROM Cedule.dbo.Gabarit_PieceGabarit        AS pg
        LEFT JOIN Cedule.dbo.Gabarit_GabaritUsinage AS gu
            ON pg.Gabarit = gu.numero
        LEFT JOIN Cedule.dbo.Gabarit_PlaqueReceveuse AS pr
            ON gu.PlaqueReceveuse_Numro = pr.numeroModel
        LEFT JOIN Cedule.dbo.Gabarit_PaletteUsinage AS pu
            ON pu.PlaqueReceveuse = pg.Gabarit;   -- pallets that currently carry this gabarit

        Then, in your Python “FixtureDataProvider”, you can do things like:
            •	SELECT * FROM Cedule.dbo.Autopilot_FixtureMatrix WHERE PieceCode = @PieceCode
            •	→ see required fixture, its storage location, and whether any pallets already have it.

        ⸻

        6. How this plugs into your Autopilot

        Rough mapping:
            •	MachinePallet provider
            •	Uses Query 1 (or the view behind it).
            •	Fixture inventory provider
            •	Uses Query 2.
            •	PieceFixture provider
            •	Uses Query 3 or Autopilot_FixtureMatrix filtered by PieceCode.
            •	“Ready pallet” quick lookup
            •	Uses Query 4 or the unified view.
            •	Scoring
            •	Uses:
            •	“ready pallet” info → low setup penalty.
            •	fixture quantity & used → detect scarcity.
            •	plaque model matching → compatibility.



⸻

D. Material & WIP locations
    ** not available for now, will be wired the API later *** 
D.1 Material pallet state

For each material pallet:
	•	MaterialPalletId
	•	ContentType: raw / WIP
	•	WorkOrder, PartId (or material code)
	•	QuantityAvailable
	•	Location: storage area, operator area, buffer, etc.

D.2 WIP outside pallets (if applicable)
    ** not available for now, will be wired the API later *** 
Any WIP parts not on material pallets:
	•	WorkOrder, PartId, OperationId
	•	QuantityAvailable
	•	Location: shelf, cart, etc.




F. Crane & logistics data
    ** not available for now, will be wired the API later *** 
F.1 Crane moves & load station events (from Fastems Oracle)
	•	Logs of:
	•	PalletId
	•	FromLocation, ToLocation
	•	StartTime, EndTime
	•	Loading station:
	•	IN/OUT events for machine pallets & material pallets.
	•	Enough to:
	•	derive average crane move time per pallet/location type,
	•	detect start/end of operator setup sessions (via your external scheduler).

Used to:
	•	Estimate MaterialPenalty (more moves = more time).
	•	Feed SetupSession timing when tied to loading station events.

⸻

G. Work calendar & shifts

G.1 Shift & working hours
	•	Shift schedule:
	•	Start/end times for each shift (morning, day, night).
	•	Days of week in operation.
	•	Night unattended window:
	•	Start / end when no loading/unloading occurs.

Used to:
	•	Configure AutopilotShiftWindow rows:
	•	MorningRestart window
	•	Normal day window
	•	NightPrep window
** for now use a fixed schedule 
monday to friday 
shift 1 : 6h00 to 16h00 
shift 2 : 16h00 to 24h00 


⸻

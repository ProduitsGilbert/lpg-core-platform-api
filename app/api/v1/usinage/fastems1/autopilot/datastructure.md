Nice, so we’ve moved from “let’s invent tables” to “tables are live in production, don’t mess them up”. Good. That means the PRD now needs to describe structure and meaning, not SQL.

Here’s a cleaned-up PRD section focused on how the data is structured and what values exist / are expected in each fastems1.Autopilot.* table.

⸻

1. High-level data model

The Autopilot layer sits on top of:
	•	Existing Fastems / CNC / Oracle data:
	•	Parts, operations, work orders, tools, fixtures, pallets, crane moves, loading-station in/out, etc.
	•	New fastems1.Autopilot.* tables:
	•	These are log & planning tables only; they never replace source-of-truth production data.

Conceptually, a job is identified by:
	•	WorkOrder + PartId + OperationId
(you can also tie to a specific MachinePalletId when relevant).

The Autopilot tables are grouped by responsibility:
	•	Decisions & schedule:
	•	fastems1.AutopilotDecision
	•	fastems1.AutopilotPlannedJob
	•	Telemetry / analytics:
	•	fastems1.AutopilotSetupSession
	•	fastems1.AutopilotToolUsageEvent
	•	fastems1.AutopilotPalletUsageDaily
	•	Behavior control:
	•	fastems1.AutopilotShiftWindow
	•	fastems1.AutopilotJobIgnore
	•	fastems1.AutopilotMachineStatus

Below: each table, what each column means, and which values are expected.

⸻

2. Table by table

2.1 fastems1.AutopilotDecision

What it is:
One row per Autopilot suggestion. This is the “black box recorder” for each decision the system makes.

Key fields:
	•	DecisionId
	•	Identity, primary key.
	•	TsUtc
	•	UTC timestamp when the suggestion was generated.
	•	MachineId
	•	Target machine for this job: e.g. "DMC1", "DMC2", "DMC3", "DMC4".
	•	WorkOrder
	•	Work-order identifier associated with the job (string).
	•	PartId, OperationId
	•	Database IDs for the part and operation being suggested.
	•	SuggestedMachinePalletId, SuggestedMaterialPalletId
	•	Chosen machine pallet and material pallet to use for this job.
	•	EstimatedSetupMinutes
	•	Planner’s estimate of total setup time for this job (fixture + part fitting).
	•	EstimatedCycleMinutes
	•	Estimate of machine cutting time for this operation.
	•	ScoreTotal
	•	Final score used to rank candidates (lower or higher is better depending on implementation, but consistent).
	•	ScoreToolPenalty, ScoreSetupPenalty, ScoreMaterialPenalty, ScoreBalancePenalty
	•	Components of the score:
	•	ToolPenalty: cost of needed tool changes.
	•	SetupPenalty: fixture and part-fitting effort.
	•	MaterialPenalty: crane/handling overhead.
	•	BalancePenalty: load-balancing/fairness cost across machines.
	•	ShiftWindowId
	•	Foreign key (logical) to AutopilotShiftWindow row used for scoring (e.g. MorningRestart vs NightPrep).
	•	PayloadJson
	•	JSON document containing the full suggestion details, including:
	•	Action plan (steps like UNLOAD_PART, MOUNT_FIXTURE, LOAD_RAW_MATERIAL).
	•	Detailed fixture mapping (e.g. “unload fixture 24B, load 44C”).
	•	Hardware list and locations.
	•	Any additional debug/trace info.

⸻

2.2 fastems1.AutopilotPlannedJob

What it is:
Short-horizon schedule of intended jobs for each machine. The scheduler periodically generates a new plan batch.

Key fields:
	•	PlannedJobId
	•	Identity, primary key.
	•	PlanBatchId
	•	ID representing one full planning run.
	•	A new planning run = new PlanBatchId, with a set of rows inserted.
	•	TsPlannedUtc
	•	When this plan entry was created.
	•	MachineId
	•	Target machine: DMC1–DMC4.
	•	SequenceIndex
	•	The order in which this machine is supposed to run these jobs (1, 2, 3, …).
	•	WorkOrder, PartId, OperationId
	•	Identify the job (see “job key” above).
	•	MachinePalletId, MaterialPalletId
	•	Pallet assignments for this job.
	•	EstimatedSetupMinutes, EstimatedCycleMinutes
	•	Planner’s estimates at planning time (may differ from AutopilotDecision if re-evaluated later).
	•	PlannedStartUtc, PlannedEndUtc
	•	Optional timing estimate for when the job is expected to run, if the scheduler computes absolute times.
	•	Status
	•	Allowed values:
	•	"planned": created by planner, not yet used.
	•	"dispatched": used to generate a Decision (sent to operator/production).
	•	"done": job completed successfully.
	•	"skipped": plan entry was skipped (e.g. operator refused or constraints changed).
	•	"cancelled": job removed due to changes (e.g. machine down, material shortage).
	•	DecisionId
	•	When the plan entry becomes a real suggestion, this links to the AutopilotDecision row created.

How it’s used:
	•	Your external scheduling service calls an endpoint to refresh this table periodically.
	•	/autopilot/next uses the current batch to choose the best candidate across all machines.

⸻

2.3 fastems1.AutopilotShiftWindow

What it is:
Defines behavior profiles depending on time of day (e.g. morning restart vs night prep).

Key fields:
	•	ShiftWindowId
	•	Identity, primary key.
	•	Name
	•	Human-readable name: e.g. "MorningRestart", "Day", "EveningNightPrep".
	•	StartTime, EndTime
	•	Local time-of-day bounds when this window is active.
	•	The algorithm picks the row whose time range covers “now”.
	•	Mode
	•	Allowed values:
	•	"restart" – morning logic: prioritize short setups and quick parts to restart machines.
	•	"normal" – balanced logic during the day.
	•	"night_prep" – end-of-shift logic: accept longer setups to run long programs overnight.
	•	Weight fields:
	•	WeightShortSetup
	•	How strongly we penalize setup time in this window.
	•	WeightLongRun
	•	How strongly we reward longer cycle times (especially for night prep).
	•	WeightToolPenalty
	•	How strongly we penalize tool changes.
	•	WeightMaterialPenalty
	•	How strongly we penalize material handling / crane overhead.
	•	WeightMachineBalance
	•	How strongly we penalize overloading a single machine.
	•	MaxShortJobsPerMachine
	•	Optional limit on how many “short jobs” should be run per machine in this window (for example: 2 quick jobs per machine during restart before allowing long setups).

How it’s used:
	•	The planner looks up the active window and uses these weights in the score calculation.
	•	Different windows = different behavior without code changes (only DB config).

⸻

2.4 fastems1.AutopilotJobIgnore

What it is:
Stores jobs that should be temporarily avoided, mainly because the operator refused a suggestion.

Key fields:
	•	IgnoreId
	•	Identity, primary key.
	•	TsUtc
	•	When ignore was recorded.
	•	WorkOrder, PartId, OperationId, MachinePalletId
	•	Identifies the job that should be ignored.
	•	MachinePalletId can be NULL if we want to ignore all pallets for that WO/part/op.
	•	IgnoreUntilUtc
	•	Job must not be suggested again until this time (typically now + 1 day).
	•	Reason
	•	Free text: e.g. "Fixture 24B currently dedicated to another family".
	•	DecisionId
	•	Which decision was refused.

How it’s used:
	•	When generating candidates or reading AutopilotPlannedJob, planner skips jobs that match an active ignore (now < IgnoreUntilUtc).

⸻

2.5 fastems1.AutopilotMachineStatus

What it is:
Manual / external availability state for each machine (DMC1–4).

Key fields:
	•	MachineId
	•	Primary key: DMC1, DMC2, DMC3, DMC4.
	•	IsAvailable
	•	1 = can be used by Autopilot.
	•	0 = must not be scheduled (down/maintenance).
	•	Status
	•	Suggested values:
	•	"available"
	•	"down"
	•	"maintenance"
	•	"unknown"
	•	This is more descriptive than the bare boolean.
	•	Reason
	•	Text reason if the machine is not available (e.g. "Spindle vibration").
	•	TsUpdatedUtc
	•	When this status was last changed.

How it’s used:
	•	Planner and schedule refresh exclude machines where IsAvailable = 0 or Status <> 'available'.

⸻

2.6 fastems1.AutopilotSetupSession

What it is:
Logs fixture/part setup sessions for machine pallets (how long they really take).

Key fields:
	•	SetupId
	•	Identity, primary key.
	•	TsStartUtc, TsEndUtc
	•	Start and end timestamps in UTC.
	•	In your design, these are triggered by your scheduler watching Oracle loading-station IN/OUT.
	•	MachineId, MachinePalletId
	•	Where the setup occurred.
	•	WorkOrder, PartId, OperationId
	•	Job context (if known at setup time).
	•	SetupType
	•	Suggested values:
	•	"fixture_change" – mostly fixture swap.
	•	"part_fitting" – mostly loading new parts on existing fixture.
	•	"mixed" – combination.
	•	"auto_detected" – if the system is inferring it from context.
	•	EstimatedSetupMinutes
	•	Estimate from the decision at suggestion time (for comparison).
	•	OperatorName
	•	Operator performing the setup, or a pseudo-user like "AUTO_ORACLE" if fully automated.
	•	DecisionId
	•	Which decision led to this setup.

How it’s used:
	•	To compute real fixture-change and part-fitting times.
	•	To tune scoring weights (SetupPenalty) and to justify fixture investments.

⸻

2.7 fastems1.AutopilotToolUsageEvent

What it is:
Granular log of tool-related events associated with jobs and decisions.

Key fields:
	•	ToolEventId
	•	Identity, primary key.
	•	TsUtc
	•	When the event was recorded.
	•	MachineId
	•	Machine concerned.
	•	ToolId
	•	Identifier of the tool (from your tool inventory).
	•	EventType
	•	Suggested values:
	•	"required" – job requires this tool.
	•	"present" – tool was already loaded in machine.
	•	"missing" – tool is not available / not in inventory.
	•	"loaded" – tool was loaded into the machine.
	•	"unloaded" – tool was removed.
	•	"used" – tool was actually used in machining (if we can detect).
	•	WorkOrder, PartId, OperationId
	•	Job context.
	•	DecisionId
	•	Which decision this event is attached to.

How it’s used:
	•	Data to find:
	•	often missing tools,
	•	tools required but never used,
	•	useless tool load/unload cycles.
	•	Feeds into the tool penalty model (ScoreToolPenalty).

⸻

2.8 fastems1.AutopilotPalletUsageDaily

What it is:
Daily usage summary for each machine pallet.

Key fields:
	•	UsageDate
	•	Date (no time component).
	•	MachinePalletId
	•	Identity of the pallet.
	•	CyclesRun
	•	Number of machining cycles that used this pallet on that date.
	•	TotalCutMinutes
	•	Total time the machine spent cutting with this pallet on that date.
	•	TotalSetupMinutes
	•	Total setup time associated with this pallet on that date.

Primary key: (UsageDate, MachinePalletId).

How it’s used:
	•	To identify:
	•	pallets that are under-used or not used at all,
	•	pallets with very high setup-time-to-cut-time ratios (“bad designs”),
	•	potential candidates for duplication or redesign.

⸻

3. Suggestion payload (conceptual structure)

In addition to the table fields, the suggestion returned by /autopilot/next (and stored in PayloadJson) has a structured action plan with steps like:
	•	Unload instructions
	•	UNLOAD_PART – remove finished part.
	•	UNMOUNT_FIXTURE – remove existing part fixture (e.g. 24B).
	•	Load instructions
	•	MOUNT_FIXTURE – mount new part fixture (e.g. 44C) and specify location to pick it.
	•	LOAD_RAW_MATERIAL – load raw part ABC from a specific material pallet / location.
	•	Hardware list
	•	Items required (jaws, pins, stops) + quantity + storage location.

This is not a table but a JSON structure embedded in PayloadJson (and in the API response), something like:

{
  "action_plan": {
    "steps": [
      { "step_type": "UNLOAD_PART", "description": "Unload finished part from pallet 42" },
      { "step_type": "UNMOUNT_FIXTURE", "part_fixture_code": "24B" },
      { "step_type": "MOUNT_FIXTURE", "part_fixture_code": "44C", "location": "Rack A2, shelf 3" },
      { "step_type": "LOAD_RAW_MATERIAL", "material_pallet_id": 7, "part_number": "ABC-001" }
    ],
    "fixture_hardware_list": [
      { "item": "Jaw type C 125mm", "qty": 2, "location": "Jaws rack row 2" },
      { "item": "Stop pin 16mm", "qty": 2, "location": "Bin SP16" }
    ]
  }
}

The data providers (fixture/location/tool providers) are responsible for mapping these fixture codes and hardware lists from your many source systems into this structure.

⸻

If you want, next step could be a small “data dictionary” doc just for WorkOrder + Part + Operation flows (where each one lives in Oracle vs SQL vs CAM), so your data providers have a clear contract and you don’t end up chasing fields like a squirrel in a tool crib.
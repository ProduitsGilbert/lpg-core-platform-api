# Payload Reference Guide - Tool Shortage API

This guide explains how to compute each field in:

`POST /predict/future-needs`

so inference matches how the model was designed and trained.

## 1) Canonical Rules

- Normalize `tool_id` as `UPPER(TRIM(tool_id))`.
- Use machine center names exactly as expected by your API payload, for example `DMC100`, `NHX5500`.
- Keep units consistent:
  - `*_seconds` in seconds
  - `*_minutes` in minutes
  - `time_since_last_use_hours` in hours
- Compute all windowed features relative to one reference timestamp `t0` (API request build time).

## 2) Primary Data Sources

- Future demand:
  - Preferred (already tool-level): `GET /api/v1/tooling/future-needs?work_center_no=...`
- Usage / task history:
  - `Cedule.dbo.ToolingTasks`
- Inventory and remaining life:
  - `Cedule.dbo.ToolInstanceHistory`

## Source Reconciliation (Important)

- The model expects **tool-level future demand** (`tool_id` + required time).
- `.../tooling/future-needs` already provides this directly and is the safest source for parity with training.
- `.../ProductionOrder/AllUnfinishedProductionOrderRoutingLine(...)` is routing-level demand (operation/work center/job); it may not include tool mapping directly.
- If routing endpoint has no tool mapping, you must enrich with NC program tool definition before building payload.

Recommended pipeline when using routing endpoint:
1. Read unfinished routing lines for target work centers (`DMC100`, `NHX5500`).
2. Resolve routing/operation -> NC program(s).
3. Resolve NC program -> tool list (tool definitions).
4. Allocate `expectedCapacityNeedMin` (or run-time estimate) across required tools.
5. Aggregate by `(machine_center, tool_id)` into:
  - `total_required_use_time_seconds`
  - `rows_count`
  - `program_count`

## 3) Field-by-Field Mapping

## Required Core

| Payload field | Source | How to compute |
|---|---|---|
| `tool_id` | Future-needs / NC definition | Normalized tool identifier. |
| `total_required_use_time_seconds` | `future-needs.tools_summary.total_required_use_time_seconds` | Sum required time for that tool in upcoming production plan. |
| `rows_count` | `future-needs.tools_summary.rows_count` | Number of future-need rows contributing to this tool. |
| `program_count` | `future-needs.tools_summary.program_count` | Number of distinct programs requiring this tool. |

## Inventory / Sister Availability

Use latest snapshot(s) from `ToolInstanceHistory` around `t0`.

| Payload field | Source | How to compute |
|---|---|---|
| `total_remaining_life` | `ToolInstanceHistory.RemainingLifeTime` | Sum of remaining life for this tool (sisters included). |
| `inventory_instances` | `ToolInstanceHistory` | Count of instances for this tool. |
| `available_instances` | `ToolInstanceHistory.Status` | Count where `Status = 1`. |
| `sister_count_total` | `ToolInstanceHistory.SisterId` | Distinct sister count; fallback to instance key when `SisterId` is empty. |
| `sister_count_available` | `ToolInstanceHistory.Status` + sister key | Distinct sister count where `Status = 1`. |
| `sister_count_machine` | `ToolInstanceHistory.CurrentLocation` + `Status` | Number of distinct machines where at least one sister is available. |

## Usage Recency / Frequency

From `ToolingTasks` in recent windows before `t0`.

| Payload field | Source | How to compute |
|---|---|---|
| `time_since_last_use_hours` | `MAX(ToolingTasks.timestamp)` | `(t0 - last_use_timestamp) / 3600`. |
| `uses_last_24h` | `ToolingTasks` | Count of rows for tool in `[t0-24h, t0)`. |
| `uses_last_7d` | `ToolingTasks` | Count of rows for tool in `[t0-7d, t0)`. |

## Wear Features

From daily inventory snapshots (`ToolInstanceHistory`).

| Payload field | Source | How to compute |
|---|---|---|
| `wear_rate_24h` | `RemainingLifeTime` daily totals | `max(0, total_remaining_life_(t0-24h) - total_remaining_life_(t0))`. |
| `wear_rate_7d` | Same | Average of daily wear over last 7 days. |

## Future-Demand Windows

Best: derive from scheduled jobs with due times.  
If not available: approximate from `total_required_use_time_seconds`.

| Payload field | Source | How to compute |
|---|---|---|
| `future_usage_minutes_24h` | Scheduling data OR approximation | Required minutes expected in next 24h. |
| `future_usage_minutes_48h` | Scheduling data OR approximation | Required minutes expected in next 48h. |
| `future_usage_minutes_7d` | Scheduling data OR approximation | Required minutes expected in next 7 days. |

Approximation fallback:

- `future_total_minutes = total_required_use_time_seconds / 60`
- `daily_rate = max(tool_usage_minutes_90d / 90, uses_last_7d / 7, 0)`
- `future_usage_minutes_24h = min(future_total_minutes, daily_rate * 1)`
- `future_usage_minutes_48h = min(future_total_minutes, daily_rate * 2)`
- `future_usage_minutes_7d = min(future_total_minutes, daily_rate * 7)`

## 4) SQL Templates

These queries are templates. Adjust connection/database names as needed.

```sql
-- Latest inventory snapshot per tool (machine scoped)
WITH latest AS (
  SELECT
      ToolId,
      SisterId,
      RemainingLifeTime,
      CurrentLocation,
      Status,
      SnapshotTimestamp,
      ROW_NUMBER() OVER (
        PARTITION BY ToolId, ISNULL(NULLIF(LTRIM(RTRIM(SisterId)), ''), CurrentLocation)
        ORDER BY SnapshotTimestamp DESC
      ) AS rn
  FROM [Cedule].[dbo].[ToolInstanceHistory]
  WHERE CurrentLocation LIKE @machine_center + '%'
)
SELECT
    UPPER(LTRIM(RTRIM(ToolId))) AS tool_id,
    SUM(CAST(RemainingLifeTime AS FLOAT)) AS total_remaining_life,
    COUNT(*) AS inventory_instances,
    SUM(CASE WHEN Status = 1 THEN 1 ELSE 0 END) AS available_instances,
    COUNT(DISTINCT ISNULL(NULLIF(LTRIM(RTRIM(SisterId)), ''), CurrentLocation)) AS sister_count_total,
    COUNT(DISTINCT CASE WHEN Status = 1 THEN ISNULL(NULLIF(LTRIM(RTRIM(SisterId)), ''), CurrentLocation) END) AS sister_count_available,
    COUNT(DISTINCT CASE WHEN Status = 1 THEN LEFT(CurrentLocation, CHARINDEX(':', CurrentLocation + ':') - 1) END) AS sister_count_machine
FROM latest
WHERE rn = 1
GROUP BY UPPER(LTRIM(RTRIM(ToolId)));
```

```sql
-- Usage recency/frequency from ToolingTasks
SELECT
    UPPER(LTRIM(RTRIM(tool_id))) AS tool_id,
    DATEDIFF(hour, MAX([timestamp]), @t0) AS time_since_last_use_hours,
    SUM(CASE WHEN [timestamp] >= DATEADD(hour, -24, @t0) AND [timestamp] < @t0 THEN 1 ELSE 0 END) AS uses_last_24h,
    SUM(CASE WHEN [timestamp] >= DATEADD(day, -7, @t0) AND [timestamp] < @t0 THEN 1 ELSE 0 END) AS uses_last_7d
FROM [Cedule].[dbo].[ToolingTasks]
WHERE cnc_machine LIKE @machine_center + '%'
GROUP BY UPPER(LTRIM(RTRIM(tool_id)));
```

```sql
-- Daily total remaining life for wear calculations
WITH daily AS (
  SELECT
      UPPER(LTRIM(RTRIM(ToolId))) AS tool_id,
      CAST(SnapshotDate AS date) AS d,
      SUM(CAST(RemainingLifeTime AS FLOAT)) AS total_remaining_life
  FROM [Cedule].[dbo].[ToolInstanceHistory]
  WHERE CurrentLocation LIKE @machine_center + '%'
    AND SnapshotDate >= DATEADD(day, -8, CAST(@t0 AS date))
    AND SnapshotDate <= CAST(@t0 AS date)
  GROUP BY UPPER(LTRIM(RTRIM(ToolId))), CAST(SnapshotDate AS date)
)
SELECT
    d0.tool_id,
    CASE WHEN d1.total_remaining_life - d0.total_remaining_life > 0
         THEN d1.total_remaining_life - d0.total_remaining_life
         ELSE 0 END AS wear_rate_24h
FROM daily d0
LEFT JOIN daily d1
  ON d1.tool_id = d0.tool_id
 AND d1.d = DATEADD(day, -1, d0.d)
WHERE d0.d = CAST(@t0 AS date);
```

## 5) Build Order Recommendation

1. Build base rows from future-needs (`tool_id`, `total_required_use_time_seconds`, `rows_count`, `program_count`).
2. Left join inventory/sister aggregates.
3. Left join usage recency/frequency aggregates.
4. Left join wear aggregates.
5. Compute future-demand window fields.
6. Fill missing numeric fields with `0` only when source truly unavailable.

## 6) Validation Checklist Before Calling API

- No duplicate `(machine_center, tool_id)` rows in one request.
- `total_required_use_time_seconds >= 0`
- `total_remaining_life >= 0` and `available_instances <= inventory_instances`
- `future_usage_minutes_24h <= future_usage_minutes_48h <= future_usage_minutes_7d` when manually supplied.
- All IDs normalized (uppercase, trimmed).

## 7) Notes About Missing Data

- If optional features are omitted, the standalone predictor falls back to exported profile defaults.
- Prediction still works, but quality is better when real-time inventory and recent usage are provided.

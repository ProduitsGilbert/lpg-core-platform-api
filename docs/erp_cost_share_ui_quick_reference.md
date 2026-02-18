# ERP Cost Share Snapshot UI Quick Reference

## Scope
Use this guide to build UI screens for production costing snapshots stored in Cedule tables:

- `[Cedule].[dbo].[30_COMPTABILITÉ ET FINANCES_COST_SHARE_SCANS]`
- `[Cedule].[dbo].[30_COMPTABILITÉ ET FINANCES_COST_SHARE_STATE]`
- `[Cedule].[dbo].[30_COMPTABILITÉ ET FINANCES_COST_SHARE_SNAPSHOT]`

## Backend endpoints

- Trigger scan
  - `POST /api/v1/erp/production/costing/scans`
  - Body: `{ "full_refresh": true|false }`

- Get grouped snapshots by base item number
  - `GET /api/v1/erp/production/costing/items/{item_no}?latest_only=true|false&include_lines=true|false`
  - Use `latest_only=false` to get all historical versions for diff UI.

## Search textbox behavior (`*{item_no}*`)

Use a forgiving input parser in UI:

1. Read user input (example: `*0115105*`, `0115105`, `0115105-05`).
2. Strip spaces and leading/trailing `*`.
3. If value contains `-`, keep the base item only for query (`0115105-05` -> `0115105`).
4. Call:
   - `GET /api/v1/erp/production/costing/items/0115105?latest_only=false&include_lines=true`

Notes:
- Current API key path is base item number, not free text SQL LIKE.
- Wildcard UX is handled client-side by normalization.

## How to render versions

From response:

- `routing_versions[]`
- `bom_versions[]`

Each entry has:

- `source_no` (ex: `0115105-04`, `0115105-05`)
- `scan_id`
- `scan_started_at`
- `header_last_modified_at`
- `lines[]`

UI recommendation:

1. Keep two tabs: `Routing` and `BOM`.
2. In each tab, group by `source_no`.
3. Inside each `source_no`, order versions by `scan_started_at` ascending.
4. Show timeline cards:
   - `source_no`
   - `scan_started_at`
   - `header_last_modified_at`
   - `line_count`

## Diff logic (green/red)

Compare two consecutive versions of the same `source_type + source_no`.

### Normalize each line

Build a stable key per line:

- Prefer `line_key` if present in payload metadata.
- Fallback key: JSON string of a normalized object with sorted keys.

### Compute sets

- `old_map[key] = line`
- `new_map[key] = line`

Then:

- Added: keys in `new_map` not in `old_map` -> **green**
- Removed: keys in `old_map` not in `new_map` -> **red**
- Common keys:
  - If serialized normalized line differs -> **modified** (show field-level delta)
  - Else unchanged (optional collapsed)

### Suggested colors

- Added: background `#e8f7e9`, text `#1f7a1f`
- Removed: background `#fdeaea`, text `#a12626`
- Modified: background `#fff7e6`, text `#8a5a00`

## Minimal client flow

1. User searches `*0115105*`.
2. UI normalizes to `0115105`.
3. Fetch with `latest_only=false&include_lines=true`.
4. Build version timeline for Routing and BOM.
5. On selecting version `N`, auto-compare to `N-1` and render diff.

## Optional improvements

- Add a toggle `Show only changed lines`.
- Add export button for diff JSON per version pair.
- Cache last query result in client state for quick tab switching.

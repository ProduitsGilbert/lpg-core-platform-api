# Carrier Statement UI Quick Guide

This guide is for building a single page that:
1. uploads a carrier statement PDF,
2. calls extraction,
3. saves extracted rows to DB,
4. shows current rows in a table,
5. marks a row as matched.

Base API prefix:
- `/api/v1/ocr/documents`

## Endpoints you need

1. Extract statement from uploaded PDF
- `POST /carrier-statements/extract`
- `multipart/form-data`
- fields:
  - `file` (required, PDF)
  - `carrier` (required, use `purolator`)
  - `max_pages` (optional, integer)

2. Save extracted shipments to DB
- `POST /carrier-statements/records`
- JSON body:
  - `carrier`
  - `workflow_type` (fallback only)
  - `status`
  - `matched`
  - `statement_filename`
  - `extracted_data` (output of extract endpoint)

3. List saved rows for table
- `GET /carrier-statements/records?carrier=purolator&limit=100&offset=0`
- Optional filters:
  - `status`
  - `matched`
  - `workflow_type`

4. Update one row (mark matched, change status)
- `PATCH /carrier-statements/records/{record_id}`
- JSON body supports:
  - `matched`
  - `status`
  - `workflow_type`
  - `sales_invoice_number` (example: `INV036928`)
  - `sales_transport_charge_line_amount` (transport charge line amount)
  - `sales_total_amount_incl_vat` (sales order total incl. VAT)

## Important response shapes

- Extract and Save and Patch return wrapped payload:
  - `{ "data": ..., "meta": ... }`
- List returns direct payload:
  - `{ "total": number, "items": [...] }`

## Workflow inference behavior (already in backend)

On save, workflow is inferred per shipment:
- `purchase` when `shipped_to_address` is Gilbert HQ (Les Produits Gilbert, 1840 Marcotte, Roberval, G8H 2P2).
- `sales` when `shipped_from_address` is Gilbert HQ and `ref_1`/`ref_2` contains sales-order style refs (`GI20877`, `GI21960`, `R1234`, etc.).
- provided `workflow_type` is used as fallback only.

## Frontend page state (recommended)

Use these states:
- `file: File | null`
- `extracting: boolean`
- `saving: boolean`
- `loadingRows: boolean`
- `extractionResult: CarrierExtractData | null`
- `rows: CarrierRow[]`
- `error: string | null`

## Minimal React + TypeScript example

```tsx
import React, { useEffect, useState } from "react";

type CarrierExtractData = {
  carrier: string;
  processed_pages: number;
  shipments: Array<{
    tracking_number: string;
    shipment_date: string;
    shipped_from_address: string;
    shipped_to_address: string;
    ref_1?: string | null;
    ref_2?: string | null;
    total_charges: string;
    workflow_type?: "purchase" | "sales";
  }>;
  [k: string]: unknown;
};

type CarrierRow = {
  id: number;
  tracking_number: string;
  shipment_date: string;
  status: string;
  matched: boolean;
  workflow_type: "purchase" | "sales";
  total_charges: string;
  ref_1?: string | null;
  ref_2?: string | null;
};

const API = "/api/v1/ocr/documents";

export default function CarrierStatementPage() {
  const [file, setFile] = useState<File | null>(null);
  const [extracting, setExtracting] = useState(false);
  const [saving, setSaving] = useState(false);
  const [loadingRows, setLoadingRows] = useState(false);
  const [extractionResult, setExtractionResult] = useState<CarrierExtractData | null>(null);
  const [rows, setRows] = useState<CarrierRow[]>([]);
  const [error, setError] = useState<string | null>(null);

  async function fetchRows() {
    setLoadingRows(true);
    setError(null);
    try {
      const res = await fetch(`${API}/carrier-statements/records?carrier=purolator&limit=100&offset=0`);
      const data = await res.json();
      if (!res.ok) throw new Error(data?.detail || "Failed to load rows");
      setRows(data.items || []);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setLoadingRows(false);
    }
  }

  useEffect(() => {
    fetchRows();
  }, []);

  async function extractFile() {
    if (!file) return;
    setExtracting(true);
    setError(null);
    try {
      const form = new FormData();
      form.append("file", file);
      form.append("carrier", "purolator");
      // Optional page cap for testing only:
      // form.append("max_pages", "10");

      const res = await fetch(`${API}/carrier-statements/extract`, {
        method: "POST",
        body: form,
      });
      const json = await res.json();
      const payload = json?.data;
      if (!res.ok || !payload?.success) {
        throw new Error(payload?.error_message || json?.detail || "Extraction failed");
      }
      setExtractionResult(payload.extracted_data as CarrierExtractData);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setExtracting(false);
    }
  }

  async function saveExtraction() {
    if (!extractionResult || !file) return;
    setSaving(true);
    setError(null);
    try {
      const body = {
        carrier: "purolator",
        workflow_type: "sales", // fallback only; backend infers per row
        status: "new",
        matched: false,
        statement_filename: file.name,
        extracted_data: extractionResult,
      };

      const res = await fetch(`${API}/carrier-statements/records`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const json = await res.json();
      if (!res.ok) throw new Error(json?.detail || "Save failed");

      await fetchRows();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setSaving(false);
    }
  }

  async function markMatched(row: CarrierRow) {
    setError(null);
    try {
      const res = await fetch(`${API}/carrier-statements/records/${row.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ matched: true, status: "matched", workflow_type: row.workflow_type }),
      });
      const json = await res.json();
      if (!res.ok) throw new Error(json?.detail || "Patch failed");
      await fetchRows();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error");
    }
  }

  return (
    <div style={{ padding: 16 }}>
      <h2>Carrier Statement (Purolator)</h2>

      <div style={{ marginBottom: 12 }}>
        <input
          type="file"
          accept="application/pdf"
          onChange={(e) => setFile(e.target.files?.[0] || null)}
        />
        <button onClick={extractFile} disabled={!file || extracting}>
          {extracting ? "Extracting..." : "Extract"}
        </button>
        <button onClick={saveExtraction} disabled={!extractionResult || saving}>
          {saving ? "Saving..." : "Save to DB"}
        </button>
      </div>

      {extractionResult && (
        <div style={{ marginBottom: 12 }}>
          Extracted pages: {extractionResult.processed_pages}, shipments: {extractionResult.shipments?.length || 0}
        </div>
      )}

      {error && <div style={{ color: "crimson", marginBottom: 12 }}>{error}</div>}

      <h3>Current Records {loadingRows ? "(loading...)" : ""}</h3>
      <table width="100%" cellPadding={8} style={{ borderCollapse: "collapse" }}>
        <thead>
          <tr>
            <th align="left">Tracking</th>
            <th align="left">Date</th>
            <th align="left">Workflow</th>
            <th align="left">Status</th>
            <th align="left">Matched</th>
            <th align="left">Total</th>
            <th align="left">Ref 1</th>
            <th align="left">Ref 2</th>
            <th align="left">Action</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.id}>
              <td>{row.tracking_number}</td>
              <td>{row.shipment_date}</td>
              <td>{row.workflow_type}</td>
              <td>{row.status}</td>
              <td>{String(row.matched)}</td>
              <td>{row.total_charges}</td>
              <td>{row.ref_1 || ""}</td>
              <td>{row.ref_2 || ""}</td>
              <td>
                <button disabled={row.matched} onClick={() => markMatched(row)}>
                  Mark matched
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
```

## Suggested UX sequence

1. User selects PDF.
2. Click `Extract` and show spinner.
3. Show extracted count summary.
4. Click `Save to DB`.
5. Refresh table immediately after save.
6. On reconciliation, click `Mark matched` per row.

## Quick acceptance checklist

- Upload + extract returns `200` and shipment count > 0.
- Save returns `200` and table refreshes.
- Table row shows inferred `workflow_type` (`sales`/`purchase`).
- Mark matched updates `matched=true` and `status=matched` in table.

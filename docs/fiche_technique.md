# Fiche Technique Extraction Implementation Guide

This document describes how to implement a fiche technique reader using
`fillpdfs`, based on the current “creation” flow in this repo. The goal is to
fetch any fiche technique from the system, extract its content, and return it
as JSON.

## Overview

The pipeline should:

1. Fetch a fiche technique PDF by part number.
2. Extract fillable form fields using `fillpdfs.get_form_fields()` (primary).
3. Fall back to text extraction when no form fields exist.
4. Normalize and clean extracted values.
5. Return a JSON object containing extracted fields plus metadata if needed.

## Reference Locations in This Repo

Primary logic and patterns:

- `app/processors/creation.py`
  - `_process_purchased_part()`
  - `_fetch_technical_sheet()`
  - `_process_technical_sheet_pdf()`
  - `_parse_technical_sheet_text()`
  - `_get_field_value()`
  - `_extract_price_from_fields()`
- `app/services/fileshare_api.py`
  - `fetch_item_pdf()`

## Detailed Implementation Steps

### 1. Fetch the fiche technique PDF

**Goal:** Retrieve PDF bytes for a given `part_number`.

Implement a fetcher like:

- `fetch_technical_sheet(part_number: str) -> bytes | None`

Expected behavior:

- Call your storage/API using the part number.
- Return PDF bytes (`bytes`) on success.
- Return `None` on failure.
- Include any required auth headers (e.g. `RequesterUserID`).

### 2. Save PDF bytes to a temporary file

`fillpdfs` expects a file path, so:

- Create a temp file.
- Write PDF bytes to disk.
- Pass the temp file path to `fillpdfs.get_form_fields()`.

### 3. Extract form fields using `fillpdfs` (primary path)

Call:

- `fillpdfs.get_form_fields(tmp_path)`

If this returns a non-empty dict:

- Treat it as the source of truth.
- Normalize and return a cleaned dictionary.

Use a helper to map multiple possible field names into canonical keys:

- `_get_field_value(form_data, field_names, default="")`

### 4. Fallback to text extraction (when no fields exist)

If `form_fields` is empty or `None`:

1. Extract raw text from the PDF (`PyPDF2` or `PyMuPDF`).
2. Parse key/value pairs using:
   - Regex for known fields.
   - A generic colon-separated key/value parser.

Reference behavior in:

- `_parse_technical_sheet_text(text: str)`

### 5. Normalize and clean values

Key normalization steps:

- Strip whitespace from all string values.
- Normalize prices:
  - Remove currency symbols (`$`, `€`).
  - Handle comma vs dot separators.
  - Return a float, or `0.0` on failure.
- Provide fallback for missing descriptions if needed.

### 6. Return JSON

Return a dict that can be serialized to JSON, e.g.:

```json
{
  "Produit-Fournisseur": "...",
  "Produit-Fabriquant": "...",
  "Prix": "...",
  "Description": "...",
  "Choix": "...",
  "Vendeur": "...",
  "Unite": "...",
  "Quantite": "..."
}
```

Guidelines:

- Do not add mock data.
- Only include fields that were actually found.
- If you emit JSON for display, use `ensure_ascii=False`.
- Optionally include a `source` field with the API path or file ID.

## Suggested Module Structure (for another project)

1. `pdf_fetcher.py`
   - `fetch_technical_sheet(part_number) -> bytes | None`
2. `pdf_reader.py`
   - `extract_form_fields(pdf_bytes) -> dict | None`
   - `extract_text_fields(pdf_bytes) -> dict | None`
   - `normalize_fields(fields: dict) -> dict`
3. `technical_sheet_service.py`
   - `get_technical_sheet_json(part_number) -> dict | None`

## Error Handling Rules

Follow these patterns:

- If `fillpdfs` is missing, log and return `None`.
- If fetching fails, stop early.
- If both form and text extraction fail, return `None`.
- Only return JSON if at least one meaningful field is present.

## Dependencies

Recommended libraries:

- `fillpdf` for PDF form fields
- `PyPDF2` or `PyMuPDF (fitz)` for text fallback
- Your system’s HTTP client (`aiohttp`, `requests`, etc.)
- `json` for serialization

## Flow Summary

1. `part_number` → fetch PDF bytes
2. Save temp file → `fillpdfs.get_form_fields()`
3. If fields exist → normalize → return JSON
4. Else → extract text → parse → normalize → return JSON
5. If everything fails → return `None`

# PRD — Centralized Vendor Quote Request API

## 1) Goal
Provide a single FastAPI endpoint that sends vendor quote requests through Front, automatically:
- Resolves vendor email from Business Central
- Determines vendor language
- Translates subject/body if needed
- Renders an optional table from a dataframe
- Attaches optional file(s)
- Appends default signature
- Logs outcome

## 2) Non-Goals
- Building a full UI
- Storing quote request lines in a separate table (unless already required)
- Handling inbound vendor replies

## 3) Primary Use Cases
1. Automation scripts send a quote request by vendor ID with subject/body and optional attachments.
2. Automation scripts include a dataframe to embed a table in the email.
3. System auto-translates to vendor language before sending.

## 4) API Design

### 4.1 Endpoint
`POST /api/v1/quotes/send`

### 4.2 Request Payload
**JSON + multipart (preferred)** for file support.

**Multipart Form Fields**
- `vendor_id` (string, required)
- `subject` (string, required)
- `body` (string, required; HTML or markdown)
- `language_override` (string, optional; e.g., `fr`, `en`)
- `table_json` (string, optional)
  - JSON serialized array of objects (rows) or pandas `to_json(orient="records")`
- `table_format` (string, optional, default: `html`)
  - `html` | `markdown`
- `attach` (file, optional; single file)
- `attachments` (file list, optional; multiple files)
- `dry_run` (bool, optional; default `false`)

**Example (multipart)**
- vendor_id: `ACILE01`
- subject: `Soumission items pour ACILE01`
- body: `<p>Bonjour, ...</p>`
- table_json: `[{"Item":"123","Description":"X","UOM":"UN"}]`
- attach: `plan_123.pdf`

### 4.3 Response Payload
```json
{
  "status": "sent",
  "vendor_id": "ACILE01",
  "vendor_email": "nlemay@russelmetals.com",
  "language": "en",
  "subject_final": "Quote request for items",
  "body_final_preview": "<p>Dear ...</p>",
  "attachments_sent": ["plan_123.pdf"],
  "front_message_id": "msg_...",
  "dry_run": false
}
```

### 4.4 Error Responses
- `400` invalid payload
- `404` vendor not found in BC
- `409` missing vendor email
- `422` invalid `table_json`
- `500` unexpected service error

## 5) Business Rules

1. **Vendor email lookup**
   - Use BC vendor ID (No) to get email.
   - If not found → error `409`.

2. **Vendor language selection**
   - Retrieve BC language code (e.g., `FRA`, `ENG`).
   - If `language_override` provided, it takes precedence.

3. **Translation logic**
   - If vendor language is not French, translate subject/body into English (or vendor language if supported).
   - Only translate plain text and non-HTML strings.
   - If body is HTML/markdown, preserve structure; translate text content only.

4. **Table rendering**
   - `table_json` converts to HTML table or markdown table.
   - Append table after body with a line break.
   - If `table_json` is empty, ignore.

5. **Attachments**
   - Single or multiple files accepted.
   - Optional.
   - If file is included, use Front multipart send.

6. **Signature**
   - Signature appended by default via Front API or by templating in service.

7. **Dry run**
   - When `dry_run=true`, do not send, but return rendered subject/body and resolved email.

## 6) Workflow
1. Validate request
2. Fetch vendor email and language from BC
3. Determine target language (override or BC)
4. Translate subject/body if needed
5. Build table (if provided) and append to body
6. Append signature
7. Send via Front API (multipart if attachments)
8. Return response with metadata

## 7) Logging & Observability
- Log request ID, vendor_id, language, and send status.
- Log translation success/failure.
- Log Front API response (id, status).
- On failure, include correlation_id.

## 8) Security
- Require API key or OAuth.
- Validate file size and type.
- Sanitize/escape table content to avoid HTML injection.

## 9) Acceptance Criteria
- Request with vendor_id, subject, body sends email to the correct vendor address.
- Vendor language is fetched and applied to translation.
- Table renders properly in email.
- Attachments are sent when provided.
- Signature is appended.
- Dry run returns the final rendered content without sending.

## 10) Open Questions
- Supported languages beyond French/English?
- Exact translation service in the target repo?
- Desired limits on file size and table rows?

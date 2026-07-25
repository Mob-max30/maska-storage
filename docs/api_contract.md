# MaskaStorage — Backend API Contract

**Owner:** Pannaga (Backend Engineer)
**Last Updated:** 2026-07-23
**Status:** Stable — frontend may build against these shapes.

---

## Architecture Boundary Reminder

> These endpoints are the **only** way the frontend communicates with the backend.

| Layer | Responsibility | Must never |
|---|---|---|
| **Frontend** | Display info, collect input, call these APIs, render responses | Generate embeddings, parse PDFs, query databases directly |
| **Routes (`backend/app/api`)** | Receive HTTP requests, validate input via Pydantic schemas, delegate to the service layer | Contain business logic or call the database directly |
| **Services (`backend/app/services`)** | Coordinate the database, AI pipeline, and retrieval pipeline | Be bypassed — nothing talks to AI/retrieval/DB except through here |
| **Database (`backend/app/database`)** | Persist resource metadata to SQLite via CRUD helpers | Be called from routes or the frontend |

---

## Base URL

```
http://localhost:8000        # local development (uvicorn app.main:app --reload)
https://api.maskastorage.com # production (placeholder — not yet deployed)
```

All responses are `application/json` unless noted otherwise. File uploads use `multipart/form-data`.

Interactive docs (Swagger UI): `http://localhost:8000/docs`

---

## Common Enums

These string values are used across multiple endpoints. The backend enforces them via Pydantic — invalid values return 422.

### `source_type`

| Value | Meaning |
|---|---|
| `"url"` | Resource was ingested from a public HTTP/HTTPS URL |
| `"pdf"` | Resource was ingested from an uploaded PDF file |

### `status` (resource lifecycle)

| Value | Meaning | Terminal? |
|---|---|---|
| `"pending"` | Record created, pipeline not yet started | No |
| `"processing"` | Pipeline actively running (extraction → embedding → summarization) | No |
| `"ready"` | All pipeline stages complete; resource is queryable via chat | **Yes** |
| `"failed"` | Pipeline encountered an unrecoverable error | **Yes** |

> Stop polling `GET /archive/{resource_id}` when status is `"ready"` or `"failed"`.

---

## Consistent Error Response Shape

Every error — validation failures, not-found, unsupported type, server errors — returns the same envelope regardless of which endpoint failed:

```json
{
  "error": {
    "code": "string",
    "message": "string",
    "details": {} or null
  }
}
```

| Field | Type | Description |
|---|---|---|
| `code` | `string` | Machine-readable error identifier. See catalogue below. |
| `message` | `string` | Human-readable explanation, safe to display in the UI. |
| `details` | `object or null` | Optional structured context — field names, received values, etc. `null` when there is no extra information. |

### Error code catalogue

| `code` | Typical HTTP status | When it appears |
|---|---|---|
| `"validation_error"` | 400 or 422 | Input failed schema or business-level validation |
| `"not_found"` | 404 | Requested resource does not exist |
| `"unsupported_type"` | 415 | Uploaded file MIME type is not accepted |
| `"invalid_url"` | 400 | URL supplied by user cannot be reached or is unsuitable for extraction |
| `"pdf_parsing_error"` | 500 | PDF file could not be parsed (corrupt, password-protected) |
| `"text_extraction_error"` | 500 | No usable text could be extracted from the source |
| `"embedding_error"` | 500 | Embedding model failed to generate a vector |
| `"pipeline_error"` | 500 | General AI pipeline failure not covered by a more specific code |
| `"service_error"` | 500 | Service-layer failure (DB write error, etc.) |
| `"internal_error"` | 500 | Unexpected server error (never leaks stack traces) |
| `"http_error"` | varies | Starlette/FastAPI built-in errors (e.g. 405 Method Not Allowed) |

### Standard HTTP status codes

| Status | Meaning |
|---|---|
| `200` | Success |
| `202` | Accepted (async processing started — resource is not yet ready) |
| `400` | Bad request / business-level validation failure |
| `404` | Resource not found |
| `415` | Unsupported media type |
| `422` | Pydantic schema validation failure (malformed body or bad query params) |
| `500` | Server error |

### Common error examples

**404 — Resource not found:**
```json
{
  "error": {
    "code": "not_found",
    "message": "No resource found with id 'res_7610be09199042a7ab3d74980095458a'.",
    "details": {
      "resource_id": "res_7610be09199042a7ab3d74980095458a"
    }
  }
}
```

**422 — Pydantic validation failure (e.g. empty question):**
```json
{
  "error": {
    "code": "validation_error",
    "message": "Request validation failed. Check the 'details.errors' list.",
    "details": {
      "errors": [
        {
          "field": "body.question",
          "message": "Value error, 'question' must not be empty or whitespace-only."
        }
      ]
    }
  }
}
```

**415 — Unsupported file type:**
```json
{
  "error": {
    "code": "unsupported_type",
    "message": "Only PDF files are accepted. Received: image/png.",
    "details": {
      "received_mime_type": "image/png"
    }
  }
}
```

**500 — Internal error:**
```json
{
  "error": {
    "code": "internal_error",
    "message": "An unexpected error occurred. Please try again later.",
    "details": null
  }
}
```

---

## Endpoints

---

### 1. `GET /health`

#### Purpose
Lightweight liveness check. Confirms the API process is reachable before making other requests.

#### Request
No body, no parameters.

#### Success Response — `200 OK`

```json
{
  "status": "ok",
  "service": "maska-storage-api",
  "version": "0.1.0"
}
```

| Field | Type | Description |
|---|---|---|
| `status` | `string` | Always `"ok"` when the server is running |
| `service` | `string` | Always `"maska-storage-api"` |
| `version` | `string` | Application version string (semver) |

#### Error Response
This endpoint should never return an error. A non-`200` response means the server itself is down.

#### Frontend Notes
- Call once on app load to gate the UI behind a "backend available" check.
- Do not block the user indefinitely — show a friendly "Service unavailable" state if this fails.

---

### 2. `POST /upload`

#### Purpose
Accepts either a **public URL** or a **PDF file** and creates a resource record immediately. AI processing (extraction → chunking → embedding → summarization) continues asynchronously after the response is returned.

> **Current implementation note:** The resource record is written to SQLite with `status: "processing"` immediately. The AI pipeline integration (Sriganesh) is not yet wired — status will remain `"processing"` until the pipeline is connected. The response shape is final.

#### Request

**Content-Type:** `multipart/form-data`

Send **exactly one** of the two form fields:

| Field | Type | Required | Constraint |
|---|---|---|---|
| `url` | `string` (form field) | One of `url` / `file` | Must be a valid HTTP/HTTPS URL |
| `file` | `file` (binary form field) | One of `url` / `file` | Must have MIME type `application/pdf` |

> **Validation rules (enforced by the backend):**
> - Sending both `url` and `file` → `400 Bad Request`, `code: "validation_error"`
> - Sending neither → `400 Bad Request`, `code: "validation_error"`
> - `url` is not a valid HTTP/HTTPS URL → `400 Bad Request`, `code: "validation_error"`
> - `file` MIME type is not `application/pdf` → `415 Unsupported Media Type`, `code: "unsupported_type"`

##### Example — URL upload
```bash
curl -X POST http://localhost:8000/upload \
  -F "url=https://example.com/article"
```

##### Example — PDF upload
```bash
curl -X POST http://localhost:8000/upload \
  -F "file=@/path/to/document.pdf"
```

#### Success Response — `202 Accepted`

```json
{
  "resource_id": "res_7610be09199042a7ab3d74980095458a",
  "status": "processing",
  "source_type": "url",
  "title": null,
  "summary": null,
  "created_at": "2026-07-21T14:30:00Z"
}
```

| Field | Type | Nullable | Description |
|---|---|---|---|
| `resource_id` | `string` | No | Stable unique identifier. Store this — use it for Archive and Chat calls. Format: `res_<32 hex chars>` |
| `status` | `string` | No | Always `"processing"` at upload time. Poll `GET /archive/{resource_id}` for updates. |
| `source_type` | `string` | No | `"url"` or `"pdf"` |
| `title` | `string or null` | Yes | `null` at upload time for URL uploads. Set to the original filename for PDF uploads (provisional — will be overwritten by AI extraction). |
| `summary` | `string or null` | Yes | Always `null` at upload time. Populated once the AI pipeline completes summarization. |
| `created_at` | `string` (ISO 8601) | No | UTC timestamp of when the resource record was created. |

> **Status lifecycle:** `processing` → `ready` (success) or `failed` (pipeline error).
> Poll `GET /archive/{resource_id}` until status is `"ready"` or `"failed"` (both are terminal).

#### Error Responses

**400 — Both sources provided:**
```json
{
  "error": {
    "code": "validation_error",
    "message": "Provide exactly one of 'url' or 'file', not both.",
    "details": null
  }
}
```

**400 — No source provided:**
```json
{
  "error": {
    "code": "validation_error",
    "message": "Provide exactly one of 'url' or 'file'.",
    "details": null
  }
}
```

**400 — Invalid URL:**
```json
{
  "error": {
    "code": "validation_error",
    "message": "The provided URL is not a valid HTTP/HTTPS URL.",
    "details": {
      "field": "url",
      "value": "not-a-url"
    }
  }
}
```

**415 — Wrong file type:**
```json
{
  "error": {
    "code": "unsupported_type",
    "message": "Only PDF files are accepted. Received: image/png.",
    "details": {
      "received_mime_type": "image/png"
    }
  }
}
```

**500 — Unexpected error:**
```json
{
  "error": {
    "code": "internal_error",
    "message": "An unexpected error occurred. Please try again later.",
    "details": null
  }
}
```

#### Frontend Notes
- Use `multipart/form-data` — do **not** send JSON for this endpoint.
- `202` means "accepted, processing in background" — **not** that the resource is ready to query.
- Store `resource_id` immediately; use it to poll status.
- Do **not** parse PDF content or generate embeddings in the browser — send the raw file.
- Show a processing indicator until `GET /archive/{resource_id}` returns `status: "ready"`.

---

### 3. `GET /archive`

#### Purpose
Returns a paginated list of all ingested resources from SQLite. Supports filtering by status and source type. Used to populate the Archive page.

> **Current implementation note:** Data is read from SQLite. On first startup with an empty database, three seed rows are inserted automatically (one ready URL, one processing PDF, one failed URL) so the frontend always has something to render.

#### Query Parameters

| Parameter | Type | Required | Default | Constraint | Description |
|---|---|---|---|---|---|
| `page` | `integer` | No | `1` | `≥ 1` | Page number (1-indexed) |
| `page_size` | `integer` | No | `20` | `1–100` | Items per page |
| `status` | `string` | No | — | One of the `status` enum values | Filter by resource status |
| `source_type` | `string` | No | — | `"url"` or `"pdf"` | Filter by origin |

> Invalid values for `page` or `page_size` return `422`. Invalid enum values for `status` or `source_type` return `422`.

#### Success Response — `200 OK`

```json
{
  "items": [
    {
      "id": "res_seed_000000000000000001",
      "title": "Example Article Title",
      "source_type": "url",
      "status": "ready",
      "summary": "A concise AI-generated summary of the resource content.",
      "created_at": "2026-07-21T14:30:00Z",
      "updated_at": "2026-07-21T14:32:45Z"
    },
    {
      "id": "res_seed_000000000000000002",
      "title": "Research Paper on Attention Mechanisms.pdf",
      "source_type": "pdf",
      "status": "processing",
      "summary": null,
      "created_at": "2026-07-21T14:35:00Z",
      "updated_at": "2026-07-21T14:35:00Z"
    }
  ],
  "total": 2,
  "page": 1,
  "page_size": 20
}
```

| Field | Type | Nullable | Description |
|---|---|---|---|
| `items` | `array` | No | List of resource summary objects for this page. May be empty. |
| `items[].id` | `string` | No | Unique resource identifier |
| `items[].title` | `string or null` | Yes | Extracted or inferred title. `null` while processing. |
| `items[].source_type` | `string` | No | `"url"` or `"pdf"` |
| `items[].status` | `string` | No | `"pending"`, `"processing"`, `"ready"`, or `"failed"` |
| `items[].summary` | `string or null` | Yes | AI-generated summary; `null` while processing |
| `items[].created_at` | `string` (ISO 8601) | No | UTC creation timestamp |
| `items[].updated_at` | `string` (ISO 8601) | No | UTC last-updated timestamp |
| `total` | `integer` | No | Total matching resources across all pages (for pagination controls) |
| `page` | `integer` | No | Current page number |
| `page_size` | `integer` | No | Items per page used for this response |

#### Error Responses

**422 — Invalid query parameter value:**
```json
{
  "error": {
    "code": "validation_error",
    "message": "Request validation failed. Check the 'details.errors' list.",
    "details": {
      "errors": [
        {
          "field": "query.status",
          "message": "Input should be 'pending', 'processing', 'ready' or 'failed'"
        }
      ]
    }
  }
}
```

**500 — Server error:**
```json
{
  "error": {
    "code": "internal_error",
    "message": "An unexpected error occurred. Please try again later.",
    "details": null
  }
}
```

#### Frontend Notes
- An empty `items` array with `total: 0` is a valid success response — render an empty state, not an error.
- Use `total`, `page`, and `page_size` to build pagination controls.
- The list view does **not** include `source_url` — fetch `GET /archive/{resource_id}` for full detail.

---

### 4. `GET /archive/{resource_id}`

#### Purpose
Fetches the full detail record for a single resource. Use this to poll for status changes after upload, or to show a resource detail view.

#### Path Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `resource_id` | `string` | Yes | The `resource_id` returned by `POST /upload` |

#### Success Response — `200 OK`

```json
{
  "id": "res_7610be09199042a7ab3d74980095458a",
  "title": "Example Article Title",
  "source_type": "url",
  "source_url": "https://example.com/article",
  "filename": null,
  "status": "ready",
  "summary": "A concise AI-generated summary of the resource content.",
  "error_message": null,
  "created_at": "2026-07-21T14:30:00Z",
  "updated_at": "2026-07-21T14:32:45Z",
  "completed_at": "2026-07-21T14:32:45Z"
}
```

**Failed resource example:**
```json
{
  "id": "res_seed_000000000000000003",
  "title": "Private Page (failed)",
  "source_type": "url",
  "source_url": "https://example.com/private-page",
  "filename": null,
  "status": "failed",
  "summary": null,
  "error_message": "Invalid or unreachable URL: the page returned HTTP 403.",
  "created_at": "2026-07-23T08:20:30Z",
  "updated_at": "2026-07-23T08:20:30Z",
  "completed_at": "2026-07-23T08:20:30Z"
}
```

| Field | Type | Nullable | Description |
|---|---|---|---|
| `id` | `string` | No | Unique resource identifier |
| `title` | `string or null` | Yes | Extracted or inferred title. `null` while processing. |
| `source_type` | `string` | No | `"url"` or `"pdf"` |
| `source_url` | `string or null` | Yes | Original URL if `source_type` is `"url"`; `null` for PDF uploads |
| `filename` | `string or null` | Yes | Original PDF filename if `source_type` is `"pdf"`; `null` for URL uploads |
| `status` | `string` | No | `"pending"`, `"processing"`, `"ready"`, or `"failed"` |
| `summary` | `string or null` | Yes | AI-generated summary; `null` while processing or if generation failed |
| `error_message` | `string or null` | Yes | Human-readable failure reason. Non-null **only** when `status == "failed"`. Safe to display in the UI. |
| `created_at` | `string` (ISO 8601) | No | UTC creation timestamp |
| `updated_at` | `string` (ISO 8601) | No | UTC last-updated timestamp |
| `completed_at` | `string or null` (ISO 8601) | Yes | UTC timestamp when the pipeline finished (`"ready"` or `"failed"`). `null` while `"pending"` or `"processing"`. |

> **Note:** `source_url`, `filename`, `error_message`, and `completed_at` are only present in the detail response, not in the list response (`GET /archive`).

#### Error Responses

**404 — Resource not found:**
```json
{
  "error": {
    "code": "not_found",
    "message": "No resource found with id 'res_7610be09199042a7ab3d74980095458a'.",
    "details": {
      "resource_id": "res_7610be09199042a7ab3d74980095458a"
    }
  }
}
```

**500 — Server error:**
```json
{
  "error": {
    "code": "internal_error",
    "message": "An unexpected error occurred. Please try again later.",
    "details": null
  }
}
```

#### Frontend Notes
- Poll this endpoint (e.g. every 3–5 seconds) after `POST /upload` until `status` changes to `"ready"` or `"failed"`.
- Both `"ready"` and `"failed"` are **terminal** — stop polling on either.
- On `"failed"`: read `error_message` and surface it to the user. The resource record still exists and can be deleted.
- On `"ready"`: read `completed_at` for display (e.g. "Processed in X seconds").
- For PDF resources: use `filename` as the display name until `title` is populated by the AI pipeline.

---

### 5. `DELETE /archive/{resource_id}`

#### Purpose
Permanently deletes a resource — its metadata row from SQLite. This is irreversible.

> **Current implementation note:** Only the SQLite metadata row is deleted. ChromaDB vector deletion will be coordinated with Yeshneil's retrieval module in a future phase. The response shape and status codes are final.

#### Path Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `resource_id` | `string` | Yes | The unique identifier of the resource to delete |

#### Request
No body.

#### Success Response — `200 OK`

```json
{
  "deleted": true,
  "resource_id": "res_7610be09199042a7ab3d74980095458a"
}
```

| Field | Type | Description |
|---|---|---|
| `deleted` | `boolean` | Always `true` on a successful deletion |
| `resource_id` | `string` | Echoed back so the frontend can reconcile its local state without a follow-up fetch |

#### Error Responses

**404 — Resource not found:**
```json
{
  "error": {
    "code": "not_found",
    "message": "No resource found with id 'res_7610be09199042a7ab3d74980095458a'.",
    "details": {
      "resource_id": "res_7610be09199042a7ab3d74980095458a"
    }
  }
}
```

**500 — Server error:**
```json
{
  "error": {
    "code": "internal_error",
    "message": "An unexpected error occurred. Please try again later.",
    "details": null
  }
}
```

#### Frontend Notes
- Deletion is **permanent and irreversible** — show a confirmation dialog before calling this endpoint.
- On `200`, remove the resource from the local list immediately using the echoed `resource_id`.
- On `404`, the resource is already gone — treat it as a successful deletion in the UI and update local state accordingly.

---

### 6. `POST /chat`

#### Purpose
Accepts a natural-language question and runs the RAG pipeline: embedding the question, similarity search over stored chunks, building a prompt with top-k context, calling the LLM, and returning the answer with source citations.

> **Current implementation note — MOCK RESPONSES:** The AI pipeline (Sriganesh) and retrieval pipeline (Yeshneil) are **not yet wired**. The service currently returns a hardcoded mock answer and citations so the frontend can build against the final response shape. When the real pipeline is connected, the response shape will not change.

#### Request Body

**Content-Type:** `application/json`

```json
{
  "question": "What are the key takeaways from the uploaded articles about neural networks?",
  "resource_ids": ["res_7610be09199042a7ab3d74980095458a", "res_c7ab43c01a134481905e702e99340910"]
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `question` | `string` | **Yes** | The user's natural-language question. Must be non-empty and non-whitespace-only. |
| `resource_ids` | `array[string] or null` | No | Scope retrieval to specific resources. Pass `null` or omit to search across all `"ready"` resources. If provided, must be a non-empty list. |

> **Validation rules (enforced by Pydantic — returns 422 on failure):**
> - `question` is missing → `422`, field: `body.question`
> - `question` is empty string or whitespace-only → `422`, field: `body.question`
> - `resource_ids` is provided as an empty list `[]` → `422`, field: `body.resource_ids`

#### Success Response — `200 OK`

```json
{
  "answer": "The uploaded articles highlight three key takeaways about neural networks: (1) depth improves representational power, (2) residual connections mitigate vanishing gradients, and (3) attention mechanisms enable long-range dependency modelling.",
  "citations": [
    {
      "resource_id": "res_7610be09199042a7ab3d74980095458a",
      "title": "Example Article Title",
      "snippet": "Residual connections, introduced by He et al. (2016), allow gradients to flow directly through skip connections, effectively solving the vanishing gradient problem in very deep networks."
    },
    {
      "resource_id": "res_c7ab43c01a134481905e702e99340910",
      "title": "Research Paper on Attention Mechanisms.pdf",
      "snippet": "Attention mechanisms compute a weighted sum over all positions in a sequence, enabling the model to capture long-range dependencies that recurrent architectures struggle with."
    }
  ],
  "resource_ids_used": [
    "res_7610be09199042a7ab3d74980095458a",
    "res_c7ab43c01a134481905e702e99340910"
  ]
}
```

| Field | Type | Nullable | Description |
|---|---|---|---|
| `answer` | `string` | No | The LLM-generated answer grounded in retrieved context. Always present — may state "no relevant content found" if retrieval returned no results. |
| `citations` | `array` | No | Ordered list of context snippets used to produce the answer. May be empty `[]` — this is **not** an error. |
| `citations[].resource_id` | `string` | No | ID of the source resource |
| `citations[].title` | `string or null` | Yes | Title of the source resource. `null` if no title was extracted. |
| `citations[].snippet` | `string` | No | The exact chunk of text retrieved from ChromaDB and used as context |
| `resource_ids_used` | `array[string]` | No | IDs of all resources that contributed context. May be a subset of the requested `resource_ids`. May be empty `[]`. |

> **When no relevant context is found:** The service returns `200` with `answer` explaining no relevant content was found, and `citations: []`, `resource_ids_used: []`. This is **not** an error.

#### Error Responses

**422 — Question is empty or whitespace-only:**
```json
{
  "error": {
    "code": "validation_error",
    "message": "Request validation failed. Check the 'details.errors' list.",
    "details": {
      "errors": [
        {
          "field": "body.question",
          "message": "Value error, 'question' must not be empty or whitespace-only."
        }
      ]
    }
  }
}
```

**422 — `resource_ids` is an empty list:**
```json
{
  "error": {
    "code": "validation_error",
    "message": "Request validation failed. Check the 'details.errors' list.",
    "details": {
      "errors": [
        {
          "field": "body.resource_ids",
          "message": "Value error, resource_ids must be a non-empty list when provided. Pass null or omit the field to search all resources."
        }
      ]
    }
  }
}
```

**500 — LLM or retrieval failure:**
```json
{
  "error": {
    "code": "internal_error",
    "message": "An unexpected error occurred. Please try again later.",
    "details": null
  }
}
```

#### Frontend Notes
- `resource_ids` is **optional** — omit the field or pass `null` to search across everything.
- An empty `citations` list is **not an error** — render it as "No sources found."
- Use `resource_ids_used` to highlight which archive cards contributed to the answer — **not** the originally requested `resource_ids`.
- Do **not** embed the question or search ChromaDB directly — send the raw question string.
- **Currently returns mock responses** — do not build real behaviour around specific mock text.

---

## Field Name Reference

All field names follow `snake_case` to match the Pydantic models in `backend/app/schemas`.

| Field | JSON key in response | Notes |
|---|---|---|
| `resource_id` | `resource_id` | Used in `UploadResponse`, `DeleteResourceResponse`, `CitationSnippet` |
| `id` | `id` | Used in `ArchiveItem` and `ArchiveItemDetail` (list and detail views) |
| `source_type` | `source_type` | Enum: `"url"` or `"pdf"` |
| `status` | `status` | Enum: `"pending"`, `"processing"`, `"ready"`, `"failed"` |
| `source_url` | `source_url` | Only in `ArchiveItemDetail` (detail view); `null` for PDF uploads |
| `created_at` | `created_at` | ISO 8601 UTC datetime string |
| `updated_at` | `updated_at` | ISO 8601 UTC datetime string |
| `resource_ids_used` | `resource_ids_used` | `ChatResponse` only; list of strings, may be empty |

> **Note on `id` vs `resource_id`:** Upload and chat responses use `resource_id` as the key. Archive list and detail responses use `id` as the key. Both refer to the same identifier — this is a known inconsistency that will be resolved in a future schema cleanup.

---

## Summary Table

| Method | Path | Purpose | Success Status |
|---|---|---|---|
| `GET` | `/health` | Liveness check | `200` |
| `POST` | `/upload` | Ingest a URL or PDF | `202` |
| `GET` | `/archive` | List all resources (paginated, filterable) | `200` |
| `GET` | `/archive/{resource_id}` | Get a single resource detail | `200` |
| `DELETE` | `/archive/{resource_id}` | Permanently delete a resource | `200` |
| `POST` | `/chat` | Ask a question via RAG (currently mock) | `200` |

> **Authentication:** Out of scope for the current phase. All endpoints are open. This will change in a future phase — only an `Authorization` header will be added; the contract shapes will not change.

---

*This document is owned by **Pannaga** (`backend/app/api`, `backend/app/services`, `backend/app/database`, `backend/app/schemas`). Any changes to endpoint shapes must be coordinated with **Vineeth/Priyashu** (frontend) and reviewed by **Pranav** (Technical Lead) via Pull Request.*

# Backend ↔ AI Pipeline Integration Contract

**Owner:** Pannaga (Backend Engineer)  
**Consumer:** Sriganesh (AI Pipeline Engineer)  
**Last Updated:** 2026-07-23  
**Status:** Draft — ready for Sriganesh's review before implementation.

---

## Purpose

This document defines the **data contract** between Pannaga's backend service layer (`backend/app/services/`) and Sriganesh's AI pipeline (`backend/app/ai/`). It specifies:

1. What the service layer provides to the pipeline (inputs).
2. What the pipeline must return to the service layer (outputs).
3. How errors should be reported.
4. How the integration point works at runtime.

Neither side imports the other's internal modules directly. The service layer owns the contract models (`backend/app/schemas/pipeline.py`); the pipeline code produces data conforming to these shapes.

---

## Architecture Boundary

```
POST /upload (route)
       │
       ▼
upload_service.py (service layer — Pannaga)
       │
       ├── 1. Create resource row in SQLite (status = "processing")
       ├── 2. Return HTTP 202 to the client immediately
       └── 3. Schedule background processing:
              │
              ▼
        AI Pipeline (Sriganesh — backend/app/ai)
              │
              ├── On success → PipelineResult
              │      │
              │      ├── Service updates resource: status="ready", title, summary
              │      └── Service passes chunks to retrieval layer (Yeshneil)
              │
              └── On failure → PipelineFailure
                     │
                     └── Service updates resource: status="failed", error_message
```

> **Key rule:** The AI pipeline never writes to SQLite or returns HTTP responses. It receives input and produces a `PipelineResult` or `PipelineFailure` — the service layer handles the rest.

---

## Contract Models

All models are defined in [`backend/app/schemas/pipeline.py`](../backend/app/schemas/pipeline.py).

### Input: What the Service Layer Provides

The service layer will call the pipeline with:

| Parameter | Type | Description |
|---|---|---|
| `resource_id` | `str` | Stable resource identifier (e.g. `"res_abc123def456..."`) |
| `source_type` | `str` | `"url"` or `"pdf"` |
| `source_url` | `str \| None` | The URL to scrape (for URL uploads). `None` for PDFs. |
| `file_bytes` | `bytes \| None` | Raw PDF file content (for PDF uploads). `None` for URLs. |
| `filename` | `str \| None` | Original PDF filename. `None` for URLs. |

The exact function signature will be defined when wiring, but conceptually:

```python
# This function lives in backend/app/ai (Sriganesh's code).
# The service layer calls it.

def process_resource(
    resource_id: str,
    source_type: str,       # "url" or "pdf"
    source_url: str | None,
    file_bytes: bytes | None,
    filename: str | None,
) -> PipelineResult:
    """
    Run the full AI pipeline: extract → clean → chunk → embed → summarize.
    
    Returns PipelineResult on success.
    Raises PipelineExecutionError (or returns PipelineFailure) on failure.
    """
    ...
```

### Output on Success: `PipelineResult`

```python
class PipelineResult(BaseModel):
    resource_id: str                          # echoed back
    metadata: PipelineMetadata                # document-level info
    chunks: list[PipelineChunk]               # embedded text chunks (min 1)
    processing_time_seconds: float | None     # optional timing
```

> **Important:** `chunks` must contain at least one item. If the document has no extractable text, return a `PipelineFailure` with `stage="extraction"` instead of a `PipelineResult` with empty chunks.

### `PipelineMetadata` — Document-level information

| Field | Type | Required | Description |
|---|---|---|---|
| `resource_id` | `str` | Yes | Parent resource ID |
| `title` | `str \| None` | No | Extracted title (from `<title>` tag, PDF metadata, or first heading) |
| `summary` | `str` | Yes | AI-generated summary of the document |
| `source_type` | `str` | Yes | `"url"` or `"pdf"` |
| `source_url` | `str \| None` | No | Original URL (None for PDFs) |
| `filename` | `str \| None` | No | Original filename (None for URLs) |
| `total_chunks` | `int` | Yes | Number of chunks produced |
| `total_pages` | `int \| None` | No | Page count (PDF only) |
| `language` | `str \| None` | No | Detected language code (e.g. `"en"`) |
| `extra` | `dict \| None` | No | Any additional metadata for ChromaDB |

### `PipelineChunk` — One embedded text chunk

| Field | Type | Required | Description |
|---|---|---|---|
| `chunk_id` | `str` | Yes | Unique ID. Suggested: `"{resource_id}_chunk_{index:04d}"` |
| `resource_id` | `str` | Yes | Parent resource ID |
| `text` | `str` | Yes | Cleaned chunk text (non-empty) |
| `embedding` | `list[float]` | Yes | Dense vector. Dimension depends on model (e.g. 384) |
| `page_number` | `int \| None` | No | 1-indexed page (PDF only) |
| `chunk_index` | `int` | Yes | 0-indexed position in document |
| `char_start` | `int \| None` | No | Character offset start |
| `char_end` | `int \| None` | No | Character offset end |

### Output on Failure: `PipelineFailure`

| Field | Type | Required | Description |
|---|---|---|---|
| `resource_id` | `str` | Yes | The resource that failed |
| `stage` | `PipelineStage` | Yes | Which stage failed (see enum below) |
| `error_code` | `str` | Yes | Machine-readable code (e.g. `"pdf_parsing_error"`) |
| `error_message` | `str` | Yes | Human-readable description (no secrets) |
| `details` | `dict \| None` | No | Optional structured context |

### `PipelineStage` Enum

| Value | Meaning |
|---|---|
| `"extraction"` | URL scraping or PDF text extraction |
| `"cleaning"` | Text cleaning / normalisation |
| `"chunking"` | Text splitting into chunks |
| `"embedding"` | Vector embedding generation |
| `"summarization"` | AI summary generation |
| `"metadata"` | Metadata extraction |

---

## Error Handling Contract

1. **The pipeline should NOT let raw exceptions propagate.** Catch errors internally and either:
   - Return a `PipelineFailure` object, OR
   - Raise one of the domain exceptions below (defined in `backend/app/exceptions/types.py`) that the service layer catches.

2. **The service layer will:**
   - On `PipelineResult`: update resource to `status="ready"`, set `title`, `summary`, `completed_at`.
   - On `PipelineFailure` / exception: update resource to `status="failed"`, set `error_message`.

3. **Error messages should be safe for logging** — no API keys, no raw file contents, no stack traces in the message field.

### Pipeline Exception Classes

All defined in [`backend/app/exceptions/types.py`](../backend/app/exceptions/types.py). All inherit from `MaskaBaseError` (pure Python, no FastAPI imports).

> **Background task behaviour:** `POST /upload` returns `202 Accepted` immediately — before processing starts. Pipeline failures in background tasks therefore **never return an HTTP error to the upload caller**. Instead the service layer catches the exception and calls `crud.update_resource_status(db, resource_id, status="failed", error_message=...)`. The frontend discovers the failure by polling `GET /archive/{resource_id}` and checking `status == "failed"`.

| Exception | `code` | `http_status` | When to raise |
|---|---|---|---|
| `InvalidUrlError` | `invalid_url` | **400** | URL cannot be reached, returns non-200, or is unsuitable for extraction |
| `PdfParsingError` | `pdf_parsing_error` | 500 | PDF is corrupted, password-protected, or unreadable |
| `TextExtractionError` | `text_extraction_error` | 500 | No usable text could be extracted from the source |
| `EmbeddingGenerationError` | `embedding_error` | 500 | Embedding model unavailable, returns error, or produces invalid output |
| `PipelineExecutionError` | `pipeline_error` | 500 | General catch-all for pipeline failures not covered above |

### How Failed Processing Maps to Resource Status

When the service layer catches a pipeline exception during background processing:

```python
# In _run_background_processing (upload_service.py):
except (InvalidUrlError, PdfParsingError, TextExtractionError,
        EmbeddingGenerationError, PipelineExecutionError) as exc:
    crud.update_resource_status(
        db, resource_id,
        status="failed",
        error_message=exc.message,  # safe for logging, no secrets
    )
```

The frontend can then poll `GET /archive/{resource_id}` and see `status: "failed"` with `error_message` explaining what went wrong.

---

## What the Service Layer Does with the Result

```
PipelineResult received
    │
    ├── Update SQLite resource row:
    │     status = "ready"
    │     title = result.metadata.title
    │     summary = result.metadata.summary
    │     completed_at = utcnow()
    │
    └── Hand off to retrieval layer (Yeshneil):
          For each chunk in result.chunks:
              ChromaDB.upsert(
                  id = chunk.chunk_id,
                  document = chunk.text,
                  embedding = chunk.embedding,
                  metadata = {
                      resource_id, source_type, page_number,
                      chunk_index, ...result.metadata.extra
                  }
              )
```

---

## How to Integrate (Step by Step for Sriganesh)

1. **Implement your pipeline function** in `backend/app/ai/` (your owned directory).
2. **Accept the input parameters** listed above (resource_id, source_type, source_url, file_bytes, filename).
3. **Return a `PipelineResult`** on success with all chunks and metadata populated.
4. **Return a `PipelineFailure`** (or raise `PipelineExecutionError`) on failure.
5. **Do NOT** write to SQLite, return HTTP responses, or import from `app.services`.
6. **Do NOT** hardcode API keys — read from environment via `app.core.config.get_settings().llm_api_key`.
7. When ready, tell Pannaga — the service layer wiring (calling your function from `upload_service.py`) is Pannaga's responsibility.

---

## Open Questions for Team Alignment

1. **Embedding model & dimension:** Which model will Sriganesh use? The `embedding` field is `list[float]` — Yeshneil needs to know the dimension for ChromaDB collection setup.
2. **Chunk size strategy:** What chunk size / overlap will the pipeline use? This affects retrieval quality.
3. **Sync vs async:** Should `process_resource()` be sync or async? The service layer can handle either via `BackgroundTasks` or `asyncio.to_thread()`.
4. **LLM provider:** Which LLM for summarization? The `llm_api_key` config field is ready but provider-agnostic.

---

*This document is maintained by **Pannaga** (Backend). Changes to the contract shapes must be coordinated with **Sriganesh** (AI Pipeline) and **Yeshneil** (Retrieval) and reviewed by **Pranav** (Tech Lead).*

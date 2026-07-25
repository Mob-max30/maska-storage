"""
backend/app/schemas/pipeline.py
---------------------------------
Backend-owned contract models for the AI pipeline handoff.

These Pydantic models define the **data shapes** that Sriganesh's AI pipeline
(``backend/app/ai``) must produce after processing a URL or PDF resource.
The service layer (``backend/app/services``) will consume these models to
persist results to SQLite and hand off embeddings/chunks to Yeshneil's
retrieval layer (ChromaDB).

Ownership
~~~~~~~~~
These models are owned by Pannaga (backend). Sriganesh's pipeline code
must return data conforming to these shapes but does NOT need to import
them — the service layer handles the translation.

Design rules
~~~~~~~~~~~~
* No imports from ``app.ai`` or ``app.retrieval`` — this file is a
  backend-only contract definition.
* All fields use standard Python types + Pydantic so they can be
  serialised, logged, and validated without AI/ML dependencies.
* ``embedding`` is typed as ``list[float]`` — the pipeline is responsible
  for producing a fixed-dimension float vector.
* These models are NOT API request/response schemas — they are internal
  data transfer objects between the service layer and the AI pipeline.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class PipelineStage(str, Enum):
    """Stages of the AI pipeline — used for progress tracking and error reporting."""

    EXTRACTION = "extraction"
    CLEANING = "cleaning"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    SUMMARIZATION = "summarization"
    METADATA = "metadata"


# ---------------------------------------------------------------------------
# Chunk — one piece of extracted and embedded content
# ---------------------------------------------------------------------------


class PipelineChunk(BaseModel):
    """
    A single chunk of content produced by the AI pipeline.

    After extraction, cleaning, and chunking, each chunk is independently
    embedded and stored in ChromaDB. The ``chunk_id`` is unique within a
    resource and is used as the ChromaDB document ID.

    Fields
    ------
    chunk_id : str
        Unique identifier for this chunk within the resource.
        Suggested format: ``"{resource_id}_chunk_{index:04d}"``
    resource_id : str
        Parent resource identifier (matches the ``resources`` table PK).
    text : str
        The cleaned, chunked text content. Must not be empty.
    embedding : list[float]
        Dense vector representation of ``text``. Dimension depends on
        the embedding model used (e.g. 384 for all-MiniLM-L6-v2).
    page_number : int | None
        For PDF sources: the 1-indexed page this chunk was extracted from.
        ``None`` for URL sources or when page tracking is unavailable.
    chunk_index : int
        0-indexed position of this chunk within the full document.
        Preserves original document ordering for context reconstruction.
    char_start : int | None
        Character offset where this chunk starts in the cleaned document.
        ``None`` if not tracked.
    char_end : int | None
        Character offset where this chunk ends in the cleaned document.
        ``None`` if not tracked.
    """

    chunk_id: str = Field(
        ...,
        description="Unique chunk identifier. Format: '{resource_id}_chunk_{index:04d}'.",
        examples=["res_abc123_chunk_0001"],
    )
    resource_id: str = Field(
        ...,
        description="Parent resource identifier.",
        examples=["res_abc123"],
    )
    text: str = Field(
        ...,
        min_length=1,
        description="Cleaned, chunked text content.",
    )
    embedding: list[float] = Field(
        ...,
        description="Dense vector embedding of the text chunk.",
    )
    page_number: int | None = Field(
        default=None,
        description="1-indexed page number for PDF sources. None for URLs.",
    )
    chunk_index: int = Field(
        ...,
        ge=0,
        description="0-indexed position of this chunk in the document.",
    )
    char_start: int | None = Field(
        default=None,
        description="Character offset where this chunk starts in the cleaned document.",
    )
    char_end: int | None = Field(
        default=None,
        description="Character offset where this chunk ends in the cleaned document.",
    )


# ---------------------------------------------------------------------------
# Metadata — extracted document-level information
# ---------------------------------------------------------------------------


class PipelineMetadata(BaseModel):
    """
    Document-level metadata extracted by the AI pipeline.

    This information is used to update the ``resources`` table (title,
    summary) and to enrich ChromaDB document metadata for better retrieval.

    Fields
    ------
    resource_id : str
        The resource this metadata belongs to.
    title : str | None
        Extracted or inferred document title. For PDFs this may come from
        PDF metadata or the first heading. For URLs, from the <title> tag.
    summary : str
        AI-generated summary of the full document content.
    source_type : str
        "url" or "pdf" — echoed from the resource record.
    source_url : str | None
        Original URL for URL-sourced resources. None for PDFs.
    filename : str | None
        Original filename for PDF uploads. None for URL resources.
    total_chunks : int
        Number of chunks produced from this document.
    total_pages : int | None
        Number of pages (PDF only). None for URL resources.
    language : str | None
        Detected language code (e.g. "en"). None if detection was skipped.
    extra : dict[str, Any] | None
        Any additional metadata the pipeline wants to pass through.
        The service layer will not interpret this — it is stored as-is
        in ChromaDB metadata.
    """

    resource_id: str = Field(..., description="Parent resource identifier.")
    title: str | None = Field(
        default=None,
        description="Extracted or inferred document title.",
    )
    summary: str = Field(
        ...,
        description="AI-generated summary of the full document.",
    )
    source_type: str = Field(
        ...,
        description="'url' or 'pdf'.",
    )
    source_url: str | None = Field(
        default=None,
        description="Original URL. None for PDF uploads.",
    )
    filename: str | None = Field(
        default=None,
        description="Original PDF filename. None for URL resources.",
    )
    total_chunks: int = Field(
        ...,
        ge=0,
        description="Number of chunks produced.",
    )
    total_pages: int | None = Field(
        default=None,
        description="Number of pages (PDF only).",
    )
    language: str | None = Field(
        default=None,
        description="Detected language code (e.g. 'en').",
    )
    extra: dict[str, Any] | None = Field(
        default=None,
        description="Additional metadata passed through to ChromaDB.",
    )


# ---------------------------------------------------------------------------
# Result — successful pipeline completion
# ---------------------------------------------------------------------------


class PipelineResult(BaseModel):
    """
    Complete output of a successful AI pipeline run for one resource.

    The service layer uses this to:
      1. Update the ``resources`` table with title, summary, status="ready".
      2. Pass chunks + metadata to Yeshneil's retrieval layer for ChromaDB storage.

    The pipeline must produce this object and return it to the service layer.

    Important:
      ``chunks`` must contain at least one item. If the document has no
      extractable text, the pipeline should return a ``PipelineFailure``
      (stage="extraction") instead of a ``PipelineResult`` with empty chunks.
    """

    resource_id: str = Field(..., description="The resource that was processed.")
    metadata: PipelineMetadata = Field(
        ...,
        description="Extracted document-level metadata.",
    )
    chunks: list[PipelineChunk] = Field(
        ...,
        min_length=1,
        description=(
            "Ordered list of embedded chunks. Must contain at least one chunk. "
            "If no text could be extracted, return PipelineFailure instead."
        ),
    )
    processing_time_seconds: float | None = Field(
        default=None,
        description="Wall-clock time for the full pipeline run, in seconds.",
    )


# ---------------------------------------------------------------------------
# Failure — pipeline error report
# ---------------------------------------------------------------------------


class PipelineFailure(BaseModel):
    """
    Error report from a failed AI pipeline run.

    The service layer uses this to update the resource status to "failed"
    and store a human-readable error message for debugging.

    The pipeline should catch its own exceptions and produce this object
    rather than letting raw exceptions propagate to the service layer.
    """

    resource_id: str = Field(..., description="The resource that failed processing.")
    stage: PipelineStage = Field(
        ...,
        description="The pipeline stage where the failure occurred.",
    )
    error_code: str = Field(
        ...,
        description="Machine-readable error code (e.g. 'pdf_parsing_error').",
    )
    error_message: str = Field(
        ...,
        description="Human-readable error description. Safe for logging; do not include secrets.",
    )
    details: dict[str, Any] | None = Field(
        default=None,
        description="Optional structured error context.",
    )

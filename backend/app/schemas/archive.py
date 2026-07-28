"""
archive.py
----------
Schemas for:
    GET  /archive               → ArchiveListResponse
    GET  /archive/{resource_id} → ArchiveItemDetail
    DELETE /archive/{resource_id} → DeleteResourceResponse

Design notes
~~~~~~~~~~~~
* ``ArchiveItem`` is the compact list-view shape (used inside
  ``ArchiveListResponse``).

* ``ArchiveItemDetail`` extends ``ArchiveItem`` with extra fields that
  are only included in the single-resource detail view (e.g. ``source_url``).
  This avoids returning large fields unnecessarily in the paginated list.

* ``ArchiveListResponse`` wraps a list of ``ArchiveItem`` objects with
  pagination metadata so the frontend can build page controls.

* ``DeleteResourceResponse`` is the slim acknowledgement returned after a
  successful DELETE. The echoed ``resource_id`` lets the frontend reconcile
  its local state without a follow-up fetch.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import ResourceStatus, SourceType


# ---------------------------------------------------------------------------
# Shared list-item shape
# ---------------------------------------------------------------------------


class ArchiveItem(BaseModel):
    """
    Compact resource representation used inside the paginated archive list.

    Intentionally omits large or URL-specific fields (e.g. ``source_url``)
    that are not needed for list rendering.

    Shape (one item inside ``ArchiveListResponse.items``)::

        {
          "id": "res_01j9k3m7xp0000000000000000",
          "title": "Example Article Title",
          "source_type": "url",
          "status": "ready",
          "summary": "A concise AI-generated summary...",
          "created_at": "2026-07-21T14:30:00Z",
          "updated_at": "2026-07-21T14:32:45Z"
        }
    """

    id: str = Field(
        ...,
        description="Unique resource identifier.",
        examples=["res_01j9k3m7xp0000000000000000"],
    )
    title: str | None = Field(
        default=None,
        description="Extracted or inferred title. Null while processing.",
        examples=["Example Article Title", None],
    )
    source_type: SourceType = Field(
        ...,
        description="Whether the resource originated from a URL or a PDF file.",
        examples=[SourceType.URL],
    )
    status: ResourceStatus = Field(
        ...,
        description=(
            "Current processing state. "
            "'ready' and 'failed' are terminal — stop polling on either."
        ),
        examples=[ResourceStatus.READY],
    )
    summary: str | None = Field(
        default=None,
        description="AI-generated summary. Null while processing or if summarization failed.",
        examples=["A concise AI-generated summary of the resource content.", None],
    )
    created_at: datetime = Field(
        ...,
        description="UTC timestamp of initial resource creation (ISO 8601).",
        examples=["2026-07-21T14:30:00Z"],
    )
    updated_at: datetime = Field(
        ...,
        description="UTC timestamp of the last status or metadata update (ISO 8601).",
        examples=["2026-07-21T14:32:45Z"],
    )


# ---------------------------------------------------------------------------
# Single-resource detail (GET /archive/{resource_id})
# ---------------------------------------------------------------------------


class ArchiveItemDetail(ArchiveItem):
    """
    Full detail record for a single resource.

    Extends ``ArchiveItem`` with fields that are only needed for the
    single-resource detail view — omitted from the list to reduce payload.

    Shape (GET /archive/{resource_id} success response)::

        {
          "id": "res_01j9k3m7xp0000000000000000",
          "title": "Example Article Title",
          "source_type": "url",
          "source_url": "https://example.com/article",
          "filename": null,
          "status": "ready",
          "summary": "A concise AI-generated summary...",
          "error_message": null,
          "created_at": "2026-07-21T14:30:00Z",
          "updated_at": "2026-07-21T14:32:45Z",
          "completed_at": "2026-07-21T14:32:45Z"
        }

    Frontend polling note:
        After POST /upload, poll this endpoint every 3-5 seconds until
        ``status`` is ``"ready"`` or ``"failed"``. Do not poll the list
        endpoint for status updates — use this single-resource endpoint.

    Failure handling:
        When ``status == "failed"``, render ``error_message`` to the user
        so they understand why processing did not complete (e.g. unreachable
        URL, corrupt PDF). ``completed_at`` is set on both "ready" and "failed".
    """

    source_url: str | None = Field(
        default=None,
        description=(
            "The original URL that was ingested. "
            "Null for PDF uploads (source_type == 'pdf')."
        ),
        examples=["https://example.com/article", None],
    )
    filename: str | None = Field(
        default=None,
        description=(
            "Original PDF filename. "
            "Null for URL uploads (source_type == 'url')."
        ),
        examples=["research_paper.pdf", None],
    )
    error_message: str | None = Field(
        default=None,
        description=(
            "Human-readable pipeline failure reason. "
            "Non-null only when status == 'failed'. "
            "Safe to surface in the UI."
        ),
        examples=["PDF parsing failed: file is password-protected.", None],
    )
    completed_at: datetime | None = Field(
        default=None,
        description=(
            "UTC timestamp when pipeline processing finished "
            "(status transitioned to 'ready' or 'failed'). "
            "Null while status is 'pending' or 'processing'."
        ),
        examples=["2026-07-21T14:32:45Z", None],
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": "res_01j9k3m7xp0000000000000000",
                    "title": "Example Article Title",
                    "source_type": "url",
                    "source_url": "https://example.com/article",
                    "filename": None,
                    "status": "ready",
                    "summary": "A concise AI-generated summary of the resource content.",
                    "error_message": None,
                    "created_at": "2026-07-21T14:30:00Z",
                    "updated_at": "2026-07-21T14:32:45Z",
                    "completed_at": "2026-07-21T14:32:45Z",
                }
            ]
        }
    }


# ---------------------------------------------------------------------------
# Paginated list response (GET /archive)
# ---------------------------------------------------------------------------


class ArchiveListResponse(BaseModel):
    """
    Paginated response for GET /archive.

    ``items`` is always a list (may be empty — that is not an error).
    ``total`` reflects the count of all matching records across all pages,
    not just the current page.

    Shape::

        {
          "items": [ ...ArchiveItem... ],
          "total": 42,
          "page": 1,
          "page_size": 20
        }

    Frontend notes:
        - An empty ``items`` array with ``total == 0`` is valid — render
          an empty state, not an error.
        - Use ``total``, ``page``, and ``page_size`` for pagination controls.
    """

    items: list[ArchiveItem] = Field(
        default_factory=list,
        description="Resource summaries for the current page.",
    )
    total: int = Field(
        ...,
        description="Total number of resources matching the applied filters (across all pages).",
        examples=[42],
        ge=0,
    )
    page: int = Field(
        ...,
        description="Current page number (1-indexed).",
        examples=[1],
        ge=1,
    )
    page_size: int = Field(
        ...,
        description="Number of items per page.",
        examples=[20],
        ge=1,
        le=100,
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "items": [
                        {
                            "id": "res_01j9k3m7xp0000000000000000",
                            "title": "Example Article Title",
                            "source_type": "url",
                            "status": "ready",
                            "summary": "A concise AI-generated summary of the resource content.",
                            "created_at": "2026-07-21T14:30:00Z",
                            "updated_at": "2026-07-21T14:32:45Z",
                        },
                        {
                            "id": "res_01j9k3m7xp0000000000000001",
                            "title": "Research Paper.pdf",
                            "source_type": "pdf",
                            "status": "processing",
                            "summary": None,
                            "created_at": "2026-07-21T14:35:00Z",
                            "updated_at": "2026-07-21T14:35:00Z",
                        },
                    ],
                    "total": 42,
                    "page": 1,
                    "page_size": 20,
                }
            ]
        }
    }


# ---------------------------------------------------------------------------
# Delete response (DELETE /archive/{resource_id})
# ---------------------------------------------------------------------------


class DeleteResourceResponse(BaseModel):
    """
    Acknowledgement response for DELETE /archive/{resource_id}.

    Deletion removes the resource record from SQLite **and** the associated
    vectors from ChromaDB. This operation is irreversible.

    The frontend should:
        1. Show a confirmation dialog before calling this endpoint.
        2. On 200: use ``resource_id`` to remove the item from local state.
        3. On 404: treat as already-deleted — update local state the same way.

    Shape::

        {
          "deleted": true,
          "resource_id": "res_01j9k3m7xp0000000000000000"
        }
    """

    deleted: bool = Field(
        default=True,
        description="Always true on a successful deletion.",
        examples=[True],
    )
    resource_id: str = Field(
        ...,
        description="Echoed resource id — use this to reconcile local frontend state.",
        examples=["res_01j9k3m7xp0000000000000000"],
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "deleted": True,
                    "resource_id": "res_01j9k3m7xp0000000000000000",
                }
            ]
        }
    }

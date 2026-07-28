"""
upload.py
---------
Schemas for POST /upload.

Design notes
~~~~~~~~~~~~
* The route receives ``multipart/form-data``, so the raw ``UploadFile``
  object (for PDFs) and the ``url`` string (for URLs) are extracted
  directly by FastAPI as function parameters — they are NOT wrapped in a
  Pydantic model themselves (Pydantic cannot parse UploadFile).

* ``UrlUploadRequest`` is used when the route needs to validate a
  URL-only form submission where the URL is passed as a form field.
  It is instantiated manually inside the route handler from the form value.

* ``UploadResponse`` is the ``202 Accepted`` body returned immediately
  after the resource record is created. AI processing is async — the
  frontend must poll GET /archive/{resource_id} for status updates.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field, HttpUrl, field_validator

from app.schemas.common import ResourceStatus, SourceType


# ---------------------------------------------------------------------------
# Request
# ---------------------------------------------------------------------------


class UrlUploadRequest(BaseModel):
    """
    Validated metadata for a URL-based upload.

    Instantiated inside the route handler after extracting the raw form
    field. It is NOT the top-level request body (that is multipart/form-data).

    Validation:
        - ``url`` must be a valid HTTP or HTTPS URL.
        - Pydantic's ``HttpUrl`` type rejects mailto:, ftp:, etc.
    """

    url: Annotated[
        HttpUrl,
        Field(
            ...,
            description="Publicly accessible HTTP/HTTPS URL to ingest.",
            examples=["https://example.com/article"],
        ),
    ]

    model_config = {
        "json_schema_extra": {
            "examples": [{"url": "https://example.com/article"}]
        }
    }


# ---------------------------------------------------------------------------
# Response
# ---------------------------------------------------------------------------


class UploadResponse(BaseModel):
    """
    Response body for a successful POST /upload.

    Returned with HTTP 202 Accepted. The resource record has been created
    and pipeline processing has started, but the resource is NOT yet ready
    to query. The frontend should treat this as "accepted, not complete".

    Status lifecycle:
        pending → processing → ready   (happy path)
        pending → processing → failed  (pipeline error)

    The frontend must poll GET /archive/{resource_id} until ``status``
    is ``"ready"`` or ``"failed"`` (both are terminal states).

    Shape::

        {
          "resource_id": "res_01j9k3m7xp0000000000000000",
          "status": "processing",
          "source_type": "url",
          "title": "Example Article Title",
          "summary": null,
          "created_at": "2026-07-21T14:30:00Z"
        }
    """

    resource_id: str = Field(
        ...,
        description=(
            "Stable unique identifier for this resource. "
            "Store this immediately — it is used for Archive and Chat calls."
        ),
        examples=["res_01j9k3m7xp0000000000000000"],
    )
    status: ResourceStatus = Field(
        ...,
        description=(
            "Current processing state. Will be 'processing' or 'pending' at "
            "upload time. Poll GET /archive/{resource_id} for updates."
        ),
        examples=[ResourceStatus.PROCESSING],
    )
    source_type: SourceType = Field(
        ...,
        description="Whether the resource originated from a URL or a PDF file.",
        examples=[SourceType.URL],
    )
    title: str | None = Field(
        default=None,
        description=(
            "Extracted or inferred title. Null if not yet available at "
            "response time — may be populated once processing completes."
        ),
        examples=["Example Article Title", None],
    )
    summary: str | None = Field(
        default=None,
        description=(
            "AI-generated summary. Always null at upload time. "
            "Populated once the pipeline finishes summarization."
        ),
        examples=[None],
    )
    created_at: datetime = Field(
        ...,
        description="UTC timestamp of when the resource record was created (ISO 8601).",
        examples=["2026-07-21T14:30:00Z"],
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "resource_id": "res_01j9k3m7xp0000000000000000",
                    "status": "processing",
                    "source_type": "url",
                    "title": "Example Article Title",
                    "summary": None,
                    "created_at": "2026-07-21T14:30:00Z",
                }
            ]
        }
    }

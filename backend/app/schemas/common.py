"""
common.py
---------
Shared enums and the universal error envelope used by every endpoint.

All routes return errors using ErrorResponse so the frontend always
receives the same JSON shape regardless of which endpoint failed.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class SourceType(str, Enum):
    """The origin format of an ingested resource."""

    URL = "url"
    PDF = "pdf"


class ResourceStatus(str, Enum):
    """
    Lifecycle states of a resource through the ingestion pipeline.

    Transitions:
        pending → processing → ready   (happy path)
        pending → processing → failed  (pipeline error)

    Notes:
        - ``pending``    : record created, pipeline not yet started.
        - ``processing`` : pipeline actively running (extraction → embedding).
        - ``ready``      : all pipeline stages complete; resource is queryable.
        - ``failed``     : pipeline encountered an unrecoverable error.
    """

    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


# ---------------------------------------------------------------------------
# Error envelope
# ---------------------------------------------------------------------------


class ErrorDetail(BaseModel):
    """
    Inner payload of an error response.

    ``code`` is machine-readable (used by the frontend for branching logic).
    ``message`` is human-readable and safe to surface in the UI.
    ``details`` is an optional free-form object — for example, field-level
    validation errors from Pydantic, or partial-failure context.
    """

    code: str = Field(
        ...,
        description=(
            "Machine-readable error code. "
            "Examples: 'not_found', 'validation_error', 'internal_error'."
        ),
        examples=["not_found", "validation_error", "internal_error"],
    )
    message: str = Field(
        ...,
        description="Human-readable explanation safe to display in the UI.",
        examples=["No resource found with the provided id."],
    )
    details: dict[str, Any] | None = Field(
        default=None,
        description=(
            "Optional structured detail. May contain field names, received values, "
            "or partial-failure context. Null when there is no extra information."
        ),
    )


class ErrorResponse(BaseModel):
    """
    Universal error envelope returned by all endpoints on failure.

    Shape::

        {
          "error": {
            "code": "not_found",
            "message": "No resource found with id 'res_...'.",
            "details": {"resource_id": "res_..."}
          }
        }

    The frontend must check for the presence of the ``"error"`` key to
    distinguish error responses from success responses.
    """

    error: ErrorDetail = Field(..., description="Error detail payload.")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "error": {
                        "code": "not_found",
                        "message": "No resource found with id 'res_01j9k3m7xp0000000000000000'.",
                        "details": {"resource_id": "res_01j9k3m7xp0000000000000000"},
                    }
                }
            ]
        }
    }

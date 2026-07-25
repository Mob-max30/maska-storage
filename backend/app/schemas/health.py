"""
health.py
---------
Schema for GET /health.

This is the simplest endpoint — a liveness probe that confirms the API
process is reachable. No auth, no body, no path parameters.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """
    Success response for GET /health.

    Returned with HTTP 200. A non-200 response (network error, 5xx) means
    the server itself is unavailable — not a schema-level failure.

    Shape::

        {
          "status": "ok",
          "service": "maska-storage-api",
          "version": "0.1.0"
        }
    """

    status: str = Field(
        default="ok",
        description="Always 'ok' when the server is reachable.",
        examples=["ok"],
    )
    service: str = Field(
        default="maska-storage-api",
        description="Human-readable service name.",
        examples=["maska-storage-api"],
    )
    version: str = Field(
        ...,
        description="Application version string (semver).",
        examples=["0.1.0"],
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "status": "ok",
                    "service": "maska-storage-api",
                    "version": "0.1.0",
                }
            ]
        }
    }

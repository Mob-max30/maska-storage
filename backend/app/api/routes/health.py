"""
backend/app/api/routes/health.py
---------------------------------
GET /health — Liveness probe.

Route responsibility: receive the request and return a response.
No business logic lives here. When real monitoring/version metadata
is needed, inject it via a service call (see TODO below).
"""

from __future__ import annotations

from app.core.config import get_settings
from app.schemas import HealthResponse
from fastapi import APIRouter

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Liveness check",
    description=(
        "Lightweight endpoint confirming the API process is reachable. "
        "Returns HTTP 200 when healthy. A non-200 means the server is down."
    ),
    tags=["health"],
)
def get_health() -> HealthResponse:
    """
    Return service liveness status.

    This route contains no business logic. In a future phase, the version
    string and any dependency-health checks (DB, ChromaDB) will be
    delegated to a health-check service.
    """
    settings = get_settings()
    return HealthResponse(
        status="ok",
        service="maska-storage-api",
        version=settings.app_version,
    )

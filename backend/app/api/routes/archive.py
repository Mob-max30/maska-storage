"""
backend/app/api/routes/archive.py
-----------------------------------
Archive routes:

    GET    /archive                   → paginated resource list
    GET    /archive/{resource_id}     → single resource detail
    DELETE /archive/{resource_id}     → permanent deletion

Route responsibility
~~~~~~~~~~~~~~~~~~~~
* Parse and validate query/path parameters.
* Inject a database session via ``Depends(get_db)``.
* Call the appropriate archive_service function, passing the session.
* Translate a ``None`` return value into a 404 HTTPException.
* Return the service result directly.

What does NOT live here
~~~~~~~~~~~~~~~~~~~~~~~
* No business logic — that lives in archive_service.
* No direct database/CRUD calls — only the session is obtained here.
* No ChromaDB calls.
"""

from __future__ import annotations

from app.database.session import get_db
from app.exceptions import ResourceNotFoundError
from app.schemas import (
    ArchiveItemDetail,
    ArchiveListResponse,
    DeleteResourceResponse,
    ResourceStatus,
    SourceType,
)
from app.services import archive_service
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

router = APIRouter()


# ---------------------------------------------------------------------------
# GET /archive — paginated list
# ---------------------------------------------------------------------------


@router.get(
    "/archive",
    response_model=ArchiveListResponse,
    summary="List archived resources",
    description=(
        "Returns a paginated list of all ingested resources. "
        "Supports optional filtering by status and source_type."
    ),
    tags=["archive"],
)
def list_archive(
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)."),
    page_size: int = Query(
        default=20, ge=1, le=100, description="Items per page. Max: 100."
    ),
    status_filter: ResourceStatus | None = Query(
        default=None,
        alias="status",
        description="Filter by resource status: pending, processing, ready, failed.",
    ),
    source_type_filter: SourceType | None = Query(
        default=None,
        alias="source_type",
        description="Filter by source type: url or pdf.",
    ),
    db: Session = Depends(get_db),
) -> ArchiveListResponse:
    """
    Delegate to archive_service.list_resources and return the result.
    """
    return archive_service.list_resources(
        db=db,
        page=page,
        page_size=page_size,
        status_filter=status_filter,
        source_type_filter=source_type_filter,
    )


# ---------------------------------------------------------------------------
# GET /archive/{resource_id} — single resource detail
# ---------------------------------------------------------------------------


@router.get(
    "/archive/{resource_id}",
    response_model=ArchiveItemDetail,
    summary="Get resource detail",
    description=(
        "Returns full detail for a single resource. "
        "Use this endpoint to poll status after POST /upload. "
        "Status 'ready' and 'failed' are terminal — stop polling on either."
    ),
    tags=["archive"],
)
def get_archive_item(
    resource_id: str,
    db: Session = Depends(get_db),
) -> ArchiveItemDetail:
    """
    Delegate to archive_service.get_resource. Raise 404 if not found.
    """
    result = archive_service.get_resource(db=db, resource_id=resource_id)

    if result is None:
        raise ResourceNotFoundError(resource_id)

    return result


# ---------------------------------------------------------------------------
# DELETE /archive/{resource_id} — permanent deletion
# ---------------------------------------------------------------------------


@router.delete(
    "/archive/{resource_id}",
    response_model=DeleteResourceResponse,
    summary="Delete a resource",
    description=(
        "Permanently deletes a resource — metadata from SQLite and "
        "vectors from ChromaDB. This operation is irreversible. "
        "Show a confirmation dialog in the UI before calling this."
    ),
    tags=["archive"],
)
def delete_archive_item(
    resource_id: str,
    db: Session = Depends(get_db),
) -> DeleteResourceResponse:
    """
    Delegate to archive_service.delete_resource. Raise 404 if not found.

    Frontend note: a 404 on DELETE means the resource is already gone.
    Treat it as a successful deletion and update local state accordingly.
    """
    result = archive_service.delete_resource(db=db, resource_id=resource_id)

    if result is None:
        raise ResourceNotFoundError(resource_id)

    return result

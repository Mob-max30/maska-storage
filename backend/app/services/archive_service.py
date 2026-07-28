"""
backend/app/services/archive_service.py
-----------------------------------------
Service layer for archive read/delete operations.

Responsibility
~~~~~~~~~~~~~~
This module owns the business logic for listing, retrieving, and deleting
stored resources. Routes call functions here; routes never query storage
directly. The service maps ORM Resource objects to Pydantic schema instances
before returning, keeping the database layer decoupled from the API contract.

Current state: SQLite-backed
    All functions delegate to database.crud, which queries the SQLite
    ``resources`` table. The in-memory mock store has been removed.

Seed data
~~~~~~~~~
``seed_mock_resources(db)`` inserts two realistic sample rows the first time
the database is empty. It is called once from the app lifespan (main.py) and
is idempotent — skipped if any resource row already exists. This keeps the
frontend team's archive page populated during development.

Not-found convention
~~~~~~~~~~~~~~~~~~~~
Functions return ``None`` (or ``False`` for delete) when the requested
resource does not exist. The calling route raises HTTPException 404.
Services never raise HTTPException.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.database import crud
from app.schemas import (
    ArchiveItem,
    ArchiveItemDetail,
    ArchiveListResponse,
    DeleteResourceResponse,
    ResourceStatus,
    SourceType,
)
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _to_archive_item(r) -> ArchiveItem:
    """Map a Resource ORM row to an ArchiveItem schema."""
    return ArchiveItem(
        id=r.resource_id,
        title=r.title,
        source_type=SourceType(r.source_type),
        status=ResourceStatus(r.status),
        summary=r.summary,
        created_at=r.created_at,
        updated_at=r.updated_at,
    )


def _to_archive_item_detail(r) -> ArchiveItemDetail:
    """Map a Resource ORM row to an ArchiveItemDetail schema."""
    return ArchiveItemDetail(
        id=r.resource_id,
        title=r.title,
        source_type=SourceType(r.source_type),
        source_url=r.source_url,
        filename=r.filename,
        status=ResourceStatus(r.status),
        summary=r.summary,
        error_message=r.error_message,
        created_at=r.created_at,
        updated_at=r.updated_at,
        completed_at=r.completed_at,
    )


# ---------------------------------------------------------------------------
# Seed helper — called once on startup when the DB is empty
# ---------------------------------------------------------------------------


def seed_mock_resources(db: Session) -> None:
    """
    Insert two realistic sample resources when the database is empty.

    This is an idempotent development convenience so the frontend archive
    page is never blank on first run. It is safe to call on every startup —
    skipped immediately if any resource row already exists.

    Do NOT call this from routes or services other than the startup hook in
    main.py. Remove or gate behind an environment flag before production.

    TODO(pannaga): gate behind ``settings.seed_on_startup`` (default False
        in production) once app.core.config.Settings is wired.
    """
    existing, total = crud.list_resources(db, page=1, page_size=1)
    if total > 0:
        return  # DB already has data — skip seeding

    now = datetime.now(tz=timezone.utc)

    # Seed 1: a ready URL resource
    crud.create_resource(
        db,
        resource_id="res_seed_000000000000000001",
        source_type=SourceType.URL.value,
        status=ResourceStatus.READY.value,
        source_url="https://example.com/article",
        title="Example Article Title",
        summary="A concise AI-generated summary of the resource content.",
    )
    crud.update_resource_status(
        db,
        "res_seed_000000000000000001",
        status=ResourceStatus.READY.value,
        completed_at=now,
    )

    # Seed 2: a PDF still in processing
    crud.create_resource(
        db,
        resource_id="res_seed_000000000000000002",
        source_type=SourceType.PDF.value,
        status=ResourceStatus.PROCESSING.value,
        filename="Research Paper on Attention Mechanisms.pdf",
        title="Research Paper on Attention Mechanisms.pdf",
        summary=None,
    )

    # Seed 3: a failed URL resource (demonstrates error_message field)
    crud.create_resource(
        db,
        resource_id="res_seed_000000000000000003",
        source_type=SourceType.URL.value,
        status=ResourceStatus.FAILED.value,
        source_url="https://example.com/private-page",
        title="Private Page (failed)",
        summary=None,
    )
    crud.update_resource_status(
        db,
        "res_seed_000000000000000003",
        status=ResourceStatus.FAILED.value,
        error_message="Invalid or unreachable URL: the page returned HTTP 403.",
        completed_at=now,
    )


# ---------------------------------------------------------------------------
# Public service functions
# ---------------------------------------------------------------------------


def list_resources(
    db: Session,
    page: int,
    page_size: int,
    status_filter: ResourceStatus | None,
    source_type_filter: SourceType | None,
) -> ArchiveListResponse:
    """
    Return a paginated, optionally-filtered list of resources from SQLite.

    Parameters
    ----------
    db:
        Active SQLAlchemy session, provided by the route.
    page:
        1-indexed page number. Validated upstream by the route.
    page_size:
        Items per page (1–100). Validated upstream.
    status_filter:
        When provided, only resources with this status are returned.
    source_type_filter:
        When provided, only resources with this source_type are returned.

    Returns
    -------
    ArchiveListResponse
        Always valid — ``items`` may be an empty list.
    """
    rows, total = crud.list_resources(
        db,
        page=page,
        page_size=page_size,
        status=status_filter.value if status_filter is not None else None,
        source_type=source_type_filter.value if source_type_filter is not None else None,
    )

    return ArchiveListResponse(
        items=[_to_archive_item(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


def get_resource(db: Session, resource_id: str) -> ArchiveItemDetail | None:
    """
    Return full detail for a single resource, or ``None`` if not found.

    The route translates ``None`` into a 404 HTTPException.

    Parameters
    ----------
    db:
        Active SQLAlchemy session.
    resource_id:
        The unique resource identifier to look up.

    Returns
    -------
    ArchiveItemDetail | None
    """
    row = crud.get_resource(db, resource_id)
    if row is None:
        logger.warning("Resource not found: resource_id=%s", resource_id)
        return None
    return _to_archive_item_detail(row)


def delete_resource(db: Session, resource_id: str) -> DeleteResourceResponse | None:
    """
    Permanently delete a resource. Returns ``None`` if not found.

    The route translates ``None`` into a 404 HTTPException.

    Note: this function only removes the SQLite metadata row. ChromaDB
    vector deletion must be coordinated with Yeshneil's retrieval module —
    see TODO below.

    Parameters
    ----------
    db:
        Active SQLAlchemy session.
    resource_id:
        The unique resource identifier to delete.

    Returns
    -------
    DeleteResourceResponse | None
        Confirmation on success, or ``None`` if the resource was not found.

    TODO(pannaga + yeshneil): before deleting the DB row, call:
        retrieval.vector_store.delete_by_resource_id(resource_id)
        (idempotent — safe even if no vectors exist yet)
    """
    deleted = crud.delete_resource(db, resource_id)
    if not deleted:
        logger.warning("Delete requested for non-existent resource: resource_id=%s", resource_id)
        return None

    logger.info("Resource deleted: resource_id=%s", resource_id)
    return DeleteResourceResponse(
        deleted=True,
        resource_id=resource_id,
    )

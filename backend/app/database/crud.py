"""
backend/app/database/crud.py
------------------------------
CRUD helper functions for the ``resources`` table.

Requires: sqlalchemy>=2.0  (pip install sqlalchemy)

Design rules
~~~~~~~~~~~~
* Every function takes an explicit ``db: Session`` parameter.
  The caller (service layer) owns the session lifecycle — these functions
  never open or close sessions themselves.
* Every function is synchronous. Async SQLAlchemy is deferred to a later
  phase when/if the app moves to async I/O throughout.
* These functions return ORM model instances (``Resource``), not Pydantic
  schemas. The service layer maps ORM objects to schema instances.
  This keeps the database layer decoupled from the API contract.
* None is returned (not an exception) when a requested resource does not
  exist. The service layer decides what to do with a missing record.

Caller
~~~~~~
Only ``app.services.*`` modules should call functions in this file.
Route files (``app.api.routes.*``) must never import from here directly.

TODO(pranav/pannaga): once Alembic is set up, remove the ``create_tables()``
    call from app startup and rely solely on ``alembic upgrade head``.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.database.models import Resource
from sqlalchemy import func, select
from sqlalchemy.orm import Session


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _utcnow() -> datetime:
    """Return the current UTC datetime (timezone-aware)."""
    return datetime.now(tz=timezone.utc)


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------


def create_resource(
    db: Session,
    *,
    resource_id: str,
    source_type: str,
    status: str = "pending",
    source_url: str | None = None,
    filename: str | None = None,
    title: str | None = None,
    summary: str | None = None,
) -> Resource:
    """
    Insert a new resource row and return the ORM instance.

    Parameters
    ----------
    db:
        Active SQLAlchemy session.
    resource_id:
        Pre-generated unique identifier (e.g. "res_<ulid>"). The service
        layer is responsible for generating this before calling here.
    source_type:
        "url" or "pdf". Validated by the service before being passed in.
    status:
        Initial status. Defaults to "pending".
    source_url:
        Original URL for URL uploads; ``None`` for PDFs.
    filename:
        Original filename for PDF uploads; ``None`` for URLs.
    title:
        Optional initial title. Usually ``None`` at creation time.
    summary:
        Optional summary. Always ``None`` at creation time.

    Returns
    -------
    Resource
        The newly created and committed ORM instance.

    TODO(pannaga): add resource_id generation here using ULID once the
        dependency is available:
            from ulid import ULID
            resource_id = f"res_{ULID()}"
    """
    now = _utcnow()
    resource = Resource(
        resource_id=resource_id,
        source_type=source_type,
        status=status,
        source_url=source_url,
        filename=filename,
        title=title,
        summary=summary,
        created_at=now,
        updated_at=now,
    )
    db.add(resource)
    db.commit()
    db.refresh(resource)
    return resource


# ---------------------------------------------------------------------------
# Read — list
# ---------------------------------------------------------------------------


def list_resources(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 20,
    status: str | None = None,
    source_type: str | None = None,
) -> tuple[list[Resource], int]:
    """
    Return a paginated list of resources and the total matching count.

    Parameters
    ----------
    db:
        Active SQLAlchemy session.
    page:
        1-indexed page number.
    page_size:
        Number of rows per page (1–100).
    status:
        Optional status filter string (e.g. "ready").
    source_type:
        Optional source_type filter string (e.g. "url").

    Returns
    -------
    tuple[list[Resource], int]
        ``(items, total)`` where ``total`` is the count across all pages.

    TODO(pannaga): add ``order_by`` (e.g. created_at DESC) once the
        archive page implements sorting controls.
    """
    stmt = select(Resource)

    if status is not None:
        stmt = stmt.where(Resource.status == status)

    if source_type is not None:
        stmt = stmt.where(Resource.source_type == source_type)

    # Total count before pagination
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total: int = db.execute(count_stmt).scalar_one()

    # Newest first — stable, predictable ordering for pagination
    stmt = stmt.order_by(Resource.created_at.desc())

    # Apply pagination
    offset = (page - 1) * page_size
    stmt = stmt.offset(offset).limit(page_size)

    items: list[Resource] = list(db.execute(stmt).scalars().all())
    return items, total


# ---------------------------------------------------------------------------
# Read — single
# ---------------------------------------------------------------------------


def get_resource(db: Session, resource_id: str) -> Resource | None:
    """
    Return a single resource by primary key, or ``None`` if not found.

    Parameters
    ----------
    db:
        Active SQLAlchemy session.
    resource_id:
        The resource's primary key string.

    Returns
    -------
    Resource | None
        The ORM instance, or ``None`` if the row does not exist.
    """
    return db.get(Resource, resource_id)


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------


def update_resource_status(
    db: Session,
    resource_id: str,
    *,
    status: str,
    title: str | None = None,
    summary: str | None = None,
    error_message: str | None = None,
    completed_at: datetime | None = None,
) -> Resource | None:
    """
    Update a resource's status and pipeline output fields.

    Used by the service layer to mark a resource as "ready" or "failed"
    after the AI pipeline finishes, and to record the extracted title,
    AI-generated summary, and any error context.

    Parameters
    ----------
    db:
        Active SQLAlchemy session.
    resource_id:
        Primary key of the resource to update.
    status:
        New status string ("processing" | "ready" | "failed").
    title:
        If provided, overwrites the current title. Pass ``None`` to leave
        the existing title unchanged.
    summary:
        If provided, overwrites the current summary. Pass ``None`` to leave
        the existing summary unchanged.
    error_message:
        Human-readable failure reason. Set when status="failed".
        Must be safe for logging — no secrets, no raw stack traces.
    completed_at:
        UTC timestamp marking when pipeline processing finished.
        If not provided and status is "ready" or "failed", defaults to
        ``_utcnow()`` automatically.

    Returns
    -------
    Resource | None
        The updated ORM instance, or ``None`` if the resource was not found.
    """
    resource = db.get(Resource, resource_id)
    if resource is None:
        return None

    resource.status = status
    resource.updated_at = _utcnow()

    if title is not None:
        resource.title = title

    if summary is not None:
        resource.summary = summary

    if error_message is not None:
        resource.error_message = error_message

    # Set completed_at when pipeline finishes (either terminal state)
    if status in ("ready", "failed"):
        resource.completed_at = completed_at if completed_at is not None else _utcnow()

    db.commit()
    db.refresh(resource)
    return resource


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------


def delete_resource(db: Session, resource_id: str) -> bool:
    """
    Delete a resource row by primary key.

    Parameters
    ----------
    db:
        Active SQLAlchemy session.
    resource_id:
        Primary key of the resource to delete.

    Returns
    -------
    bool
        ``True`` if the row was found and deleted; ``False`` if it did not
        exist. The service layer maps ``False`` to a 404 HTTPException.

    Note: deleting the metadata row here does NOT remove ChromaDB vectors.
    The service layer is responsible for calling Yeshneil's retrieval module
    to delete associated vectors before (or after) calling this function.

    TODO(pannaga + yeshneil): coordinate deletion order — delete ChromaDB
        vectors first (idempotent), then delete the SQLite row, so a partial
        failure leaves the DB row intact and the operation can be retried.
    """
    resource = db.get(Resource, resource_id)
    if resource is None:
        return False

    db.delete(resource)
    db.commit()
    return True

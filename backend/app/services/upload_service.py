"""
backend/app/services/upload_service.py
----------------------------------------
Service layer for resource ingestion (POST /upload).

Responsibility
~~~~~~~~~~~~~~
This module owns the business logic for creating a new resource record
and scheduling background AI processing. Routes call this module; routes
never contain ingestion logic or database calls themselves.

Current state: DB-backed, pipeline placeholder
    Both functions write a real Resource row to SQLite (status="processing")
    and schedule a background task that logs the processing intent.
    The actual AI pipeline call will replace the placeholder once
    Sriganesh's code is ready.

Resource ID generation
~~~~~~~~~~~~~~~~~~~~~~
IDs are generated using Python's built-in ``uuid`` module until the ULID
dependency is available. Format: "res_<uuid4-no-hyphens>".

Integration points
~~~~~~~~~~~~~~~~~~
    1. create_url_upload  → crud.create_resource → _schedule_processing
    2. create_pdf_upload  → crud.create_resource → _schedule_processing
    3. _run_background_processing → [AI pipeline placeholder]
"""

from __future__ import annotations

import logging
import uuid

from app.database import crud
from app.schemas import ResourceStatus, SourceType, UploadResponse
from fastapi import BackgroundTasks
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _new_resource_id() -> str:
    """Generate a new resource identifier. Format: res_<uuid4_hex>."""
    return f"res_{uuid.uuid4().hex}"


# ---------------------------------------------------------------------------
# Background processing — integration point for Sriganesh's AI pipeline
# ---------------------------------------------------------------------------


def _run_background_processing(
    resource_id: str,
    source_type: str,
    source_url: str | None,
    file_bytes: bytes | None,
    filename: str | None,
) -> None:
    """
    Background task: run the AI pipeline for a single resource.

    This function is scheduled via FastAPI ``BackgroundTasks`` and runs
    after the HTTP 202 response is returned to the client.

    Current state: PLACEHOLDER
        Logs the processing intent but does not call the actual AI pipeline.
        When Sriganesh's pipeline is ready, replace the placeholder body
        with the real pipeline call.

    Integration (when ready)::

        from app.ai.pipeline import process_resource  # Sriganesh's code
        from app.database.session import SessionLocal

        db = SessionLocal()
        try:
            result = process_resource(
                resource_id=resource_id,
                source_type=source_type,
                source_url=source_url,
                file_bytes=file_bytes,
                filename=filename,
            )
            # On success: update resource to "ready" with title/summary
            crud.update_resource_status(
                db, resource_id,
                status="ready",
                title=result.metadata.title,
                summary=result.metadata.summary,
            )
            # Hand off chunks to Yeshneil's retrieval layer
            # retrieval.store_chunks(result.chunks)
        except Exception as exc:
            crud.update_resource_status(
                db, resource_id,
                status="failed",
                error_message=str(exc),
            )
        finally:
            db.close()

    Parameters
    ----------
    resource_id:
        The resource to process.
    source_type:
        "url" or "pdf".
    source_url:
        URL to scrape (for URL uploads). None for PDFs.
    file_bytes:
        Raw PDF content (for PDF uploads). None for URLs.
    filename:
        Original PDF filename. None for URLs.
    """
    # --- PLACEHOLDER: log intent, do not process ---
    logger.info(
        "Background processing scheduled for resource_id=%s source_type=%s "
        "(AI pipeline not yet wired — resource will remain in 'processing' status)",
        resource_id,
        source_type,
    )

    # TODO(pannaga + sriganesh): replace the log above with the real
    # pipeline call once backend/app/ai is ready. See integration
    # example in the docstring above and docs/backend_ai_contract.md.


def _schedule_processing(
    background_tasks: BackgroundTasks,
    resource_id: str,
    source_type: str,
    source_url: str | None = None,
    file_bytes: bytes | None = None,
    filename: str | None = None,
) -> None:
    """
    Schedule background AI processing via FastAPI BackgroundTasks.

    Called by create_url_upload / create_pdf_upload after the DB row is
    committed. The HTTP 202 response is returned immediately; this task
    runs in the background.
    """
    background_tasks.add_task(
        _run_background_processing,
        resource_id=resource_id,
        source_type=source_type,
        source_url=source_url,
        file_bytes=file_bytes,
        filename=filename,
    )
    logger.info(
        "Background processing task queued for resource_id=%s",
        resource_id,
    )


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------


def create_url_upload(
    db: Session,
    url: str,
    background_tasks: BackgroundTasks,
) -> UploadResponse:
    """
    Persist a new URL resource record, schedule processing, return 202 payload.

    Parameters
    ----------
    db:
        Active SQLAlchemy session, provided by the route via Depends(get_db).
    url:
        Validated HTTP/HTTPS URL string. The route validates format via
        UrlUploadRequest before calling here.
    background_tasks:
        FastAPI BackgroundTasks instance for scheduling async processing.

    Returns
    -------
    UploadResponse
        Immediately returned 202 payload. Status is ``processing``.
        The resource is NOT yet queryable via chat — poll
        GET /archive/{resource_id} until status is ``ready``.
    """
    resource_id = _new_resource_id()

    resource = crud.create_resource(
        db,
        resource_id=resource_id,
        source_type=SourceType.URL.value,
        status=ResourceStatus.PROCESSING.value,
        source_url=url,
        title=None,    # populated by AI pipeline
        summary=None,  # populated by AI pipeline
    )
    logger.info(
        "Resource created: resource_id=%s source_type=url",
        resource_id,
    )

    # Schedule background AI processing (placeholder for now)
    _schedule_processing(
        background_tasks=background_tasks,
        resource_id=resource_id,
        source_type=SourceType.URL.value,
        source_url=url,
    )

    return UploadResponse(
        resource_id=resource.resource_id,
        status=ResourceStatus(resource.status),
        source_type=SourceType(resource.source_type),
        title=resource.title,
        summary=resource.summary,
        created_at=resource.created_at,
    )


def create_pdf_upload(
    db: Session,
    filename: str | None,
    file_bytes: bytes,
    background_tasks: BackgroundTasks,
) -> UploadResponse:
    """
    Persist a new PDF resource record, schedule processing, return 202 payload.

    Parameters
    ----------
    db:
        Active SQLAlchemy session, provided by the route via Depends(get_db).
    filename:
        Original filename from the UploadFile. Used as a provisional title
        until the AI pipeline extracts a better one. May be ``None``.
    file_bytes:
        Raw PDF file content read by the route. Passed to the background
        processing task for hand-off to Sriganesh's AI pipeline.
    background_tasks:
        FastAPI BackgroundTasks instance for scheduling async processing.

    Returns
    -------
    UploadResponse
        Immediately returned 202 payload. Status is ``processing``.
    """
    resource_id = _new_resource_id()

    resource = crud.create_resource(
        db,
        resource_id=resource_id,
        source_type=SourceType.PDF.value,
        status=ResourceStatus.PROCESSING.value,
        filename=filename,
        title=filename,  # provisional; overwritten by AI extraction
        summary=None,
    )
    logger.info(
        "Resource created: resource_id=%s source_type=pdf filename=%s file_size_bytes=%d",
        resource_id,
        filename or "<unnamed>",
        len(file_bytes),
    )

    # Schedule background AI processing (placeholder for now)
    _schedule_processing(
        background_tasks=background_tasks,
        resource_id=resource_id,
        source_type=SourceType.PDF.value,
        file_bytes=file_bytes,
        filename=filename,
    )

    return UploadResponse(
        resource_id=resource.resource_id,
        status=ResourceStatus(resource.status),
        source_type=SourceType(resource.source_type),
        title=resource.title,
        summary=resource.summary,
        created_at=resource.created_at,
    )

"""
backend/app/api/routes/upload.py
---------------------------------
POST /upload — Ingest a URL or PDF document.

Route responsibility
~~~~~~~~~~~~~~~~~~~~
* Parse and validate ``multipart/form-data`` fields.
* Enforce the "exactly one of url/file" constraint.
* Validate URL format via ``UrlUploadRequest``.
* Validate PDF MIME type.
* Inject a database session via ``Depends(get_db)``.
* Raise domain exceptions (UploadValidationError, UnsupportedUploadTypeError)
  for known validation failures — the global handler converts them to HTTP.
* Delegate all business logic to ``upload_service``.
* Return the service result directly.

What does NOT live here
~~~~~~~~~~~~~~~~~~~~~~~
* No resource ID generation.
* No database calls — only the session is obtained here.
* No AI pipeline invocations.
* No repeated error-dict construction — that is done once in handlers.py.

Design note on UploadFile
~~~~~~~~~~~~~~~~~~~~~~~~~
FastAPI resolves ``UploadFile`` parameters directly from the multipart form;
they cannot be nested inside a Pydantic model. The route accepts
``url: str | None`` and ``file: UploadFile | None`` as separate Form/File
parameters, validates them, then passes the session and validated data to
the appropriate service function.
"""

from __future__ import annotations

from app.database.session import get_db
from app.exceptions import UnsupportedUploadTypeError, UploadValidationError
from app.schemas import UploadResponse, UrlUploadRequest
from app.services import upload_service
from fastapi import APIRouter, BackgroundTasks, Depends, Form, UploadFile, status
from pydantic import ValidationError
from sqlalchemy.orm import Session

router = APIRouter()


@router.post(
    "/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Ingest a URL or PDF",
    description=(
        "Accepts either a public URL (form field `url`) or a PDF file "
        "(form field `file`). Exactly one must be provided. "
        "Returns 202 Accepted immediately; AI processing is asynchronous. "
        "Poll GET /archive/{resource_id} for status updates."
    ),
    tags=["upload"],
)
async def upload_resource(
    background_tasks: BackgroundTasks,
    url: str | None = Form(
        default=None,
        description="Public HTTP/HTTPS URL to ingest. Mutually exclusive with `file`.",
    ),
    file: UploadFile | None = None,
    db: Session = Depends(get_db),
) -> UploadResponse:
    """
    Validate input, inject db session, delegate to upload_service.

    Validation errors raise domain exceptions (UploadValidationError,
    UnsupportedUploadTypeError) which the global handler converts to
    HTTP 400 / 415 with ErrorResponse bodies.

    All business logic (ID generation, DB write, AI pipeline trigger) lives
    in upload_service, not here.
    """
    has_url = url is not None and url.strip() != ""
    has_file = file is not None

    # --- Guard: exactly one source -------------------------------------------
    if has_url and has_file:
        raise UploadValidationError(
            "Provide exactly one of 'url' or 'file', not both."
        )

    if not has_url and not has_file:
        raise UploadValidationError("Provide exactly one of 'url' or 'file'.")

    # --- URL path ------------------------------------------------------------
    if has_url:
        try:
            validated = UrlUploadRequest(url=url)  # type: ignore[arg-type]
        except ValidationError:
            raise UploadValidationError(
                "The provided URL is not a valid HTTP/HTTPS URL.",
                details={"field": "url", "value": url},
            )

        return upload_service.create_url_upload(
            db=db,
            url=str(validated.url),
            background_tasks=background_tasks,
        )

    # --- PDF path ------------------------------------------------------------
    assert file is not None  # narrowing for type-checkers

    if file.content_type != "application/pdf":
        raise UnsupportedUploadTypeError(received_mime_type=file.content_type)

    # Read file bytes here (route responsibility) so the service layer
    # receives raw bytes without needing FastAPI UploadFile awareness.
    file_bytes = await file.read()

    return upload_service.create_pdf_upload(
        db=db,
        filename=file.filename,
        file_bytes=file_bytes,
        background_tasks=background_tasks,
    )

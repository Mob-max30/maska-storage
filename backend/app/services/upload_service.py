"""
backend/app/services/upload_service.py
--------------------------------------

Service layer for resource ingestion.

Responsibilities
----------------
• Create Resource records in SQLite.
• Schedule background AI processing.
• Execute the AI pipeline.
• Store embeddings in ChromaDB.
• Update resource status.
• Handle processing failures.

The route layer should NEVER call the AI pipeline directly.
"""

from __future__ import annotations

import logging
import os
import tempfile
import uuid

from fastapi import BackgroundTasks
from sqlalchemy.orm import Session

from app.database import SessionLocal, crud
from app.schemas import (
    ResourceStatus,
    SourceType,
    UploadResponse,
)

from app.ai.pipeline import AIPipeline
from app.ai.retrieval.rag_retrieval import (
    store_pipeline_result,
)

logger = logging.getLogger(__name__)

###############################################################################
# Singleton AI Pipeline
###############################################################################

_pipeline: AIPipeline | None = None


def get_pipeline() -> AIPipeline:
    """
    Returns a singleton AIPipeline.

    Prevents repeatedly loading:

    • Embedding model
    • Summarizer
    • Metadata generator
    • PDF parser
    • Web scraper

    for every upload.
    """

    global _pipeline

    if _pipeline is None:

        logger.info(
            "Initializing AI Pipeline..."
        )

        _pipeline = AIPipeline()

        logger.info(
            "AI Pipeline initialized successfully."
        )

    return _pipeline


###############################################################################
# Resource ID Generator
###############################################################################

def _new_resource_id() -> str:
    """
    Generate a unique resource ID.

    Format:

        res_<uuid4>

    Example:

        res_7fa6bca31c6f4cf49c18c8ec65d8352a
    """

    return f"res_{uuid.uuid4().hex}"


###############################################################################
# Temporary PDF Utilities
###############################################################################

def _create_temp_pdf(
    file_bytes: bytes,
) -> str:
    """
    Creates a temporary PDF on disk.

    Sriganesh's PDF parser expects a file path,
    not raw bytes.

    Returns
    -------
    str
        Path to the temporary PDF.
    """

    temp = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=".pdf",
    )

    temp.write(file_bytes)

    temp.flush()

    temp.close()

    logger.info(
        "Temporary PDF created: %s",
        temp.name,
    )

    return temp.name


def _cleanup_temp_file(
    path: str | None,
) -> None:
    """
    Delete a temporary file if it exists.
    """

    if not path:
        return

    try:

        if os.path.exists(path):

            os.remove(path)

            logger.info(
                "Deleted temporary file: %s",
                path,
            )

    except Exception:

        logger.exception(
            "Unable to delete temporary file: %s",
            path,
        )


###############################################################################
# Background Task Scheduler
###############################################################################

def _schedule_processing(
    background_tasks: BackgroundTasks,
    resource_id: str,
    source_type: str,
    source_url: str | None = None,
    file_bytes: bytes | None = None,
    filename: str | None = None,
) -> None:
    """
    Schedule asynchronous processing.
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
        "Queued background processing for resource %s",
        resource_id,
    )


###############################################################################
# Upload APIs
#
# create_url_upload()  -> Chunk 3
# create_pdf_upload()  -> Chunk 4
###############################################################################
###############################################################################
# Background Processing
###############################################################################

def _run_background_processing(
    resource_id: str,
    source_type: str,
    source_url: str | None,
    file_bytes: bytes | None,
    filename: str | None,
) -> None:
    """
    Execute the complete AI ingestion pipeline.

        URL / PDF
            ↓
        AI Pipeline
            ↓
        ChromaDB
            ↓
        SQLite
            ↓
          READY
    """

    db = SessionLocal()
    temp_pdf_path: str | None = None

    try:

        logger.info(
            "Starting AI processing for resource %s",
            resource_id,
        )

        pipeline = get_pipeline()

        #######################################################################
        # URL Upload
        #######################################################################

        if source_type == SourceType.URL:

            logger.info(
                "Processing URL: %s",
                source_url,
            )

            pipeline_result = pipeline.process_url(
                url=source_url,
                resource_id=resource_id,
            )

        #######################################################################
        # PDF Upload
        #######################################################################

        elif source_type == SourceType.PDF:

            if file_bytes is None:
                raise ValueError(
                    "PDF upload missing file bytes."
                )

            temp_pdf_path = _create_temp_pdf(
                file_bytes,
            )

            logger.info(
                "Processing PDF: %s",
                filename,
            )

            pipeline_result = pipeline.process_pdf(
                pdf_path=temp_pdf_path,
                resource_id=resource_id,
            )

        #######################################################################
        # Invalid Source
        #######################################################################

        else:

            raise ValueError(
                f"Unsupported source type: {source_type}"
            )

        #######################################################################
        # Store Embeddings
        #######################################################################

        logger.info(
            "Storing embeddings in ChromaDB..."
        )

        store_pipeline_result(
            pipeline_result,
        )

        logger.info(
            "Embeddings stored successfully."
        )

        #######################################################################
        # Extract Metadata
        #######################################################################

        document = pipeline_result.get(
            "document",
            {},
        )
        title = (
            document.get("title")
            or document.get("filename")
            or "Untitled Resource"

)

        summary_data = pipeline_result.get("summary", {})

        summary = (
            summary_data.get("summary", "")
            if isinstance(summary_data, dict)
            else str(summary_data)
                   
        
)

        import os
        print("UPLOAD DB:", os.path.abspath(db.get_bind().url.database))
        
        #######################################################################
        # Update SQLite
        #######################################################################

        crud.update_resource_status(
            db=db,
            resource_id=resource_id,
            status=ResourceStatus.READY.value,
            title=title,
            summary=summary,
)

        logger.info(
            "Resource %s marked READY.",
            resource_id,
        )
        updated = crud.get_resource(db, resource_id)

        print(
            "AFTER UPDATE:",
            updated.status,
            updated.title,
        )

    ###########################################################################
    # Error Handling
    ###########################################################################

    except Exception as exc:

        logger.exception(
            "Pipeline failed for resource %s",
            resource_id,
        )

        try:

            crud.update_resource_status(
                db=db,
                resource_id=resource_id,
                status=ResourceStatus.FAILED.value,
                error_message=str(exc),
            )

        except Exception:

            logger.exception(
                "Failed updating resource status."
            )

    ###########################################################################
    # Cleanup
    ###########################################################################

    finally:

        _cleanup_temp_file(
            temp_pdf_path,
        )

        db.close()

        logger.info(

            "Finished processing resource %s",
            resource_id,
        )
        ###############################################################################
# URL Upload API
###############################################################################

def create_url_upload(
    db: Session,
    background_tasks: BackgroundTasks,
    *,
    url: str,
) -> UploadResponse:
    """
    Create a URL resource and schedule background processing.

    Flow

        URL
         ↓
      SQLite (processing)
         ↓
      Background Task
         ↓
      Return immediately
    """

    logger.info(
        "Received URL upload: %s",
        url,
    )

    resource_id = _new_resource_id()

    resource = crud.create_resource(
        db=db,
        resource_id=resource_id,
        source_type=SourceType.URL,
        status=ResourceStatus.PROCESSING.value,
        source_url=url,
    )

    _schedule_processing(
        background_tasks=background_tasks,
        resource_id=resource_id,
        source_type=SourceType.URL,
        source_url=url,
    )

    logger.info(
        "URL resource %s created successfully.",
        resource_id,
    )

    return UploadResponse(
    resource_id=resource.resource_id,
    status=resource.status,
    source_type=resource.source_type,
    title=resource.title,
    summary=resource.summary,
    created_at=resource.created_at,
)


###############################################################################
# PDF Upload API
###############################################################################

def create_pdf_upload(
    db: Session,
    background_tasks: BackgroundTasks,
    *,
    filename: str,
    file_bytes: bytes,
) -> UploadResponse:
    """
    Create a PDF resource and schedule background processing.

    Flow

        PDF
         ↓
      SQLite (processing)
         ↓
      Background Task
         ↓
      Return immediately
    """

    logger.info(
        "Received PDF upload: %s",
        filename,
    )

    resource_id = _new_resource_id()

    resource = crud.create_resource(
        db=db,
        resource_id=resource_id,
        source_type=SourceType.PDF,
        status=ResourceStatus.PROCESSING.value,
        filename=filename,
    )

    _schedule_processing(
        background_tasks=background_tasks,
        resource_id=resource_id,
        source_type=SourceType.PDF,
        file_bytes=file_bytes,
        filename=filename,
    )

    logger.info(
        "PDF resource %s created successfully.",
        resource_id,
    )

    return UploadResponse(
    resource_id=resource.resource_id,
    status=resource.status,
    source_type=resource.source_type,
    title=resource.title,
    summary=resource.summary,
    created_at=resource.created_at,
)
###############################################################################
# Optional Validation Helpers
###############################################################################

def _validate_url(url: str) -> None:
    """
    Basic validation for URL uploads.
    """

    if not url:
        raise ValueError("URL cannot be empty.")

    url = url.strip()

    if not (
        url.startswith("http://")
        or url.startswith("https://")
    ):
        raise ValueError(
            "URL must start with http:// or https://"
        )


def _validate_pdf(
    filename: str,
    file_bytes: bytes,
) -> None:
    """
    Basic validation for PDF uploads.
    """

    if not filename:
        raise ValueError(
            "Filename cannot be empty."
        )

    if not filename.lower().endswith(".pdf"):
        raise ValueError(
            "Only PDF files are supported."
        )

    if not file_bytes:
        raise ValueError(
            "Uploaded PDF is empty."
        )


###############################################################################
# Convenience Wrapper APIs
#
# These wrappers can be directly used by your FastAPI routes.
###############################################################################

def upload_url(
    db: Session,
    background_tasks: BackgroundTasks,
    url: str,
) -> UploadResponse:
    """
    Validate and enqueue a URL upload.
    """

    _validate_url(url)

    return create_url_upload(
        db=db,
        background_tasks=background_tasks,
        url=url,
    )


def upload_pdf(
    db: Session,
    background_tasks: BackgroundTasks,
    filename: str,
    file_bytes: bytes,
) -> UploadResponse:
    """
    Validate and enqueue a PDF upload.
    """

    _validate_pdf(
        filename=filename,
        file_bytes=file_bytes,
    )

    return create_pdf_upload(
        db=db,
        background_tasks=background_tasks,
        filename=filename,
        file_bytes=file_bytes,
    )


###############################################################################
# End of upload_service.py
###############################################################################

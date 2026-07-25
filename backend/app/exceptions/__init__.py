"""
backend/app/exceptions/__init__.py
------------------------------------
Public re-exports for backend/app/exceptions.

Usage::

    # Raise a domain exception in a service or route:
    from app.exceptions import ResourceNotFoundError, UploadValidationError

    # Pipeline exceptions (raised by service layer during background processing):
    from app.exceptions import PipelineExecutionError, PdfParsingError

    # Build a one-off HTTPException in a route:
    from app.exceptions import http_error
    raise http_error(400, "validation_error", "URL is required.")

    # Register all handlers (done once in main.py):
    from app.exceptions.handlers import (
        maska_exception_handler,
        http_exception_handler,
        validation_exception_handler,
        internal_error_handler,
    )
"""

from app.exceptions.handlers import http_error
from app.exceptions.types import (
    EmbeddingGenerationError,
    InvalidUrlError,
    MaskaBaseError,
    PdfParsingError,
    PipelineExecutionError,
    ResourceNotFoundError,
    ServiceError,
    TextExtractionError,
    UnsupportedUploadTypeError,
    UploadValidationError,
)

__all__ = [
    # Domain exceptions — existing
    "MaskaBaseError",
    "ResourceNotFoundError",
    "UploadValidationError",
    "UnsupportedUploadTypeError",
    "ServiceError",
    # Domain exceptions — pipeline
    "InvalidUrlError",
    "PdfParsingError",
    "TextExtractionError",
    "EmbeddingGenerationError",
    "PipelineExecutionError",
    # Route helper
    "http_error",
]

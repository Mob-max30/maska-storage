"""
backend/app/exceptions/types.py
---------------------------------
Lightweight domain exception classes for MaskaStorage.

Design principles
~~~~~~~~~~~~~~~~~
* Small — only the exceptions actually needed by the current code.
* No FastAPI imports — these are pure Python; handlers translate them
  to HTTP responses (see handlers.py).
* Services raise these; routes catch them only via global handlers
  registered in main.py (so routes stay thin).
* Every class carries ``code`` (machine-readable) and ``message``
  (human-readable, safe to surface in UI) that map directly to
  ErrorDetail fields.

Error code catalogue
~~~~~~~~~~~~~~~~~~~~
    not_found              Resource does not exist.
    validation_error       Input failed business-level validation.
    unsupported_type       Upload source type is not accepted.
    service_error          Service-layer failure (DB write failed, etc.).
    invalid_url            URL could not be reached or is malformed (HTTP 400).
    pdf_parsing_error      PDF file could not be parsed or is corrupted (HTTP 500).
    text_extraction_error  Text extraction from source content failed (HTTP 500).
    embedding_error        Embedding generation failed (HTTP 500).
    pipeline_error         General AI pipeline execution failure (HTTP 500).
    internal_error         Catch-all for unexpected exceptions (HTTP 500).
"""

from __future__ import annotations

from typing import Any


class MaskaBaseError(Exception):
    """Base class for all MaskaStorage domain exceptions."""

    code: str = "internal_error"
    http_status: int = 500

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.details = details


class ResourceNotFoundError(MaskaBaseError):
    """
    Raised when a requested resource_id does not exist in the database.

    Translated to HTTP 404 by the global exception handler.
    """

    code = "not_found"
    http_status = 404

    def __init__(self, resource_id: str) -> None:
        super().__init__(
            message=f"No resource found with id '{resource_id}'.",
            details={"resource_id": resource_id},
        )
        self.resource_id = resource_id


class UploadValidationError(MaskaBaseError):
    """
    Raised when upload input fails business-level validation.

    Examples:
      - Both url and file provided simultaneously.
      - Neither url nor file provided.
      - Invalid URL format.
      - Uploaded file is not a PDF.

    Translated to HTTP 400 by the global exception handler.
    """

    code = "validation_error"
    http_status = 400

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message=message, details=details)


class UnsupportedUploadTypeError(MaskaBaseError):
    """
    Raised when the uploaded file's MIME type is not accepted.

    Translated to HTTP 415 Unsupported Media Type by the global handler.
    """

    code = "unsupported_type"
    http_status = 415

    def __init__(self, received_mime_type: str | None) -> None:
        super().__init__(
            message=(
                f"Only PDF files are accepted. "
                f"Received: {received_mime_type or 'unknown'}."
            ),
            details={"received_mime_type": received_mime_type},
        )


class ServiceError(MaskaBaseError):
    """
    Raised when a service-layer operation fails (e.g. DB write error,
    constraint violation, unexpected state).

    Translated to HTTP 500 by the global exception handler.
    """

    code = "service_error"
    http_status = 500

    def __init__(
        self,
        message: str = "An internal service error occurred.",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message=message, details=details)


# ---------------------------------------------------------------------------
# Pipeline exceptions — raised by the service layer when background
# AI processing fails. These map to resource status="failed" and are
# logged server-side. They are NOT returned as HTTP errors to the
# upload caller (upload returns 202 before processing starts), but the
# global handler will catch them if they propagate unexpectedly.
# ---------------------------------------------------------------------------


class InvalidUrlError(MaskaBaseError):
    """
    Raised when a URL cannot be reached, returns a non-200 status,
    or is otherwise unsuitable for content extraction.

    Used during the extraction stage of the AI pipeline.
    HTTP 400 — the user supplied an invalid or unreachable URL.
    """

    code = "invalid_url"
    http_status = 400

    def __init__(
        self,
        url: str,
        reason: str = "The URL could not be reached or returned an error.",
    ) -> None:
        super().__init__(
            message=f"Invalid or unreachable URL: {reason}",
            details={"url": url},
        )
        self.url = url


class PdfParsingError(MaskaBaseError):
    """
    Raised when a PDF file cannot be parsed — corrupted, password-protected,
    or otherwise unreadable.

    Used during the extraction stage of the AI pipeline.
    """

    code = "pdf_parsing_error"
    http_status = 500

    def __init__(
        self,
        resource_id: str,
        reason: str = "The PDF file could not be parsed.",
    ) -> None:
        super().__init__(
            message=f"PDF parsing failed: {reason}",
            details={"resource_id": resource_id},
        )
        self.resource_id = resource_id


class TextExtractionError(MaskaBaseError):
    """
    Raised when text extraction from the source content fails — e.g.
    the URL returned no usable text, or the PDF pages produced no
    extractable characters.

    Used during the extraction/cleaning stage of the AI pipeline.
    """

    code = "text_extraction_error"
    http_status = 500

    def __init__(
        self,
        resource_id: str,
        reason: str = "No text could be extracted from the source content.",
    ) -> None:
        super().__init__(
            message=f"Text extraction failed: {reason}",
            details={"resource_id": resource_id},
        )
        self.resource_id = resource_id


class EmbeddingGenerationError(MaskaBaseError):
    """
    Raised when embedding generation fails — e.g. the embedding model
    is unavailable, returns an error, or produces invalid output.

    Used during the embedding stage of the AI pipeline.
    """

    code = "embedding_error"
    http_status = 500

    def __init__(
        self,
        resource_id: str,
        reason: str = "Embedding generation failed.",
    ) -> None:
        super().__init__(
            message=f"Embedding generation failed: {reason}",
            details={"resource_id": resource_id},
        )
        self.resource_id = resource_id


class PipelineExecutionError(MaskaBaseError):
    """
    General-purpose AI pipeline failure — used when the error does not
    fit a more specific category, or when the pipeline catches an
    unexpected exception internally.

    The ``stage`` field indicates which pipeline stage failed.
    The service layer uses this to set resource status="failed" and
    record the error_message for debugging.
    """

    code = "pipeline_error"
    http_status = 500

    def __init__(
        self,
        resource_id: str,
        stage: str = "unknown",
        reason: str = "An error occurred during AI processing.",
    ) -> None:
        super().__init__(
            message=f"Pipeline failed at stage '{stage}': {reason}",
            details={"resource_id": resource_id, "stage": stage},
        )
        self.resource_id = resource_id
        self.stage = stage

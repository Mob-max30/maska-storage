"""
backend/app/exceptions/handlers.py
-------------------------------------
FastAPI exception handlers that ensure every error response — regardless of
origin — is serialised as the standard ErrorResponse envelope:

    {
      "error": {
        "code":    "<machine-readable string>",
        "message": "<human-readable string safe for the UI>",
        "details": <object or null>
      }
    }

Handlers registered here (in main.py)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    MaskaBaseError          → HTTP status from exception.http_status
    HTTPException           → preserves the status code; normalises the detail
                              field into the ErrorResponse shape if it is not
                              already in that shape.
    RequestValidationError  → 422 with structured field-level error list
    Exception               → 500 catch-all (never leaks stack traces)

Why normalise HTTPException?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
FastAPI already raises HTTPException for many built-in cases (e.g. 405
Method Not Allowed, 404 from path matching) and some routes still raise it
directly. Without this handler, those responses use FastAPI's default
``{"detail": ...}`` shape, which differs from ErrorResponse. This handler
re-wraps the detail so every 4xx/5xx uses the same envelope.

Helpers
~~~~~~~
``http_error(status_code, code, message, details)`` — a thin convenience
function that routes import to raise a normalised HTTPException without
repeating the dict structure. Routes that need to raise known errors should
prefer the domain exception classes from types.py; this helper is for the
remaining one-off cases.
"""

from __future__ import annotations

import logging
from typing import Any

from app.exceptions.types import MaskaBaseError
from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helper used by routes for one-off HTTPException raises
# ---------------------------------------------------------------------------


def http_error(
    status_code: int,
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> HTTPException:
    """
    Build an HTTPException whose ``detail`` is already in ErrorResponse shape.

    Usage in a route::

        from app.exceptions.handlers import http_error

        raise http_error(400, "validation_error", "URL is required.")

    Prefer raising domain exception types (ResourceNotFoundError, etc.) when
    the error is predictable — use this helper only for truly one-off cases
    where creating a new exception class would be over-engineering.
    """
    return HTTPException(
        status_code=status_code,
        detail={
            "error": {
                "code": code,
                "message": message,
                "details": details,
            }
        },
    )


# ---------------------------------------------------------------------------
# Internal helper — build the JSON body
# ---------------------------------------------------------------------------


def _error_body(
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> dict:
    return {"error": {"code": code, "message": message, "details": details}}


# ---------------------------------------------------------------------------
# Handler: domain exceptions (MaskaBaseError subclasses)
# ---------------------------------------------------------------------------


async def maska_exception_handler(
    request: Request, exc: MaskaBaseError
) -> JSONResponse:
    """
    Translate any MaskaBaseError subclass into an ErrorResponse JSON response.

    The HTTP status code comes from ``exc.http_status`` so each exception
    class controls its own status without the handler needing to know the
    mapping.
    """
    logger.warning(
        "Domain error on %s %s: [%s] %s",
        request.method,
        request.url.path,
        exc.code,
        exc.message,
    )
    return JSONResponse(
        status_code=exc.http_status,
        content=_error_body(exc.code, exc.message, exc.details),
    )


# ---------------------------------------------------------------------------
# Handler: FastAPI/Starlette HTTPException
# ---------------------------------------------------------------------------


async def http_exception_handler(
    request: Request, exc: HTTPException
) -> JSONResponse:
    """
    Normalise any HTTPException detail into the ErrorResponse envelope.

    If the ``detail`` is already in ErrorResponse shape (i.e. a dict with
    an ``"error"`` key containing ``"code"`` and ``"message"``), it is
    passed through unchanged. Otherwise the raw detail value is wrapped
    under a generic ``"http_error"`` code so the frontend always gets the
    same top-level shape.
    """
    detail = exc.detail

    # Already in ErrorResponse shape — pass through as-is.
    if (
        isinstance(detail, dict)
        and "error" in detail
        and isinstance(detail["error"], dict)
        and "code" in detail["error"]
        and "message" in detail["error"]
    ):
        return JSONResponse(status_code=exc.status_code, content=detail)

    # Starlette/FastAPI default detail is usually a plain string.
    message = str(detail) if detail is not None else "An error occurred."
    logger.warning(
        "HTTP error on %s %s: status=%d message=%s",
        request.method,
        request.url.path,
        exc.status_code,
        message,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_body("http_error", message),
    )


# ---------------------------------------------------------------------------
# Handler: Pydantic/FastAPI RequestValidationError (→ 422)
# ---------------------------------------------------------------------------


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """
    Translate Pydantic validation errors (FastAPI 422) into ErrorResponse.

    Each Pydantic error is condensed to:
        {"field": <dot-joined location>, "message": <error msg>}

    The frontend can inspect the ``details.errors`` list to highlight
    specific form fields.

    Examples of fields that produce 422:
        - ChatRequest.question is empty or whitespace-only.
        - ChatRequest.resource_ids is an empty list.
        - Query param ``page`` is not an integer.
    """
    errors = [
        {
            "field": ".".join(str(loc) for loc in err["loc"]),
            "message": err["msg"],
        }
        for err in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content=_error_body(
            code="validation_error",
            message="Request validation failed. Check the 'details.errors' list.",
            details={"errors": errors},
        ),
    )


# ---------------------------------------------------------------------------
# Handler: catch-all for unexpected exceptions (→ 500)
# ---------------------------------------------------------------------------


async def internal_error_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """
    Catch-all for any unhandled exception.

    Logs the full traceback server-side; returns a generic 500 body to the
    client that never exposes internal details or stack traces.
    """
    logger.exception(
        "Unhandled exception on %s %s",
        request.method,
        request.url.path,
        exc_info=exc,
    )
    return JSONResponse(
        status_code=500,
        content=_error_body(
            code="internal_error",
            message="An unexpected error occurred. Please try again later.",
        ),
    )

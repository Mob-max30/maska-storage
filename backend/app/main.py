"""
backend/app/main.py
--------------------
FastAPI application entry point for MaskaStorage.

Responsibilities of this file:
  - Create the FastAPI app instance with a lifespan handler.
  - Create SQLite tables on startup (development convenience).
  - Optionally seed mock resources on first run if the DB is empty.
  - Register CORS middleware for local frontend development.
  - Include all API routers.
  - Nothing else — no business logic, no AI calls.

Running locally::

    cd backend
    uvicorn app.main:app --reload

Interactive API docs available at:
    http://localhost:8000/docs   (Swagger UI)
    http://localhost:8000/redoc  (ReDoc)

TODO(pranav/pannaga): replace create_tables() startup call with
    ``alembic upgrade head`` in the Docker entrypoint before any
    production deployment. Do not rely on create_all() in production.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.routes import archive, chat, health, upload
from app.core.config import get_settings
from app.database.session import SessionLocal, create_tables
from app.exceptions.handlers import (
    http_exception_handler,
    internal_error_handler,
    maska_exception_handler,
    validation_exception_handler,
)
from app.exceptions.types import MaskaBaseError
from app.services.archive_service import seed_mock_resources

settings = get_settings()

# ---------------------------------------------------------------------------
# Logging — configured once here; all module loggers inherit this.
# Override level via MASKA_LOG_LEVEL env var (e.g. "DEBUG" for verbose output).
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lifespan — runs once on startup and once on shutdown
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan handler.

    Startup:
      1. Create all SQLite tables (idempotent — safe to run on every restart).
      2. Seed two sample resources when the DB is empty, so the frontend
         team always has something to render against. Seeding is skipped if
         any resource row already exists.

    Shutdown:
      Nothing needed for SQLite + synchronous SQLAlchemy.

    TODO(pranav/pannaga): remove create_tables() once Alembic migrations are
        in place. Keep seed_mock_resources() until the AI pipeline is wired
        and real uploads are being made.
    """
    # --- Startup -------------------------------------------------------------
    logger.info(
        "Starting %s v%s (environment=%s)",
        settings.app_name,
        settings.app_version,
        settings.environment,
    )
    create_tables()
    logger.info("Database tables ensured (create_all)")

    if settings.seed_on_startup:
        db = SessionLocal()
        try:
            seed_mock_resources(db)
            logger.info("Seed check complete")
        finally:
            db.close()

    yield  # Application runs here

    # --- Shutdown ------------------------------------------------------------
    logger.info("Shutting down %s", settings.app_name)


# ---------------------------------------------------------------------------
# Application instance
# ---------------------------------------------------------------------------

app = FastAPI(
    title=settings.app_name,
    description=(
        "AI-powered knowledge management platform. "
        "Save URLs and PDFs, ask questions in plain English, "
        "get answers grounded in your own content via RAG."
    ),
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# ---------------------------------------------------------------------------
# Exception handlers — registered before middleware and routers
# ---------------------------------------------------------------------------

# Domain exceptions (ResourceNotFoundError, UploadValidationError, etc.)
app.add_exception_handler(MaskaBaseError, maska_exception_handler)  # type: ignore[arg-type]

# FastAPI/Starlette HTTPException — normalise detail into ErrorResponse shape
app.add_exception_handler(StarletteHTTPException, http_exception_handler)  # type: ignore[arg-type]

# Pydantic RequestValidationError (FastAPI 422)
app.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore[arg-type]

# Catch-all for any unhandled exception (→ 500, never leaks stack traces)
app.add_exception_handler(Exception, internal_error_handler)

# ---------------------------------------------------------------------------
# CORS — origins from centralized settings (override via MASKA_ALLOWED_ORIGINS)
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

# Health — no prefix so GET /health is at the root level
app.include_router(health.router)

# Upload — POST /upload
app.include_router(upload.router)

# Archive — GET /archive, GET /archive/{id}, DELETE /archive/{id}
app.include_router(archive.router)

# Chat — POST /chat
app.include_router(chat.router)

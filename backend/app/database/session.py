"""
backend/app/database/session.py
---------------------------------
SQLAlchemy engine and session factory for SQLite.

Requires: sqlalchemy>=2.0  (pip install sqlalchemy)

Provides:
  - ``engine``        : the SQLAlchemy Engine (call once per process)
  - ``SessionLocal``  : sessionmaker factory — call to get a Session
  - ``get_db()``      : FastAPI dependency that yields a Session and closes it
  - ``create_tables()``: DDL helper — creates all tables that don't yet exist

Database file location
~~~~~~~~~~~~~~~~~~~~~~
The SQLite database is stored at ``./maska_storage.db`` relative to the
working directory the server is launched from (normally ``backend/``).

TODO(pannaga): move the DB path to app.core.config.Settings so it can be
    changed via environment variable (useful for tests and Docker).
    Example:
        DATABASE_URL = settings.database_url  # "sqlite:///./maska_storage.db"

TODO(pranav/pannaga): when migrating to PostgreSQL + pgvector, swap
    DATABASE_URL for a postgres connection string and replace
    ``check_same_thread`` kwarg with connection pool settings.

TODO(pranav/pannaga): add Alembic for schema migrations before any
    production deployment. Do NOT rely on ``create_tables()`` in production.
"""

from __future__ import annotations

from collections.abc import Generator

from app.core.config import get_settings
from app.database.base import Base
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

# Database URL from centralized settings (app.core.config).
# Default: "sqlite:///./maska_storage.db" — override via MASKA_DATABASE_URL env var.
_settings = get_settings()

engine = create_engine(
    _settings.database_url,
    connect_args={"check_same_thread": False} if _settings.database_url.startswith("sqlite") else {},
    echo=False,  # Set to True temporarily to log all SQL for debugging.
)

# ---------------------------------------------------------------------------
# Session factory
# ---------------------------------------------------------------------------

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,  # Avoids lazy-load errors after commit in FastAPI.
)


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that provides a database session per request.

    Yields a Session, then closes it (and rolls back on error) when the
    request completes. Inject via ``Depends(get_db)`` in route functions.

    Usage in a route::

        from app.database.session import get_db
        from sqlalchemy.orm import Session

        def my_route(db: Session = Depends(get_db)):
            ...

    TODO(pannaga): inject this into service functions (not routes directly)
        once the service layer wires up to the database.
    """
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ---------------------------------------------------------------------------
# DDL helper
# ---------------------------------------------------------------------------


def create_tables() -> None:
    """
    Create all tables defined under ``Base.metadata`` if they do not exist.

    Safe to call on every startup during development. In production, use
    Alembic migrations instead.

    TODO(pranav/pannaga): replace this call in main.py with Alembic
        ``alembic upgrade head`` in the Docker entrypoint.
    """
    # Import models here to ensure they are registered on Base.metadata
    # before create_all() is called.
    import app.database.models  # noqa: F401

    Base.metadata.create_all(bind=engine)

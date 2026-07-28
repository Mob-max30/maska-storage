"""
backend/app/database/__init__.py
----------------------------------
Public re-exports for backend/app/database.

Exposes the most commonly needed names so callers can import from a single
stable path instead of individual submodules.

Usage::

    from app.database import Base, engine, SessionLocal, get_db, create_tables
    from app.database import crud
    from app.database.models import Resource

Requires: sqlalchemy>=2.0  (pip install sqlalchemy)
"""

from app.database import crud
from app.database.base import Base
from app.database.models import Resource
from app.database.session import SessionLocal, create_tables, engine, get_db

__all__ = [
    # Base & engine
    "Base",
    "engine",
    "SessionLocal",
    # Dependency
    "get_db",
    # DDL helper
    "create_tables",
    # ORM model
    "Resource",
    # CRUD module (import as `crud.create_resource(...)` etc.)
    "crud",
]

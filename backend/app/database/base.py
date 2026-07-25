"""
backend/app/database/base.py
------------------------------
SQLAlchemy declarative base shared by all ORM models.

Requires: sqlalchemy>=2.0  (pip install sqlalchemy)

All model files must import ``Base`` from here — never create a second
DeclarativeBase. This ensures ``Base.metadata`` sees every table and
``create_all()`` works correctly.

Usage::

    from app.database.base import Base

    class MyModel(Base):
        __tablename__ = "my_table"
        ...
"""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """
    Shared SQLAlchemy 2.x declarative base.

    Inherit from this class (not from ``sqlalchemy.orm.Base``) in every
    ORM model in this application.

    TODO(pranav/pannaga): When Alembic is added, point env.py at this Base:
        from app.database.base import Base
        target_metadata = Base.metadata
    """
    pass

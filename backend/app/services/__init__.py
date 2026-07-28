"""
backend/app/services/__init__.py
----------------------------------
Public re-exports for backend/app/services.

Import from here inside routes and any future integration code rather
than from individual service submodules. Keeps import paths short and
makes reorganisation transparent to callers.

Usage::

    from app.services import upload_service, archive_service, chat_service
"""

from app.services import archive_service, chat_service, upload_service

__all__ = [
    "upload_service",
    "archive_service",
    "chat_service",
]

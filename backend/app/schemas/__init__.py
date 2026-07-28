"""
__init__.py
-----------
Public re-exports for backend/app/schemas.

Import from this module inside routes and services rather than from
individual submodules. This keeps import paths short and makes future
reorganisation transparent to callers.

Usage::

    from app.schemas import (
        SourceType,
        ResourceStatus,
        ErrorResponse,
        HealthResponse,
        UrlUploadRequest,
        UploadResponse,
        ArchiveItem,
        ArchiveItemDetail,
        ArchiveListResponse,
        DeleteResourceResponse,
        ChatRequest,
        CitationSnippet,
        ChatResponse,
    )
"""

from app.schemas.archive import (
    ArchiveItem,
    ArchiveItemDetail,
    ArchiveListResponse,
    DeleteResourceResponse,
)
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    CitationSnippet,
)
from app.schemas.common import (
    ErrorDetail,
    ErrorResponse,
    ResourceStatus,
    SourceType,
)
from app.schemas.health import HealthResponse
from app.schemas.pipeline import (
    PipelineChunk,
    PipelineFailure,
    PipelineMetadata,
    PipelineResult,
    PipelineStage,
)
from app.schemas.upload import (
    UploadResponse,
    UrlUploadRequest,
)

__all__ = [
    # common
    "SourceType",
    "ResourceStatus",
    "ErrorDetail",
    "ErrorResponse",
    # health
    "HealthResponse",
    # upload
    "UrlUploadRequest",
    "UploadResponse",
    # archive
    "ArchiveItem",
    "ArchiveItemDetail",
    "ArchiveListResponse",
    "DeleteResourceResponse",
    # chat
    "ChatRequest",
    "CitationSnippet",
    "ChatResponse",
    # pipeline contract (internal — not API schemas)
    "PipelineChunk",
    "PipelineMetadata",
    "PipelineResult",
    "PipelineFailure",
    "PipelineStage",
]

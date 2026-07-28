"""
backend/app/core/config.py
----------------------------
Centralized application settings powered by pydantic-settings.

All configuration values live here. Modules import ``get_settings()``
instead of hardcoding values. Environment variables override defaults —
useful for Docker, CI, and production without touching code.

Environment variable names are derived from field names (case-insensitive)
with an optional ``MASKA_`` prefix:
    MASKA_DATABASE_URL=sqlite:///./prod.db
    MASKA_LLM_API_KEY=sk-...
    MASKA_ENVIRONMENT=production

Usage::

    from app.core.config import get_settings

    settings = get_settings()
    print(settings.database_url)  # "sqlite:///./maska_storage.db"
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application-wide settings.

    Defaults are safe for local development. Override via environment
    variables (prefixed ``MASKA_``) or a ``.env`` file in the backend/
    directory.
    """

    model_config = SettingsConfigDict(
        env_prefix="MASKA_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # -- Application metadata -------------------------------------------------
    app_name: str = "MaskaStorage API"
    app_version: str = "0.1.0"
    environment: str = "development"  # development | staging | production

    # -- Database -------------------------------------------------------------
    database_url: str = "sqlite:///./maska_storage.db"

    # -- File uploads ---------------------------------------------------------
    upload_dir: str = "./uploads"
    max_upload_size_mb: int = 50

    # -- Startup behaviour ----------------------------------------------------
    seed_on_startup: bool = True  # False in production

    # -- ChromaDB (Yeshneil's retrieval layer) --------------------------------
    # Placeholder — actual values set by Yeshneil/Pranav once retrieval is wired.
    chroma_path: str = "./chroma_data"
    chroma_host: str | None = None  # None = use local persistent storage

    # -- LLM (Sriganesh's AI pipeline) ----------------------------------------
    # Read from env; NEVER hardcode an actual key here.
    llm_api_key: str | None = None

    # -- CORS -----------------------------------------------------------------
    allowed_origins: list[str] = [
        "http://localhost:5173",   # Vite default
        "http://127.0.0.1:5173",  # Vite alternate
    ]

    # -- Logging --------------------------------------------------------------
    log_level: str = "INFO"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Return the cached Settings singleton.

    Parsed once on first call; subsequent calls return the same instance.
    To reset (e.g. in tests), call ``get_settings.cache_clear()``.
    """
    return Settings()

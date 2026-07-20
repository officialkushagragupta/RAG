"""
Frontend configuration module.

Defines `Settings`, a pydantic-settings model that loads every configurable
value from environment variables (and a local .env file in development).
Use `get_settings()` everywhere -- it is `lru_cache`d so the environment is
parsed exactly once per process.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Strongly-typed frontend settings sourced from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # --- App -----------------------------------------------------------------
    APP_TITLE: str = "RAG Document Chatbot"
    ENVIRONMENT: str = "development"

    # --- Backend connection ----------------------------------------------------
    BACKEND_API_URL: str = "http://localhost:8000"
    API_V1_PREFIX: str = "/api/v1"
    REQUEST_TIMEOUT_SECONDS: int = 60

    # --- Logging ---------------------------------------------------------------
    LOG_LEVEL: str = "INFO"

    # --- Upload hints (mirrors backend limits for client-side feedback) -----------
    MAX_UPLOAD_SIZE_MB: int = 20
    ALLOWED_FILE_EXTENSIONS: str = ".pdf"

    # --- Model display labels (mirrors backend .env -- purely cosmetic, sidebar
    # display only; the frontend never calls Gemini/embeddings directly) ------------
    GEMINI_MODEL_NAME: str = "gemini-3.1-flash-lite"
    EMBEDDING_MODEL_NAME: str = "models/gemini-embedding-001"

    @property
    def api_base_url(self) -> str:
        """Fully-qualified backend API base URL, e.g. http://localhost:8000/api/v1."""
        return f"{self.BACKEND_API_URL.rstrip('/')}{self.API_V1_PREFIX}"

    @property
    def allowed_file_extensions_list(self) -> list[str]:
        """ALLOWED_FILE_EXTENSIONS parsed into a lowercase list, e.g. [".pdf"]."""
        return [ext.strip().lower() for ext in self.ALLOWED_FILE_EXTENSIONS.split(",") if ext.strip()]


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide cached Settings instance (parses env vars once)."""
    return Settings()

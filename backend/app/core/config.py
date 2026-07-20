"""
Production configuration module.

Defines `Settings`, a pydantic-settings model that loads every configurable
value from environment variables (and a local .env file in development).
Use `get_settings()` everywhere -- it is `lru_cache`d so the environment is
parsed exactly once per process.
"""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.utils import constants


class Settings(BaseSettings):
    """
    Strongly-typed application settings sourced from environment variables.

    Every field has a safe development-friendly default so the app can boot
    without a .env file, EXCEPT secrets like `GEMINI_API_KEY`, which must be
    supplied explicitly -- startup verification will fail loudly otherwise.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # --- App ---------------------------------------------------------------
    APP_NAME: str = constants.APP_TITLE
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"  # development | staging | production
    DEBUG: bool = False

    # --- Server --------------------------------------------------------------
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    API_V1_PREFIX: str = constants.DEFAULT_API_V1_PREFIX

    # --- CORS ----------------------------------------------------------------
    # Comma-separated list of allowed origins, e.g. "http://localhost:8501,https://app.example.com"
    CORS_ORIGINS: str = "*"

    # --- Logging ---------------------------------------------------------------
    LOG_LEVEL: str = constants.DEFAULT_LOG_LEVEL
    LOG_DIR: str = constants.DEFAULT_LOG_DIR
    LOG_FILE_NAME: str = constants.DEFAULT_LOG_FILE_NAME
    LOG_MAX_BYTES: int = constants.DEFAULT_LOG_MAX_BYTES
    LOG_BACKUP_COUNT: int = constants.DEFAULT_LOG_BACKUP_COUNT

    # --- Gemini (LLM) ----------------------------------------------------------
    GEMINI_API_KEY: str = Field(default="", description="Google AI Studio / Gemini API key.")
    GEMINI_MODEL_NAME: str = constants.DEFAULT_GEMINI_MODEL_NAME

    # --- Embeddings --------------------------------------------------------------
    EMBEDDING_MODEL_NAME: str = constants.DEFAULT_EMBEDDING_MODEL_NAME
    # Truncated vector size (Matryoshka representation learning) -- smaller than the
    # model's native 3072 dims to keep ChromaDB lightweight for free-tier hosting.
    EMBEDDING_DIMENSION: int = constants.DEFAULT_EMBEDDING_DIMENSION

    # --- ChromaDB ----------------------------------------------------------------
    CHROMA_PERSIST_DIRECTORY: str = constants.DEFAULT_CHROMA_PERSIST_DIRECTORY
    # Single fixed collection -- this app has exactly one active document at a time.
    CHROMA_COLLECTION_NAME: str = constants.CHROMA_COLLECTION_NAME

    # --- Uploads ------------------------------------------------------------------
    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE_MB: int = constants.DEFAULT_MAX_UPLOAD_SIZE_MB
    # Comma-separated, e.g. ".pdf"
    ALLOWED_FILE_EXTENSIONS: str = ",".join(constants.SUPPORTED_FILE_EXTENSIONS)
    # Comma-separated, e.g. "application/pdf"
    ALLOWED_MIME_TYPES: str = ",".join(constants.SUPPORTED_MIME_TYPES)

    # --- Chunking (used by ChunkService once implemented) --------------------------
    CHUNK_SIZE: int = constants.DEFAULT_CHUNK_SIZE
    CHUNK_OVERLAP: int = constants.DEFAULT_CHUNK_OVERLAP

    # --- Chat ------------------------------------------------------------------------
    # Bounds the in-memory chat history for the active document (no DB/Redis persistence).
    MAX_CHAT_HISTORY_TURNS: int = constants.DEFAULT_MAX_CHAT_HISTORY_TURNS
    RECOMMENDED_QUESTIONS_COUNT: int = constants.RECOMMENDED_QUESTIONS_COUNT
    FOLLOWUP_QUESTIONS_COUNT: int = constants.FOLLOWUP_QUESTIONS_COUNT

    # --- Debug ---------------------------------------------------------------------
    # When true, ChatResponse.debug carries retrieval diagnostics (chunk count,
    # similarity scores) for tuning chunk size/overlap/retrieval quality.
    # Must be false in production -- it's a development/tuning aid only.
    ENABLE_DEBUG_METADATA: bool = False

    # --- Derived helpers -------------------------------------------------------

    @computed_field  # type: ignore[misc]
    @property
    def cors_origins_list(self) -> list[str]:
        """CORS_ORIGINS parsed into a list; `"*"` is kept as a literal wildcard."""
        if self.CORS_ORIGINS.strip() == "*":
            return ["*"]
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @computed_field  # type: ignore[misc]
    @property
    def allowed_file_extensions_list(self) -> list[str]:
        """ALLOWED_FILE_EXTENSIONS parsed into a lowercase list, e.g. [".pdf"]."""
        return [ext.strip().lower() for ext in self.ALLOWED_FILE_EXTENSIONS.split(",") if ext.strip()]

    @computed_field  # type: ignore[misc]
    @property
    def allowed_mime_types_list(self) -> list[str]:
        """ALLOWED_MIME_TYPES parsed into a list, e.g. ["application/pdf"]."""
        return [mime.strip() for mime in self.ALLOWED_MIME_TYPES.split(",") if mime.strip()]

    @computed_field  # type: ignore[misc]
    @property
    def max_upload_size_bytes(self) -> int:
        """MAX_UPLOAD_SIZE_MB converted to bytes."""
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    @property
    def log_file_path(self) -> Path:
        """Absolute path to the rotating log file, creating LOG_DIR if needed."""
        log_dir = Path(self.LOG_DIR)
        log_dir.mkdir(parents=True, exist_ok=True)
        return log_dir / self.LOG_FILE_NAME

    @property
    def upload_dir_path(self) -> Path:
        """Absolute path to the upload directory, creating it if needed."""
        upload_dir = Path(self.UPLOAD_DIR)
        upload_dir.mkdir(parents=True, exist_ok=True)
        return upload_dir


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide cached Settings instance (parses env vars once)."""
    return Settings()

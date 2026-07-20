"""
Fixed, non-configurable constants.

Anything an operator might reasonably want to change per-environment belongs
in core.config.Settings (env-driven) instead. This module holds values that
are fixed by the product spec (e.g. "5 recommended questions") or used as
the hardcoded defaults that Settings falls back to.
"""

# --- App metadata -----------------------------------------------------------

APP_TITLE = "RAG Document Chatbot API"
APP_DESCRIPTION = "Upload PDFs, index them, and ask questions with cited answers."

# --- API -------------------------------------------------------------------

DEFAULT_API_V1_PREFIX = "/api/v1"

# --- File upload defaults ----------------------------------------------------

DEFAULT_MAX_UPLOAD_SIZE_MB = 20
SUPPORTED_FILE_EXTENSIONS = (".pdf",)
SUPPORTED_MIME_TYPES = ("application/pdf",)

# --- Chunking defaults --------------------------------------------------------

DEFAULT_CHUNK_SIZE = 1000
DEFAULT_CHUNK_OVERLAP = 200

# --- Models --------------------------------------------------------------

DEFAULT_GEMINI_MODEL_NAME = "gemini-3.1-flash-lite"
DEFAULT_EMBEDDING_MODEL_NAME = "models/gemini-embedding-001"
# gemini-embedding-001 natively returns 3072-dim vectors but supports Matryoshka
# truncation (768/1536 are Google's validated smaller sizes). 768 keeps ChromaDB's
# on-disk/RAM footprint ~4x smaller -- important for free-tier hosting.
DEFAULT_EMBEDDING_DIMENSION = 768

# --- ChromaDB ----------------------------------------------------------------

DEFAULT_CHROMA_PERSIST_DIRECTORY = "chroma_db"
# Single fixed collection -- this app has exactly one active document at a time.
CHROMA_COLLECTION_NAME = "document_rag"

# --- Chat ------------------------------------------------------------------------

DEFAULT_MAX_CHAT_HISTORY_TURNS = 10

# Fixed by product spec -- not meant to be tuned per-environment.
RECOMMENDED_QUESTIONS_COUNT = 5
FOLLOWUP_QUESTIONS_COUNT = 5

# --- Logging -------------------------------------------------------------

DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_LOG_DIR = "logs"
DEFAULT_LOG_FILE_NAME = "app.log"
DEFAULT_LOG_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
DEFAULT_LOG_BACKUP_COUNT = 5
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# --- Chat roles ----------------------------------------------------------

ROLE_USER = "user"
ROLE_ASSISTANT = "assistant"


class ErrorCode:
    """String codes returned in ErrorResponse.error_code, stable for client-side handling."""

    INVALID_FILE_TYPE = "INVALID_FILE_TYPE"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    NO_ACTIVE_DOCUMENT = "NO_ACTIVE_DOCUMENT"
    CHROMA_UNAVAILABLE = "CHROMA_UNAVAILABLE"
    GEMINI_UNAVAILABLE = "GEMINI_UNAVAILABLE"
    INTERNAL_ERROR = "INTERNAL_ERROR"

"""
ChromaDB client wiring.

Provides a process-wide singleton persistent ChromaDB client and a startup
verification helper. This is infrastructure (connection management), not
retrieval logic -- collection/document operations belong in
app.services.vector_service.
"""

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.core.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

_client: chromadb.ClientAPI | None = None


def get_chroma_client() -> chromadb.ClientAPI:
    """Lazily create and return the singleton persistent ChromaDB client."""
    global _client
    if _client is None:
        settings = get_settings()
        logger.info("Initializing ChromaDB PersistentClient at '%s'.", settings.CHROMA_PERSIST_DIRECTORY)
        _client = chromadb.PersistentClient(
            path=settings.CHROMA_PERSIST_DIRECTORY,
            # Chroma's own anonymous product-usage telemetry (PostHog-based, sent to
            # Chroma Inc., unrelated to our app) breaks under this posthog version
            # ("capture() takes 1 positional argument but 3 were given"). It isn't
            # OpenTelemetry-based and isn't swappable for it -- just disable it.
            settings=ChromaSettings(anonymized_telemetry=False),
        )
    return _client


def verify_chroma_connection() -> bool:
    """
    Verify ChromaDB is reachable by issuing a heartbeat call.

    Raises whatever exception ChromaDB raises on failure -- callers (main.py
    lifespan, /health) decide whether that should be fatal or just reported.
    """
    client = get_chroma_client()
    client.heartbeat()
    logger.info("ChromaDB connection verified.")
    return True

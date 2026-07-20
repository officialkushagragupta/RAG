"""
Active-document state service.

Holds the single active document's metadata and its chat history in
memory, per this app's single-document architecture (see README's
"Architecture Constraints" -- no sessions, no Redis, no SQL). Uploading a
new PDF always replaces both via `clear()` followed by `set_active_document()`.
"""

import threading
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any

from app.core.config import get_settings


class DocumentStateService:
    """
    In-memory store for the one currently active document and its chat
    history. Access `get_document_state_service()` below rather than
    constructing this directly -- API handlers share one process-wide
    instance so state actually persists across requests.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._document: dict[str, Any] | None = None
        self._history: list[dict[str, Any]] = []

    def get_active_document(self) -> dict[str, Any] | None:
        """Return the active document's metadata, or None if nothing has been indexed yet."""
        with self._lock:
            return dict(self._document) if self._document is not None else None

    def set_active_document(self, document: dict[str, Any]) -> None:
        """Set the active document's metadata, replacing whatever was there before."""
        with self._lock:
            self._document = dict(document)

    def clear(self) -> None:
        """
        Wipe the active document and chat history.

        Called before indexing a new upload (per the "new PDF replaces
        everything" rule) and by DELETE /document.
        """
        with self._lock:
            self._document = None
            self._history = []

    def clear_history(self) -> None:
        """
        Clear only the chat history, leaving the active document's
        metadata (and therefore its Chroma collection/uploaded file)
        untouched. Called by DELETE /chat/history.
        """
        with self._lock:
            self._history = []

    def append_history(self, role: str, content: str) -> None:
        """Append one turn to the bounded chat history (Settings.MAX_CHAT_HISTORY_TURNS)."""
        settings = get_settings()
        with self._lock:
            self._history.append({"role": role, "content": content, "timestamp": datetime.now(timezone.utc)})
            # MAX_CHAT_HISTORY_TURNS counts Q&A turn-pairs, so keep 2x entries (user + assistant each).
            max_entries = settings.MAX_CHAT_HISTORY_TURNS * 2
            if len(self._history) > max_entries:
                self._history = self._history[-max_entries:]

    def get_history(self) -> list[dict[str, Any]]:
        """Return the chat history for the active document, oldest turn first."""
        with self._lock:
            return list(self._history)


@lru_cache
def get_document_state_service() -> DocumentStateService:
    """Return the process-wide cached DocumentStateService instance (state must survive across requests)."""
    return DocumentStateService()

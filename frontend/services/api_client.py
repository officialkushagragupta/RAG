"""
Backend API client.

Thin wrapper around HTTP calls to the FastAPI backend using `requests`.
Centralizing this here means UI components never call `requests` directly
and never hardcode the backend base URL. No session_id anywhere -- the
backend has exactly one active document at a time.
"""

from typing import Any, BinaryIO

import requests
import streamlit as st

from core.config import get_settings


class BackendAPIError(Exception):
    """
    Raised for any failure talking to the backend: network errors, timeouts,
    and non-2xx HTTP responses.

    `kind` lets callers (components/error_banner.py) pick a friendly
    message without re-inspecting the underlying exception type; use
    `status_code` for finer-grained handling (e.g. 404 = no active document).
    """

    def __init__(self, message: str, kind: str = "generic", status_code: int | None = None) -> None:
        self.kind = kind
        self.status_code = status_code
        super().__init__(message)


class BackendAPIClient:
    """Wraps REST calls to the backend's /api/v1 endpoints (see backend/app/api/*)."""

    def __init__(self, base_url: str | None = None) -> None:
        """Store the backend base URL, defaulting to core.config.get_settings().BACKEND_API_URL."""
        settings = get_settings()
        self._base_url = (base_url or settings.BACKEND_API_URL).rstrip("/")
        self._api_prefix = settings.API_V1_PREFIX
        self._timeout = settings.REQUEST_TIMEOUT_SECONDS

    def _request(self, method: str, path: str, *, versioned: bool = True, **kwargs: Any) -> Any:
        """
        Issue one HTTP request and return its parsed JSON body (or None for
        a `null`/empty body), raising BackendAPIError with a `kind` the UI
        can map to a friendly message.
        """
        prefix = self._api_prefix if versioned else ""
        url = f"{self._base_url}{prefix}{path}"
        try:
            response = requests.request(method, url, timeout=self._timeout, **kwargs)
        except requests.exceptions.Timeout as exc:
            raise BackendAPIError("Request timed out.", kind="timeout") from exc
        except requests.exceptions.ConnectionError as exc:
            raise BackendAPIError("Could not reach the backend.", kind="unavailable") from exc
        except requests.exceptions.RequestException as exc:
            raise BackendAPIError(str(exc), kind="generic") from exc

        if response.status_code >= 400:
            detail = response.text
            try:
                detail = response.json().get("detail", detail)
            except ValueError:
                pass
            raise BackendAPIError(detail, kind="http_error", status_code=response.status_code)

        if not response.content:
            return None
        return response.json()

    def get_active_document(self) -> dict[str, Any] | None:
        """GET /document -- fetch the currently active document, or None."""
        return self._request("GET", "/document")

    def upload_document(self, file: BinaryIO, filename: str) -> dict[str, Any]:
        """POST /document -- upload a PDF, replacing whatever was previously active."""
        files = {"file": (filename, file, "application/pdf")}
        return self._request("POST", "/document", files=files)

    def clear_document(self) -> dict[str, Any]:
        """DELETE /document -- clear the active document, its index, and its chat history."""
        return self._request("DELETE", "/document")

    def ask_question(self, question: str) -> dict[str, Any]:
        """POST /chat."""
        return self._request("POST", "/chat", json={"question": question})

    def get_chat_history(self) -> dict[str, Any]:
        """GET /chat/history."""
        return self._request("GET", "/chat/history")

    def clear_chat_history(self) -> dict[str, Any]:
        """
        DELETE /chat/history -- clear only the chat history, keeping the
        active document, its index, and its uploaded file untouched.

        Returns {"message", "cleared", "suggested_questions"} -- the
        document's original suggested questions, restored now that the
        conversation-specific follow-ups are gone.
        """
        return self._request("DELETE", "/chat/history")

    def health_check(self) -> dict[str, Any]:
        """GET /health (unversioned -- not under API_V1_PREFIX)."""
        return self._request("GET", "/health", versioned=False)


@st.cache_resource
def get_api_client() -> BackendAPIClient:
    """Return a process-wide cached BackendAPIClient (reuses the underlying HTTP connection pool)."""
    return BackendAPIClient()

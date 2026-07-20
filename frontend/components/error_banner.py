"""Friendly error banner component, mapping BackendAPIError -> a human-readable message."""

import streamlit as st

from services.api_client import BackendAPIError
from utils.constants import (
    ERROR_BACKEND_UNAVAILABLE,
    ERROR_GENERIC,
    ERROR_LLM_FAILED,
    ERROR_NETWORK_TIMEOUT,
    ERROR_NO_DOCUMENT,
)


def render_error(error: BackendAPIError | Exception | str, fallback: str = ERROR_GENERIC) -> None:
    """
    Render a friendly `st.error` banner for a caught error.

    `fallback` lets each call site pick the best default for its context
    (e.g. the uploader passes ERROR_UPLOAD_FAILED) when the error doesn't
    map to one of the well-known cases below (timeout, unreachable
    backend, no active document, 5xx/LLM failure).
    """
    if isinstance(error, BackendAPIError):
        if error.kind == "timeout":
            message = ERROR_NETWORK_TIMEOUT
        elif error.kind == "unavailable":
            message = ERROR_BACKEND_UNAVAILABLE
        elif error.status_code == 404:
            message = ERROR_NO_DOCUMENT
        elif error.status_code is not None and error.status_code >= 500:
            message = ERROR_LLM_FAILED
        else:
            message = fallback

        st.error(message)
        with st.expander("Technical details"):
            st.code(str(error))
        return

    message = fallback if fallback != ERROR_GENERIC else str(error)
    st.error(message)
    if isinstance(error, Exception):
        # Any *other* exception (a bug, not an expected API failure) still gets a
        # friendly banner -- the raw type/message goes in a collapsed expander,
        # never directly in the page, so debugging info is available without
        # ever "blurting out" a traceback to the user.
        with st.expander("Technical details"):
            st.code(f"{type(error).__name__}: {error}")

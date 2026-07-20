"""PDF uploader component: file picker, simulated progress, and indexing via the backend."""

import time

import streamlit as st

from core.config import get_settings
from services.api_client import BackendAPIClient
from utils.constants import (
    ERROR_UPLOAD_FAILED,
    SESSION_STATE_KEY_ACTIVE_DOCUMENT,
    SESSION_STATE_KEY_CHAT_HISTORY,
    SESSION_STATE_KEY_SHOW_UPLOADER,
    SESSION_STATE_KEY_SUGGESTED_QUESTIONS,
    SESSION_STATE_KEY_UPLOADER_KEY,
)

from components.error_banner import render_error


def render_uploader(client: BackendAPIClient) -> None:
    """
    Render the PDF file picker and, once a file is selected, index it via
    the backend -- replacing any currently active document.

    The upload call is a single synchronous request, so "Extracting
    text...", "Creating embeddings...", and "Indexing document..." are a
    cosmetic sequence shown around that one call, not real backend
    progress events. Streamlit blocks on this same script run while the
    request is in flight, so the rest of the interface is naturally
    non-interactive until it completes -- no extra "disable" logic needed.
    """
    settings = get_settings()
    uploader_key = f"pdf_uploader_{st.session_state.get(SESSION_STATE_KEY_UPLOADER_KEY, 0)}"

    uploaded_file = st.file_uploader(
        "Upload a PDF",
        type=[ext.lstrip(".") for ext in settings.allowed_file_extensions_list],
        key=uploader_key,
        help=f"PDF only, max {settings.MAX_UPLOAD_SIZE_MB} MB.",
    )

    if uploaded_file is None:
        return

    status_box = st.status("Extracting text...", expanded=True)
    try:
        time.sleep(0.4)
        status_box.write("Extracting text...")
        status_box.update(label="Creating embeddings...")
        time.sleep(0.4)
        status_box.write("Creating embeddings...")
        status_box.update(label="Indexing document...")
        status_box.write("Indexing document...")

        document = client.upload_document(uploaded_file, uploaded_file.name)
    except Exception as exc:  # noqa: BLE001 - covers BackendAPIError and anything unexpected
        status_box.update(label="Upload failed", state="error")
        render_error(exc, fallback=ERROR_UPLOAD_FAILED)
        return

    status_box.update(label="Indexed Successfully", state="complete", expanded=False)

    st.session_state[SESSION_STATE_KEY_ACTIVE_DOCUMENT] = document
    st.session_state[SESSION_STATE_KEY_CHAT_HISTORY] = []
    st.session_state[SESSION_STATE_KEY_SUGGESTED_QUESTIONS] = document.get("suggested_questions", [])
    st.session_state[SESSION_STATE_KEY_SHOW_UPLOADER] = False
    st.session_state[SESSION_STATE_KEY_UPLOADER_KEY] = st.session_state.get(SESSION_STATE_KEY_UPLOADER_KEY, 0) + 1
    st.rerun()

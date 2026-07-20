"""Upload screen: shown when there's no active document, or the user chose to upload a new one."""

import streamlit as st

from components.header import render_header
from components.uploader import render_uploader
from services.api_client import BackendAPIClient
from utils.constants import SESSION_STATE_KEY_ACTIVE_DOCUMENT, SESSION_STATE_KEY_SHOW_UPLOADER


def render(client: BackendAPIClient) -> None:
    """Render the upload screen: header band, an optional back-link, and the PDF uploader."""
    render_header("Document RAG Chatbot", "Upload a PDF and ask natural language questions.")

    has_active_document = st.session_state.get(SESSION_STATE_KEY_ACTIVE_DOCUMENT) is not None
    if has_active_document:
        if st.button("← Back to current document"):
            st.session_state[SESSION_STATE_KEY_SHOW_UPLOADER] = False
            st.rerun()

    render_uploader(client)

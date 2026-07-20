"""Sidebar component: active document info, model info, and document controls."""

import streamlit as st

from core.config import get_settings
from services.api_client import BackendAPIClient
from utils.constants import (
    SESSION_STATE_KEY_ACTIVE_DOCUMENT,
    SESSION_STATE_KEY_CHAT_HISTORY,
    SESSION_STATE_KEY_SHOW_UPLOADER,
    SESSION_STATE_KEY_SUGGESTED_QUESTIONS,
    SESSION_STATE_KEY_UPLOADER_KEY,
)
from components.error_banner import render_error


def render_sidebar(client: BackendAPIClient) -> None:
    """Render the sidebar: active document card (or empty state), model info, and Upload/Clear controls."""
    settings = get_settings()
    document = st.session_state.get(SESSION_STATE_KEY_ACTIVE_DOCUMENT)

    with st.sidebar:
        st.markdown('<p class="app-kicker">— Document RAG Chatbot</p>', unsafe_allow_html=True)

        st.markdown('<p class="kicker">Current document</p>', unsafe_allow_html=True)
        if document:
            with st.container():
                st.markdown(
                    f'<div class="doc-card"><strong>{document["filename"]}</strong><br>'
                    f'<span class="doc-card-status">{document["status"]}</span></div>',
                    unsafe_allow_html=True,
                )
                col1, col2 = st.columns(2)
                col1.metric("Pages", document.get("pages", "–"))
                col2.metric("Chunks", document.get("chunks", "–"))
        else:
            st.markdown(
                '<div class="doc-card doc-card-empty">No document uploaded yet — '
                "use the uploader in the main panel.</div>",
                unsafe_allow_html=True,
            )

        st.divider()
        st.markdown('<p class="kicker">Models</p>', unsafe_allow_html=True)
        st.caption(f"LLM: `{settings.GEMINI_MODEL_NAME}`")
        st.caption(f"Embeddings: `{settings.EMBEDDING_MODEL_NAME}`")

        # Only offer a sidebar upload shortcut once a document already exists --
        # when there's no active document, the main panel *is* the uploader, so
        # a second "upload" control here would just be a confusing duplicate.
        if document:
            st.divider()
            if st.button("Replace Document", use_container_width=True):
                st.session_state[SESSION_STATE_KEY_SHOW_UPLOADER] = True
                st.rerun()
            if st.button("Clear Current Document", use_container_width=True):
                _clear_document(client)


def _clear_document(client: BackendAPIClient) -> None:
    """Call DELETE /document, then reset local state to match (document, chat, suggestions)."""
    try:
        client.clear_document()
    except Exception as exc:  # noqa: BLE001 - covers BackendAPIError and anything unexpected
        render_error(exc)
        return

    st.session_state[SESSION_STATE_KEY_ACTIVE_DOCUMENT] = None
    st.session_state[SESSION_STATE_KEY_CHAT_HISTORY] = []
    st.session_state[SESSION_STATE_KEY_SUGGESTED_QUESTIONS] = []
    st.session_state[SESSION_STATE_KEY_SHOW_UPLOADER] = False
    st.session_state[SESSION_STATE_KEY_UPLOADER_KEY] = st.session_state.get(SESSION_STATE_KEY_UPLOADER_KEY, 0) + 1
    st.rerun()

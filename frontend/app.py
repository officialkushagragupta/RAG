"""
Streamlit entry point for the RAG Document Chatbot UI.

Wires together page config, custom CSS, session state, the sidebar, and
the main view (upload vs. chat), delegating all actual rendering to
components/ and views/. Talks to the backend only through
services.api_client -- never calls `requests` directly.
"""

import traceback
from pathlib import Path

import streamlit as st

from components.error_banner import render_error
from components.sidebar import render_sidebar
from core.config import get_settings
from services.api_client import get_api_client
from utils.constants import (
    ERROR_GENERIC,
    SESSION_STATE_KEY_ACTIVE_DOCUMENT,
    SESSION_STATE_KEY_CHAT_HISTORY,
    SESSION_STATE_KEY_SHOW_UPLOADER,
    SESSION_STATE_KEY_SUGGESTED_QUESTIONS,
    SESSION_STATE_KEY_UPLOADER_KEY,
)
from views import chat_view, upload_view


def _inject_custom_css() -> None:
    """Load and inject assets/custom.css, replacing Streamlit's default look."""
    css_path = Path(__file__).parent / "assets" / "custom.css"
    if css_path.exists():
        st.markdown(f"<style>{css_path.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)


def _page_icon() -> str | None:
    """Browser-tab icon: the Ardee mark on a black square, falling back to Streamlit's default if missing."""
    favicon_path = Path(__file__).parent / "assets" / "favicon.png"
    return str(favicon_path) if favicon_path.exists() else None


def _init_session_state() -> None:
    """Set every session_state key this app reads to a safe default, once per browser session."""
    st.session_state.setdefault(SESSION_STATE_KEY_ACTIVE_DOCUMENT, None)
    st.session_state.setdefault(SESSION_STATE_KEY_CHAT_HISTORY, [])
    st.session_state.setdefault(SESSION_STATE_KEY_SUGGESTED_QUESTIONS, [])
    st.session_state.setdefault(SESSION_STATE_KEY_SHOW_UPLOADER, False)
    st.session_state.setdefault(SESSION_STATE_KEY_UPLOADER_KEY, 0)


def main() -> None:
    """Configure the page, then render the sidebar and whichever view is active."""
    settings = get_settings()
    st.set_page_config(page_title=settings.APP_TITLE, page_icon=_page_icon(), layout="wide")
    _inject_custom_css()
    _init_session_state()

    # Last-resort safety net: components/views have their own targeted
    # try/except around individual API calls for nicer inline UX (e.g. an
    # "Upload failed" status), but *anything* escaping those -- a genuine
    # bug, a stale-module edge case, whatever -- must still never surface
    # as Streamlit's raw traceback box. The full traceback still goes to
    # the terminal (via traceback.print_exc()) for local debugging; only
    # the browser is guaranteed to see a friendly message.
    try:
        client = get_api_client()
        render_sidebar(client)

        document_active = st.session_state.get(SESSION_STATE_KEY_ACTIVE_DOCUMENT) is not None
        show_uploader = st.session_state.get(SESSION_STATE_KEY_SHOW_UPLOADER, False)

        if document_active and not show_uploader:
            chat_view.render(client)
        else:
            upload_view.render(client)
    except Exception as exc:  # noqa: BLE001 - deliberately broad, see docstring above
        traceback.print_exc()
        render_error(exc, fallback=ERROR_GENERIC)


if __name__ == "__main__":
    main()

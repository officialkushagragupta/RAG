"""Chat screen: shown once a document is active. Header + the full chat window."""

import streamlit as st

from components.chat_window import render_chat_window
from components.header import render_header
from services.api_client import BackendAPIClient
from utils.constants import SESSION_STATE_KEY_ACTIVE_DOCUMENT


def render(client: BackendAPIClient) -> None:
    """Render the chat screen: active document header + the chat window."""
    document = st.session_state[SESSION_STATE_KEY_ACTIVE_DOCUMENT]
    render_header("Document RAG Chatbot", f"Chatting with {document['filename']}")
    render_chat_window(client)

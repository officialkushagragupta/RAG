"""Chat window component: conversation history, live Q&A, citations, and suggested follow-ups."""

import streamlit.components.v1 as components
import streamlit as st

from components.citation import render_citations
from components.error_banner import render_error
from components.suggested_questions import render_suggested_questions
from services.api_client import BackendAPIClient
from utils.constants import (
    ERROR_LLM_FAILED,
    ROLE_ASSISTANT,
    ROLE_USER,
    SESSION_STATE_KEY_CHAT_HISTORY,
    SESSION_STATE_KEY_PENDING_QUESTION,
    SESSION_STATE_KEY_SUGGESTED_QUESTIONS,
)


def render_chat_window(client: BackendAPIClient) -> None:
    """Render the full chat experience: history, suggested-question chips, and the input box."""
    history = st.session_state.setdefault(SESSION_STATE_KEY_CHAT_HISTORY, [])

    _render_history_header(client)

    for turn in history:
        with st.chat_message(turn["role"]):
            st.markdown(turn["content"])
            if turn["role"] == ROLE_ASSISTANT and turn.get("citations"):
                render_citations(turn["citations"])

    suggested = st.session_state.get(SESSION_STATE_KEY_SUGGESTED_QUESTIONS, [])
    render_suggested_questions(suggested, on_select=_queue_question, key_prefix="suggested")

    _scroll_to_bottom()

    typed_question = st.chat_input("Ask a question about this document...")
    if typed_question:
        _queue_question(typed_question)

    pending_question = st.session_state.pop(SESSION_STATE_KEY_PENDING_QUESTION, None)
    if pending_question:
        _handle_question(client, pending_question)


def _render_history_header(client: BackendAPIClient) -> None:
    """Render the small 'Clear Chat' control above the conversation, when there's something to clear."""
    history = st.session_state.get(SESSION_STATE_KEY_CHAT_HISTORY, [])
    if not history:
        return

    _, clear_col = st.columns([5, 1])
    with clear_col:
        if st.button("Clear Chat", use_container_width=True):
            try:
                result = client.clear_chat_history()
            except Exception as exc:  # noqa: BLE001 - covers BackendAPIError and anything unexpected
                render_error(exc)
                return

            st.session_state[SESSION_STATE_KEY_CHAT_HISTORY] = []
            st.session_state[SESSION_STATE_KEY_SUGGESTED_QUESTIONS] = result.get("suggested_questions", [])
            st.rerun()


def _queue_question(question: str) -> None:
    """Queue `question` for processing on the next rerun (a button click can't await a network call)."""
    st.session_state[SESSION_STATE_KEY_PENDING_QUESTION] = question
    st.rerun()


def _handle_question(client: BackendAPIClient, question: str) -> None:
    """Send `question` to the backend, append both turns to history, and refresh suggested questions."""
    history = st.session_state.setdefault(SESSION_STATE_KEY_CHAT_HISTORY, [])
    history.append({"role": ROLE_USER, "content": question})

    with st.chat_message(ROLE_USER):
        st.markdown(question)

    with st.chat_message(ROLE_ASSISTANT):
        with st.spinner("Thinking..."):
            try:
                response = client.ask_question(question)
            except Exception as exc:  # noqa: BLE001 - covers BackendAPIError and anything unexpected
                history.pop()  # don't leave an unanswered question in history
                render_error(exc, fallback=ERROR_LLM_FAILED)
                return

        st.markdown(response["answer"])
        render_citations(response.get("citations", []))

    history.append(
        {
            "role": ROLE_ASSISTANT,
            "content": response["answer"],
            "citations": response.get("citations", []),
        }
    )
    st.session_state[SESSION_STATE_KEY_SUGGESTED_QUESTIONS] = response.get("suggested_questions", [])
    st.rerun()


def _scroll_to_bottom() -> None:
    """
    Best-effort auto-scroll to the newest message.

    Streamlit has no native auto-scroll API; this reaches into the parent
    document from a zero-height embedded iframe, a common community
    workaround. The `.main` selector targets Streamlit's internal DOM and
    may need adjusting across Streamlit versions.
    """
    components.html(
        """
        <script>
        var container = window.parent.document.querySelector('.main');
        if (container) { container.scrollTop = container.scrollHeight; }
        </script>
        """,
        height=0,
    )

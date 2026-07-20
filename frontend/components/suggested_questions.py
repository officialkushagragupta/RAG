"""Suggested/follow-up question chips component, shared by the post-upload and post-answer states."""

from collections.abc import Callable

import streamlit as st


def render_suggested_questions(questions: list[str], on_select: Callable[[str], None], key_prefix: str) -> None:
    """
    Render `questions` as a grid of clickable cards; calls `on_select(question)`
    the moment one is clicked.

    Used both for the initial 5 suggestions right after upload and the 5
    fresh contextual follow-ups returned after every answer -- `key_prefix`
    must be unique per call site/rerun so Streamlit doesn't collide widget keys.
    """
    if not questions:
        return

    st.markdown("**Suggested questions**")
    columns = st.columns(2)
    for index, question in enumerate(questions):
        column = columns[index % len(columns)]
        with column:
            if st.button(question, key=f"{key_prefix}_{index}", use_container_width=True):
                on_select(question)

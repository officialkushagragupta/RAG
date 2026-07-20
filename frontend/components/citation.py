"""Source citation component: renders the "Sources" section below an assistant answer."""

from typing import Any

import streamlit as st

from utils.formatting import format_citation_label


def render_citations(citations: list[dict[str, Any]]) -> None:
    """
    Render a "Sources" section with one expander per citation.

    Each expander is labeled with the formatted document -> heading
    breadcrumb -> page reference and, inside, shows the individual
    metadata fields plus a preview snippet of the retrieved chunk so the
    user can inspect it.
    """
    if not citations:
        return

    st.markdown("**Sources**")
    for citation in citations:
        label = format_citation_label(citation)
        with st.expander(label, expanded=False):
            title = citation.get("document_title") or citation.get("filename")
            if title:
                st.caption(title)
            hierarchy = citation.get("hierarchy") or []
            if hierarchy:
                st.caption(" › ".join(hierarchy))
            if citation.get("page") is not None:
                st.caption(f"Page {citation['page']}")
            if citation.get("text"):
                st.markdown(f"> {citation['text']}")

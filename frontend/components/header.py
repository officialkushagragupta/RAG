"""App header component: the black title band + Ardee mark shown atop every view."""

import base64
from functools import lru_cache
from pathlib import Path

import streamlit as st

_LOGO_PATH = Path(__file__).parent.parent / "assets" / "logo_mark.png"


@lru_cache(maxsize=1)
def _logo_data_uri() -> str | None:
    """
    Base64-encode assets/logo_mark.png once per process.

    Embedded as a data URI (rather than st.image) so it can sit inside the
    same flex-laid-out HTML block as the title/subtitle -- st.image renders
    as a separate Streamlit element and can't be inlined that way. Returns
    None if the asset is missing, so the header still renders without it.
    """
    if not _LOGO_PATH.exists():
        return None
    encoded = base64.b64encode(_LOGO_PATH.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def render_header(title: str, subtitle: str | None = None) -> None:
    """Render the black header band: Ardee mark, bold title, and optional subtitle."""
    logo_uri = _logo_data_uri()
    logo_html = f'<img class="app-header-logo" src="{logo_uri}" alt="" />' if logo_uri else ""
    subtitle_html = f'<div class="app-header-subtitle">{subtitle}</div>' if subtitle else ""

    st.markdown(
        f"""
        <div class="app-header">
            {logo_html}
            <div class="app-header-text">
                <div class="app-header-title">{title}</div>
                {subtitle_html}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

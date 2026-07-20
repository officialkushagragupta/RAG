"""
Top-level screens: upload_view (no active document, or the user chose to
upload a new one) and chat_view (an active document exists). app.py picks
one per rerun based on session_state -- these are plain modules with a
`render()` function, NOT Streamlit's file-based multipage `pages/`
directory convention (that would auto-inject its own sidebar navigation,
which conflicts with this app's custom single-flow sidebar).
"""

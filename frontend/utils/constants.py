"""
Fixed, non-configurable UI constants.

Values an operator might want to change per-environment belong in
core.config.Settings instead.
"""

RECOMMENDED_QUESTIONS_COUNT = 5
FOLLOWUP_QUESTIONS_COUNT = 5

# --- Streamlit session_state keys ---------------------------------------------
# Keys into Streamlit's own st.session_state dict (per-browser-tab UI cache,
# unrelated to any backend concept -- this app has no backend sessions).
SESSION_STATE_KEY_ACTIVE_DOCUMENT = "active_document"
SESSION_STATE_KEY_CHAT_HISTORY = "chat_history"
SESSION_STATE_KEY_SUGGESTED_QUESTIONS = "suggested_questions"
SESSION_STATE_KEY_PENDING_QUESTION = "pending_question"
# True while the uploader should be shown even though a document is already
# active (user clicked "Upload New PDF"); cleared on a successful upload or
# "Back to current document".
SESSION_STATE_KEY_SHOW_UPLOADER = "show_uploader"
# Bumped to force Streamlit to reset the file_uploader widget after a
# successful upload (it doesn't clear itself otherwise).
SESSION_STATE_KEY_UPLOADER_KEY = "uploader_key"

# --- Chat roles (mirror backend ChatRole) -----------------------------------------
ROLE_USER = "user"
ROLE_ASSISTANT = "assistant"

# --- Upload progress steps ------------------------------------------------------
# UX-only labels: the backend does parsing/embedding/indexing in a single
# synchronous request, so these are a cosmetic sequence shown around that
# one call, not truly wired to backend-internal progress.
UPLOAD_PROGRESS_STEPS = (
    "Extracting text...",
    "Creating embeddings...",
    "Indexing document...",
)

# --- Friendly error messages ------------------------------------------------------
ERROR_NO_DOCUMENT = "Please upload a PDF before asking a question."
ERROR_UPLOAD_FAILED = "We couldn't process that file. Please try a different PDF."
ERROR_LLM_FAILED = "The assistant couldn't generate a response. Please try again."
ERROR_BACKEND_UNAVAILABLE = "The backend service is unavailable right now. Please try again shortly."
ERROR_NETWORK_TIMEOUT = "The request timed out. Please check your connection and try again."
ERROR_GENERIC = "Something went wrong. Please try again."

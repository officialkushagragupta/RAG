"""
Pydantic request/response models.

This is the data contract for the API layer. There is no `session_id`
anywhere in this file: the app has exactly one active document at a time
(see README's "Architecture Constraints"), so state is global, not scoped
to a session or user.

Response shapes are intentionally flat (no nested "document" wrapper) so
the frontend can render everything it needs (filename, page/chunk counts,
status, suggested questions) straight from a single POST /document or
POST /chat response, without a follow-up call.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class ChatRole(str, Enum):
    """Speaker role within the active document's conversation history."""

    USER = "user"
    ASSISTANT = "assistant"


class DocumentStatus(str, Enum):
    """
    Processing status of the active document.

    Values are the exact human-readable strings returned to the client
    (e.g. `"status": "Indexed Successfully"`), not machine codes.
    """

    PROCESSING = "Processing"
    INDEXED = "Indexed Successfully"
    FAILED = "Failed"


class DocumentInfo(BaseModel):
    """
    Flat metadata (+ suggested questions) for the currently active document.

    Returned as-is by both `POST /document` (right after indexing) and
    `GET /document` (e.g. on a frontend refresh) so the UI never needs to
    reshape two different payloads.
    """

    filename: str
    pages: int
    chunks: int
    status: DocumentStatus
    suggested_questions: list[str] = Field(
        default_factory=list,
        description="5 suggested questions generated from the active document.",
    )


class ClearResponse(BaseModel):
    """Response returned after clearing the active document, its index, and its chat history."""

    message: str
    cleared: bool


class Citation(BaseModel):
    """
    A single, richly-annotated source citation backing part of an answer.

    Carries enough metadata for the frontend to render a professional
    breadcrumb reference (e.g. "Employee Handbook -> HR Policies -> Leave
    Policy -> Annual Leave (Page 12)") and to let the user expand it to
    inspect the retrieved chunk, rather than a bare page number.
    `document_title`/`hierarchy` are best-effort -- PDFService/ChunkService
    should fall back to `filename`-only citations (empty `hierarchy`) when
    a title or heading structure can't be confidently extracted.
    """

    filename: str
    document_title: str | None = None
    hierarchy: list[str] = Field(
        default_factory=list,
        description=(
            "Ordered heading breadcrumb leading to this chunk, e.g. "
            '["HR Policies", "Leave Policy", "Annual Leave"] -- outermost '
            "heading first, most specific last. Empty if no heading "
            "structure was detected."
        ),
    )
    page: int | None = None
    chunk_id: int | None = None
    chunk_index: int | None = None
    total_chunks: int | None = None
    char_start: int | None = None
    char_end: int | None = None
    text: str | None = Field(default=None, description="Preview snippet of the retrieved chunk.")


class ChatRequest(BaseModel):
    """A question submitted by the user about the active document."""

    question: str = Field(..., min_length=1, description="The user's natural-language question.")


class ChatDebugInfo(BaseModel):
    """
    Retrieval diagnostics for tuning chunk size, overlap, and retrieval
    quality. Only ever populated when Settings.ENABLE_DEBUG_METADATA is
    true -- ChatResponse.debug must be omitted/null in production.
    """

    retrieved_chunks: int
    similarity_scores: list[float] = Field(default_factory=list)


class ChatResponse(BaseModel):
    """Answer returned for a chat question, with citations and fresh suggested questions."""

    answer: str
    citations: list[Citation] = Field(default_factory=list)
    suggested_questions: list[str] = Field(
        default_factory=list,
        description="5 new contextual suggested questions generated after this answer.",
    )
    debug: ChatDebugInfo | None = Field(
        default=None,
        description="Retrieval diagnostics, present only when Settings.ENABLE_DEBUG_METADATA is true.",
    )


class ChatHistoryTurn(BaseModel):
    """A single turn (user question or assistant answer) in the active document's history."""

    role: ChatRole
    content: str
    timestamp: datetime


class ChatHistoryResponse(BaseModel):
    """Full conversation history for the active document."""

    history: list[ChatHistoryTurn]


class ClearChatHistoryResponse(BaseModel):
    """
    Response returned after clearing only the chat history.

    Unlike ClearResponse (DELETE /document), this keeps the active
    document, its Chroma collection, and its uploaded file untouched --
    only the conversation is wiped. `suggested_questions` echoes the
    document's original (upload-time) suggestions back, now that the
    stale, conversation-specific follow-ups have been cleared, so the
    frontend can restore them without a second GET /document call.
    """

    message: str
    cleared: bool
    suggested_questions: list[str] = Field(default_factory=list)


class HealthResponse(BaseModel):
    """Application health/readiness status, including external dependency checks."""

    status: str
    environment: str
    version: str
    chroma_status: str
    gemini_status: str
    timestamp: datetime


class ErrorResponse(BaseModel):
    """Structured error payload returned by the global exception handlers."""

    error_code: str
    detail: str

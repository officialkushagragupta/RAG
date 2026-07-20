"""
Chat endpoints.

Answers a question against the single active document (with citations),
and returns 5 new contextual suggested questions with every answer in the
same response -- no follow-up call needed. Also exposes, and can clear,
the active document's conversation history.
"""

from fastapi import APIRouter

from app.core.exceptions import NoActiveDocumentError
from app.models.schemas import (
    ChatHistoryResponse,
    ChatHistoryTurn,
    ChatRequest,
    ChatResponse,
    ClearChatHistoryResponse,
)
from app.services.question_service import QuestionService
from app.services.rag_service import RAGService
from app.services.state_service import get_document_state_service
from app.utils.constants import ROLE_ASSISTANT, ROLE_USER
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("", response_model=ChatResponse)
async def ask_question(payload: ChatRequest) -> ChatResponse:
    """
    Answer `payload.question` using the active document and prior chat
    history, returning the answer, its citations, and 5 new suggested
    follow-up questions in one response.
    """
    state_service = get_document_state_service()
    document = state_service.get_active_document()
    if document is None:
        raise NoActiveDocumentError("Upload a PDF before asking a question.")

    history = state_service.get_history()
    result = RAGService().generate_answer(payload.question, history)

    state_service.append_history(ROLE_USER, payload.question)
    state_service.append_history(ROLE_ASSISTANT, result["answer"])

    # Reuse the chunks that grounded the answer (each citation carries its
    # own "text") instead of a second similarity search for follow-ups.
    context = "\n\n".join(citation.get("text") or "" for citation in result["citations"])
    suggested_questions = QuestionService().generate_followup_questions(payload.question, result["answer"], context)

    return ChatResponse(
        answer=result["answer"],
        citations=result["citations"],
        suggested_questions=suggested_questions,
        debug=result.get("debug"),
    )


@router.get("/history", response_model=ChatHistoryResponse)
async def get_chat_history() -> ChatHistoryResponse:
    """Return the full conversation history for the active document."""
    history = get_document_state_service().get_history()
    return ChatHistoryResponse(
        history=[ChatHistoryTurn(role=turn["role"], content=turn["content"], timestamp=turn["timestamp"]) for turn in history]
    )


@router.delete("/history", response_model=ClearChatHistoryResponse)
async def clear_chat_history() -> ClearChatHistoryResponse:
    """
    Clear only the chat history, keeping the active document, its Chroma
    collection, and its uploaded file untouched. Returns the document's
    original suggested questions so the frontend can restore them without
    a second call.
    """
    state_service = get_document_state_service()
    document = state_service.get_active_document()
    if document is None:
        raise NoActiveDocumentError("No active document to clear chat history for.")

    state_service.clear_history()
    return ClearChatHistoryResponse(
        message="Chat history cleared.",
        cleared=True,
        suggested_questions=document.get("suggested_questions", []),
    )

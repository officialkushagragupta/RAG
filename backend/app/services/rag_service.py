"""
RAG orchestration service.
"""

from typing import Any

from app.core import prompts
from app.core.config import get_settings
from app.services.llm_service import LLMService
from app.services.vector_service import VectorService

_TOP_K = 5


class RAGService:
    """
    Orchestrates a full question-answering turn against the single active
    document: retrieve relevant chunks via VectorService, generate a
    grounded answer via LLMService, and assemble source citations directly
    from the retrieved chunks' rich metadata (no second lookup needed).
    """

    def __init__(self) -> None:
        self._vector_service = VectorService()
        self._llm_service = LLMService()

    def generate_answer(self, question: str, chat_history: list[dict[str, str]]) -> dict[str, Any]:
        """
        Answer `question` using the active document and prior `chat_history`.

        The prompt sent to the LLM includes each retrieved chunk's
        `document_title` and `hierarchy` breadcrumb alongside its text
        (see _format_context), not just raw chunk text -- this gives the
        model enough context to answer coherently and to ground its answer
        in the right section.

        Returns:
            A dict with {"answer": str, "citations": list[dict]}, where
            each citation dict carries the full chunk metadata (see
            models.schemas.Citation: filename, document_title, hierarchy,
            page, chunk_id, chunk_index, total_chunks, char_start,
            char_end, text). When Settings.ENABLE_DEBUG_METADATA is true,
            also includes "debug": {"retrieved_chunks": int,
            "similarity_scores": list[float]} for retrieval tuning.
        """
        settings = get_settings()
        retrieved = self._vector_service.similarity_search(question, top_k=_TOP_K)

        prompt = prompts.RAG_ANSWER_PROMPT_TEMPLATE.format(
            context=self._format_context(retrieved) or "(no relevant content found in the document)",
            chat_history=self._format_history(chat_history) or "(no prior conversation)",
            question=question,
        )
        answer = self._llm_service.generate(prompt)

        result: dict[str, Any] = {
            "answer": answer,
            "citations": [self._chunk_to_citation(chunk) for chunk in retrieved],
        }

        if settings.ENABLE_DEBUG_METADATA:
            result["debug"] = {
                "retrieved_chunks": len(retrieved),
                "similarity_scores": [
                    round(chunk["similarity"], 4) for chunk in retrieved if chunk.get("similarity") is not None
                ],
            }

        return result

    @staticmethod
    def _format_context(chunks: list[dict[str, Any]]) -> str:
        """Format retrieved chunks as one labeled block per chunk: "[Title > Section, page N]: text"."""
        blocks = []
        for chunk in chunks:
            title = chunk.get("document_title") or chunk.get("filename") or "Document"
            hierarchy = " > ".join(chunk.get("hierarchy") or [])
            location = f"{title} > {hierarchy}" if hierarchy else title
            page = chunk.get("page_number")
            label = f"{location}, page {page}" if page is not None else location
            blocks.append(f"[{label}]: {chunk.get('text', '')}")
        return "\n\n".join(blocks)

    @staticmethod
    def _format_history(chat_history: list[dict[str, str]]) -> str:
        """Format prior turns as a simple "Role: content" transcript."""
        return "\n".join(f"{turn['role'].capitalize()}: {turn['content']}" for turn in chat_history)

    @staticmethod
    def _chunk_to_citation(chunk: dict[str, Any]) -> dict[str, Any]:
        return {
            "filename": chunk.get("filename"),
            "document_title": chunk.get("document_title"),
            "hierarchy": chunk.get("hierarchy") or [],
            "page": chunk.get("page_number"),
            "chunk_id": chunk.get("chunk_id"),
            "chunk_index": chunk.get("chunk_index"),
            "total_chunks": chunk.get("total_chunks"),
            "char_start": chunk.get("char_start"),
            "char_end": chunk.get("char_end"),
            "text": chunk.get("text"),
        }

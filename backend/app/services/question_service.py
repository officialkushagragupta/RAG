"""
Question generation service.
"""

from typing import Any

from app.core import prompts
from app.core.config import get_settings
from app.services.llm_service import LLMService

# Cap how much document text goes into a single prompt (~2k tokens' worth of
# characters) -- plenty for a representative sample, and keeps prompt size
# (and cost) bounded regardless of document length.
_MAX_CONTEXT_CHARS = 8000


class QuestionService:
    """
    Generates suggested questions about the active document via
    LLMService.generate_structured(), constrained to
    core.prompts.SUGGESTED_QUESTIONS_RESPONSE_SCHEMA so Gemini always
    returns a clean JSON array of strings (no free-form-text parsing) --
    used for the initial batch right after indexing, and a fresh
    contextual batch after every answered question. Callers pass in the
    text to base questions on directly (the freshly-extracted document
    text for the initial batch, the just-retrieved answer context for
    follow-ups) rather than this service re-querying the vector store.
    """

    def __init__(self) -> None:
        self._llm_service = LLMService()

    def generate_recommended_questions(self, document_text: str) -> list[str]:
        """Generate Settings.RECOMMENDED_QUESTIONS_COUNT questions for the newly indexed active document."""
        settings = get_settings()
        prompt = prompts.RECOMMENDED_QUESTIONS_PROMPT_TEMPLATE.format(
            recommended_questions_count=settings.RECOMMENDED_QUESTIONS_COUNT,
            context=document_text[:_MAX_CONTEXT_CHARS] or "(document content unavailable)",
        )
        questions = self._llm_service.generate_structured(prompt, prompts.SUGGESTED_QUESTIONS_RESPONSE_SCHEMA)
        return self._normalize(questions, settings.RECOMMENDED_QUESTIONS_COUNT)

    def generate_followup_questions(self, question: str, answer: str, context: str = "") -> list[str]:
        """Generate Settings.FOLLOWUP_QUESTIONS_COUNT contextual follow-ups to the last Q&A turn."""
        settings = get_settings()
        prompt = prompts.FOLLOWUP_QUESTIONS_PROMPT_TEMPLATE.format(
            followup_questions_count=settings.FOLLOWUP_QUESTIONS_COUNT,
            question=question,
            answer=answer,
            context=context[:_MAX_CONTEXT_CHARS] or "(no additional context)",
        )
        questions = self._llm_service.generate_structured(prompt, prompts.SUGGESTED_QUESTIONS_RESPONSE_SCHEMA)
        return self._normalize(questions, settings.FOLLOWUP_QUESTIONS_COUNT)

    @staticmethod
    def _normalize(questions: Any, expected_count: int) -> list[str]:
        """Defensively coerce the model's JSON array into a clean list[str], capped at the expected count."""
        if not isinstance(questions, list):
            return []
        cleaned = [str(question).strip() for question in questions if str(question).strip()]
        return cleaned[:expected_count]

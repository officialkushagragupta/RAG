"""
LLM service (Gemini 2.5 Flash via google-generativeai).
"""

import json
from typing import Any

import google.generativeai as genai

from app.core.config import get_settings
from app.core.gemini_client import configure_gemini


class LLMService:
    """
    Thin wrapper around the Gemini chat model (Settings.GEMINI_MODEL_NAME),
    used by RAGService and QuestionService for all text generation calls.

    Callers (RAGService/QuestionService) are responsible for rendering the
    full prompt text (via core.prompts templates) before calling this --
    this class only knows how to talk to Gemini, not what to say to it.
    """

    def __init__(self) -> None:
        configure_gemini()
        settings = get_settings()
        self._model_name = settings.GEMINI_MODEL_NAME

    def generate(self, prompt: str) -> str:
        """Generate a free-text completion for a single fully-rendered prompt."""
        model = genai.GenerativeModel(self._model_name)
        response = model.generate_content(prompt)
        return (response.text or "").strip()

    def generate_structured(self, prompt: str, response_schema: Any) -> Any:
        """
        Generate a completion constrained to `response_schema` using
        Gemini's structured/JSON output mode, returning already-parsed
        JSON. `response_schema` is typically a plain Python type (e.g.
        `list[str]`, see core.prompts.SUGGESTED_QUESTIONS_RESPONSE_SCHEMA)
        -- `google-generativeai` converts it to the wire schema itself.

        Used by QuestionService for suggested-question generation so
        callers never need to parse free-form text into a list of strings.
        """
        model = genai.GenerativeModel(
            self._model_name,
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
                response_schema=response_schema,
            ),
        )
        response = model.generate_content(prompt)
        return json.loads(response.text)

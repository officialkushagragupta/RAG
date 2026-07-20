"""
Gemini (Google Generative AI) client wiring.

Configures the `google-generativeai` SDK with the API key from Settings and
provides a startup credential-verification helper. This is infrastructure
(auth/connectivity), not RAG logic -- prompting/generation belongs in
app.services.llm_service.
"""

import google.generativeai as genai

from app.core.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

_configured = False


def configure_gemini() -> None:
    """Configure the Google Generative AI SDK with the API key from Settings."""
    global _configured
    settings = get_settings()
    genai.configure(api_key=settings.GEMINI_API_KEY)
    _configured = True
    logger.info("Gemini SDK configured (model=%s).", settings.GEMINI_MODEL_NAME)


def verify_gemini_credentials() -> bool:
    """
    Verify Gemini API credentials are valid by listing available models.

    Raises whatever exception the SDK raises (e.g. on an invalid/missing API
    key) -- callers (main.py lifespan, /health) decide whether that should
    be fatal or just reported.
    """
    if not _configured:
        configure_gemini()

    models = list(genai.list_models())
    if not models:
        raise RuntimeError("Gemini credential check returned zero available models.")

    logger.info("Gemini credentials verified (%d models available).", len(models))
    return True

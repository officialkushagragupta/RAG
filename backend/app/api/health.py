"""
Health check endpoint.

Reports liveness plus the live status of external dependencies (ChromaDB,
Gemini). Mounted at top-level /health (unversioned) in main.py so infra
probes (Docker healthcheck, k8s, load balancers) don't need to track API
version prefixes.
"""

from datetime import datetime, timezone

from fastapi import APIRouter

from app.core.chroma_client import verify_chroma_connection
from app.core.config import get_settings
from app.core.gemini_client import verify_gemini_credentials
from app.models.schemas import HealthResponse

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse, summary="Health check")
async def health_check() -> HealthResponse:
    """Return liveness status plus a live check of ChromaDB and Gemini connectivity."""
    settings = get_settings()

    try:
        verify_chroma_connection()
        chroma_status = "ok"
    except Exception as exc:  # noqa: BLE001 - deliberately broad: report any dependency failure
        chroma_status = f"unavailable: {exc}"

    try:
        verify_gemini_credentials()
        gemini_status = "ok"
    except Exception as exc:  # noqa: BLE001
        gemini_status = f"unavailable: {exc}"

    overall = "healthy" if chroma_status == "ok" and gemini_status == "ok" else "degraded"

    return HealthResponse(
        status=overall,
        environment=settings.ENVIRONMENT,
        version=settings.APP_VERSION,
        chroma_status=chroma_status,
        gemini_status=gemini_status,
        timestamp=datetime.now(timezone.utc),
    )

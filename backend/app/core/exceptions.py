"""
Custom application exceptions and their FastAPI exception handlers.

Service/API code should raise these (or a subclass) instead of raw
HTTPException where the error is domain-specific -- the handlers registered
here convert them into a consistent ErrorResponse JSON body.
"""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.models.schemas import ErrorResponse
from app.utils.constants import ErrorCode
from app.utils.logger import get_logger

logger = get_logger(__name__)


class AppException(Exception):
    """Base class for all application-specific exceptions."""

    error_code: str = ErrorCode.INTERNAL_ERROR
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR

    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


class NoActiveDocumentError(AppException):
    """Raised when an operation (e.g. chat) is attempted before any document has been uploaded."""

    error_code = ErrorCode.NO_ACTIVE_DOCUMENT
    status_code = status.HTTP_404_NOT_FOUND


class ChromaConnectionError(AppException):
    """Raised when the ChromaDB backend is unreachable."""

    error_code = ErrorCode.CHROMA_UNAVAILABLE
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE


class GeminiCredentialError(AppException):
    """Raised when Gemini API credentials are missing or invalid."""

    error_code = ErrorCode.GEMINI_UNAVAILABLE
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE


def register_exception_handlers(app: FastAPI) -> None:
    """Register handlers that convert AppException subclasses into structured JSON responses."""

    @app.exception_handler(AppException)
    async def handle_app_exception(request: Request, exc: AppException) -> JSONResponse:
        logger.warning(
            "%s: %s (%s %s)", exc.error_code, exc.detail, request.method, request.url.path
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(error_code=exc.error_code, detail=exc.detail).model_dump(mode="json"),
        )

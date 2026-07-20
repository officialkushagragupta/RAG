"""
FastAPI application entrypoint.

Wires together configuration, logging, startup/shutdown lifecycle checks
(ChromaDB + Gemini connectivity), CORS, request logging middleware,
exception handlers, and API routers. No business logic lives here.
"""

from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.api.router import api_router
from app.core.chroma_client import verify_chroma_connection
from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.gemini_client import configure_gemini, verify_gemini_credentials
from app.middleware.logging_middleware import RequestLoggingMiddleware
from app.utils.logger import get_logger, setup_logging

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.

    On startup: configure logging, then verify Gemini credentials and the
    ChromaDB connection before accepting traffic -- either failure raises
    and aborts startup (fail fast on bad configuration).
    On shutdown: log the shutdown event. No external resources currently
    need explicit teardown (the Chroma client and Gemini SDK don't hold
    connections that require closing).
    """
    settings = get_settings()
    setup_logging(settings)
    logger.info("Starting %s v%s (%s)...", settings.APP_NAME, settings.APP_VERSION, settings.ENVIRONMENT)

    configure_gemini()
    verify_gemini_credentials()
    verify_chroma_connection()

    logger.info("Startup checks passed. Application ready.")
    yield
    logger.info("Shutting down %s...", settings.APP_NAME)


def create_app() -> FastAPI:
    """Application factory: builds and configures the FastAPI instance."""
    settings = get_settings()

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestLoggingMiddleware)

    register_exception_handlers(app)

    app.include_router(health_router)
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    return app


app = create_app()


if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)

# syntax=docker/dockerfile:1

FROM python:3.11-slim

WORKDIR /app

# System deps: build tools for any wheel-less packages, curl for the healthcheck.
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Directories that get volume-mounted in docker-compose for persistence.
RUN mkdir -p uploads chroma_db logs

# Run as a non-root user.
RUN useradd --create-home appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Shell form (not exec/array form) so ${PORT} actually expands -- hosts like
# Render assign their own port via a PORT env var and expect the container to
# listen on it; 8000 is the local/docker-compose fallback when PORT is unset.
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}

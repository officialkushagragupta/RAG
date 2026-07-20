"""
API layer.

HTTP route handlers only (FastAPI routers). Each module owns one resource:
upload.py (the single active document: upload/get/clear), chat.py
(question answering + history), health.py (liveness/readiness). Routers
are aggregated in router.py and mounted onto the app in main.py.

There is no session concept -- this app has exactly one active document
at a time (see README's "Architecture Constraints").

Handlers should validate input, delegate real work to services/, and shape
the response using models/schemas.py -- they should not contain business logic.
"""

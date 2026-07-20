"""
API router aggregation.

Combines every resource router into a single `api_router`, mounted under
Settings.API_V1_PREFIX in main.py. health.py is mounted separately at
top-level (unversioned) since it's an infra probe, not a versioned resource.
"""

from fastapi import APIRouter

from app.api import chat, upload

api_router = APIRouter()
api_router.include_router(upload.router)
api_router.include_router(chat.router)

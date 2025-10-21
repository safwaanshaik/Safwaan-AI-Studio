"""
SAFWAAN AI STUDIO - API Router
Main API router that combines all endpoint modules.

This module provides:
- Centralized API routing
- Version management
- API documentation
- Request/response middleware
"""

from fastapi import APIRouter

from app.api.v1.endpoints import auth, users, projects, videos, analytics, billing

# Create main API router
api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["authentication"]
)

api_router.include_router(
    users.router,
    prefix="/users",
    tags=["users"]
)

api_router.include_router(
    projects.router,
    prefix="/projects",
    tags=["projects"]
)

api_router.include_router(
    videos.router,
    prefix="/videos",
    tags=["videos"]
)

api_router.include_router(
    analytics.router,
    prefix="/analytics",
    tags=["analytics"]
)

api_router.include_router(
    billing.router,
    prefix="/billing",
    tags=["billing"]
)
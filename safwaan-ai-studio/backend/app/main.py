"""
SAFWAAN AI STUDIO - FastAPI Application
Main application entry point with comprehensive middleware and routing.

This module provides:
- FastAPI application setup
- Middleware configuration (CORS, security, logging)
- Route registration
- Health checks and monitoring
- Graceful shutdown handling
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from app.core.config import settings
from app.core.database import init_db, close_db
from app.core.cache import init_cache, close_cache
from app.core.monitoring import init_monitoring
from app.core.logger import setup_logging
from app.api.v1.api import api_router
from app.utils.exceptions import SafwaanAIException, create_error_response

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging HTTP requests."""

    async def dispatch(self, request: Request, call_next):
        import time
        start_time = time.time()

        # Log request
        logger.info(f"Request: {request.method} {request.url.path}")

        try:
            response = await call_next(request)

            # Log response
            process_time = time.time() - start_time
            logger.info(
                f"Response: {request.method} {request.url.path} "
                f"Status: {response.status_code} Time: {process_time:.3f}s"
            )

            return response

        except Exception as e:
            # Log error
            process_time = time.time() - start_time
            logger.error(
                f"Error: {request.method} {request.url.path} "
                f"Time: {process_time:.3f}s Error: {str(e)}"
            )
            raise


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware for adding security headers."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        return response


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context manager."""
    logger.info("Starting Safwaan AI Studio...")

    # Initialize services
    await init_db()
    await init_cache()
    await init_monitoring()

    logger.info("All services initialized successfully")

    yield

    # Cleanup
    logger.info("Shutting down Safwaan AI Studio...")

    await close_cache()
    await close_db()

    logger.info("Shutdown complete")


def create_application() -> FastAPI:
    """Create and configure FastAPI application."""

    app = FastAPI(
        title="Safwaan AI Studio API",
        description="Enterprise-grade AI video generation platform",
        version="5.0.0",
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan
    )

    # Set up middleware
    setup_middleware(app)

    # Set up exception handlers
    setup_exception_handlers(app)

    # Include routers
    app.include_router(api_router, prefix=settings.API_V1_STR)

    # Health check endpoint
    @app.get("/health")
    async def health_check():
        """Basic health check endpoint."""
        return {"status": "healthy", "version": "5.0.0"}

    # Detailed health check
    @app.get("/health/detailed")
    async def detailed_health_check():
        """Detailed health check with service status."""
        from app.core.monitoring import monitoring_manager
        return await monitoring_manager.health_check()

    # Metrics endpoint (Prometheus)
    @app.get("/metrics")
    async def metrics():
        """Prometheus metrics endpoint."""
        from app.core.monitoring import monitoring_manager
        return Response(
            content=monitoring_manager.get_metrics(),
            media_type="text/plain; charset=utf-8"
        )

    return app


def setup_middleware(app: FastAPI) -> None:
    """Configure application middleware."""

    # CORS middleware
    if settings.BACKEND_CORS_ORIGINS:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # Trusted host middleware
    if not settings.DEBUG:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=settings.ALLOWED_HOSTS
        )

    # Custom middleware
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)


def setup_exception_handlers(app: FastAPI) -> None:
    """Configure global exception handlers."""

    @app.exception_handler(SafwaanAIException)
    async def safwaan_exception_handler(request: Request, exc: SafwaanAIException):
        """Handle SafwaanAI custom exceptions."""
        return JSONResponse(
            status_code=exc.status_code,
            content=create_error_response(exc),
            headers=exc.headers
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle unexpected exceptions."""
        logger.error(f"Unhandled exception: {exc}", exc_info=True)

        from app.core.monitoring import record_error
        record_error("unhandled_exception", "system")

        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "type": "internal_error"
            }
        )


# Create application instance
app = create_application()


if __name__ == "__main__":
    # Development server
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info"
    )
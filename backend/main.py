"""FastAPI application entry point for AnimationCreator backend."""

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

import sentry_sdk
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.animations import router as animations_router
from app.api.assets import router as assets_router
from app.api.auth import router as auth_router
from app.api.billing import router as billing_router
from app.api.characters import router as characters_router
from app.api.events import router as events_router
from app.api.generate import router as generate_router
from app.api.users import router as users_router
from app.core.config import get_settings
from app.core.database import close_db, init_db
from app.core.middleware import AuthenticationError, InsufficientCreditsError
from app.core.storage_config import get_storage_settings

settings = get_settings()

# Initialize Sentry if DSN is provided
if settings.sentry_dsn:
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.environment,
        traces_sample_rate=1.0 if settings.environment == "development" else 0.1,
        profiles_sample_rate=1.0 if settings.environment == "development" else 0.1,
        enable_tracing=True,
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan handler for startup and shutdown events.

    Handles database initialization on startup and cleanup on shutdown.
    """
    # Startup
    await init_db()
    yield
    # Shutdown
    await close_db()


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AnimationCreator - Generate and animate characters with AI",
    docs_url="/api/docs" if settings.debug else None,
    redoc_url="/api/redoc" if settings.debug else None,
    openapi_url="/api/openapi.json" if settings.debug else None,
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_allow_methods,
    allow_headers=settings.cors_allow_headers,
)


# Exception handlers


@app.exception_handler(AuthenticationError)
async def authentication_error_handler(
    request: Request,
    exc: AuthenticationError,
) -> JSONResponse:
    """Handle authentication errors."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=exc.headers,
    )


@app.exception_handler(InsufficientCreditsError)
async def insufficient_credits_error_handler(
    request: Request,
    exc: InsufficientCreditsError,
) -> JSONResponse:
    """Handle insufficient credits errors."""
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.detail,
    )


# Include routers
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(billing_router)
app.include_router(assets_router)
app.include_router(events_router)
app.include_router(generate_router)
app.include_router(characters_router)
app.include_router(animations_router)


# Health check endpoint


@app.get("/api/health", tags=["health"])
async def health_check() -> dict[str, str]:
    """
    Health check endpoint.

    Returns the application status and version.
    """
    return {
        "status": "healthy",
        "version": settings.app_version,
        "environment": settings.environment,
    }


@app.get("/", tags=["root"])
async def root() -> dict[str, str]:
    """Root endpoint with basic API info."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/api/docs" if settings.debug else "Documentation disabled in production",
    }


# Mount local uploads directory for development
storage_settings = get_storage_settings()
if storage_settings.storage_mode == "local":
    uploads_path = Path(storage_settings.local_storage_path)
    uploads_path.mkdir(parents=True, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=str(uploads_path)), name="uploads")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
    )

"""
FastAPI application entry point for BiZhen system.

Main application configuration including:
- CORS middleware setup
- Router registration
- Database initialization
- Health check endpoint
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.db.session import init_db
from backend.api import api_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan handler.

    Initializes database tables on startup.
    """
    # Startup: Initialize database
    init_db()
    yield
    # Shutdown: Cleanup if needed


# Create FastAPI application
app = FastAPI(
    title="BiZhen API",
    description="Multi-Agent Essay Generation System for Chinese Gaokao",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

# Include API routers
app.include_router(api_router, prefix=settings.api_prefix)

# Mount static files
app.mount("/static", StaticFiles(directory="backend/static"), name="static")


@app.get("/health", tags=["Health"])
def health_check() -> dict:
    """
    Health check endpoint.

    Returns service status for container orchestration.
    """
    return {
        "status": "healthy",
        "service": "bizhen-backend",
        "version": "1.0.0",
    }


@app.get("/", tags=["Root"])
def root() -> dict:
    """
    Root endpoint with API information.
    """
    return {
        "service": "BiZhen API",
        "version": "1.0.0",
        "docs": "/api/docs",
        "health": "/health",
    }

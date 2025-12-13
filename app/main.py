"""FastAPI application main entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from app.api.v1.endpoints import health, tasks, upload
from app.config import settings
from app.core.assetripper import assetripper_manager
from app.core.task_queue import task_queue_manager
from app.database import close_db, init_db

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.

    Handles startup and shutdown events.
    """
    # Startup
    logger.info(f"Starting AssetRipper API Server (Environment: {settings.environment})")

    # Ensure directories exist
    settings.ensure_directories()
    logger.info("Ensured required directories exist")

    # Initialize database
    await init_db()
    logger.info("Database initialized")

    # Start AssetRipper manager
    try:
        await assetripper_manager.start()
        logger.info("AssetRipper manager started")
    except Exception as e:
        logger.error(f"Failed to start AssetRipper: {e}")
        raise

    # Start task queue manager
    try:
        await task_queue_manager.start()
        logger.info("Task queue manager started")
    except Exception as e:
        logger.error(f"Failed to start task queue: {e}")
        raise

    logger.info(f"AssetRipper API Server started on {settings.api_host}:{settings.api_port}")

    yield

    # Shutdown
    logger.info("Shutting down AssetRipper API Server...")

    # Stop task queue manager
    try:
        await task_queue_manager.stop()
        logger.info("Task queue manager stopped")
    except Exception as e:
        logger.error(f"Error stopping task queue: {e}")

    # Stop AssetRipper manager
    try:
        await assetripper_manager.stop()
        logger.info("AssetRipper manager stopped")
    except Exception as e:
        logger.error(f"Error stopping AssetRipper: {e}")

    # Close database
    try:
        await close_db()
        logger.info("Database connections closed")
    except Exception as e:
        logger.error(f"Error closing database: {e}")

    logger.info("AssetRipper API Server stopped")


# Create FastAPI application
app = FastAPI(
    title="AssetRipper API Server",
    description="API service for extracting Unity assets from APK/XAPK/IPA files using AssetRipper",
    version="1.0.0",
    lifespan=lifespan,
)


# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle general exceptions."""
    logger.exception(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if not settings.is_production else None,
        },
    )


# Include routers
app.include_router(upload.router, prefix="/api/v1", tags=["upload"])
app.include_router(tasks.router, prefix="/api/v1", tags=["tasks"])
app.include_router(health.router, prefix="/api/v1", tags=["health"])


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "AssetRipper API Server",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "health": "/api/v1/health",
    }

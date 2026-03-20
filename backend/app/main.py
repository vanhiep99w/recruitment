"""
FastAPI application entry point.

Run with:
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
"""
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import engine
from app.routers.health import router as health_router

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL, logging.INFO))
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lifespan handler (replaces deprecated on_event)
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application startup and shutdown resources."""
    logger.info("Application startup — environment: %s", settings.APP_ENV)
    yield
    await engine.dispose()
    logger.info("Application shutdown — database connections closed")


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------
app = FastAPI(
    title="AI CV & Recruitment Assistant API",
    description=(
        "Backend API for the AI-powered CV screening and recruitment assistant. "
        "Handles CV parsing, candidate management, job matching, and talent pools."
    ),
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(health_router)

# Additional routers will be registered here as feature tasks are completed:
# from app.routers import candidates, jobs, pipelines, talent_pools, upload, export
# app.include_router(candidates.router, prefix="/api")
# app.include_router(jobs.router, prefix="/api")
# app.include_router(pipelines.router, prefix="/api")
# app.include_router(talent_pools.router, prefix="/api")
# app.include_router(upload.router, prefix="/api")
# app.include_router(export.router, prefix="/api")

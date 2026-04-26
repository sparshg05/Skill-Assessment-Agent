"""
FastAPI Application Entry Point

Skill Assessment & Personalised Learning Plan Agent
"""
from __future__ import annotations

import structlog
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import get_settings
from utils import setup_logging
from api import router
from services import close_redis

setup_logging()
logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    settings = get_settings()
    logger.info(
        "app_startup",
        env=settings.app_env,
        provider=settings.llm_provider,
        assessor_model=settings.assessor_model,
    )
    yield
    # Cleanup
    await close_redis()
    logger.info("app_shutdown")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="Skill Assessment & Learning Plan Agent",
        description="""
        An AI-powered agent that:
        - Parses job descriptions and resumes
        - Conversationally assesses real skill proficiency
        - Identifies gaps between requirements and actual knowledge
        - Generates a personalised, prioritised learning roadmap
        """,
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Request logging middleware
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        logger.info(
            "request",
            method=request.method,
            path=request.url.path,
        )
        response = await call_next(request)
        logger.info("response", status=response.status_code)
        return response

    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error("unhandled_exception", path=request.url.path, error=str(exc))
        return JSONResponse(
            status_code=500,
            content={"detail": "An unexpected error occurred. Please try again."},
        )

    # Routes
    app.include_router(router)

    # Health check
    @app.get("/health", tags=["health"])
    async def health():
        return {
            "status": "healthy",
            "provider": settings.llm_provider,
            "assessor_model": settings.assessor_model,
        }

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run(
        "main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.app_env == "development",
        log_level="info",
    )
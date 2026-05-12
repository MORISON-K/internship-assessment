"""
main.py
───────
FastAPI application factory.

Responsibilities
  • Create and configure the FastAPI app instance.
  • Register the lifespan context (opens / closes the shared httpx client).
  • Mount CORS middleware.
  • Install global exception handlers that convert typed exceptions to clean
    JSON responses – no stack traces ever reach the frontend.
  • Include all routers.
"""

from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import get_settings
from .exceptions import SunbirdBaseError, ValidationError
from .models import ErrorResponse
from .routes import router
from .audio_store import AudioStore
from .sunbird_client import SunbirdClient

# ── Logging ───────────────────────────────────────────────────────────────────

def _configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        stream=sys.stdout,
    )


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Open the shared SunbirdClient (and its underlying httpx.AsyncClient) once
    at startup, then close it cleanly on shutdown.
    """
    settings = get_settings()
    client = SunbirdClient(token=settings.sunbird_api_token)
    await client.aopen()
    app.state.sunbird_client = client
    app.state.audio_store = AudioStore()
    logging.getLogger(__name__).info("SunbirdClient ready.")
    try:
        yield
    finally:
        await client.aclose()
        logging.getLogger(__name__).info("SunbirdClient closed.")


# ── Exception handlers ────────────────────────────────────────────────────────

async def _sunbird_exception_handler(
    request: Request, exc: SunbirdBaseError
) -> JSONResponse:
    logging.getLogger(__name__).warning(
        "SunbirdBaseError [%d]: %s", exc.status_code, exc.detail
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            detail=exc.detail,
            error_type=type(exc).__name__,
        ).model_dump(),
    )


async def _validation_exception_handler(
    request: Request, exc: ValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            detail=exc.detail,
            error_type=type(exc).__name__,
        ).model_dump(),
    )


async def _generic_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    logging.getLogger(__name__).exception("Unhandled exception: %s", exc)
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            detail="An unexpected error occurred. Please try again.",
            error_type="InternalServerError",
        ).model_dump(),
    )


# ── App factory ───────────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    settings = get_settings()
    _configure_logging(settings.log_level)

    app = FastAPI(
        title="Sunbird AI Pipeline API",
        description=(
            "Backend for the Sunbird AI internship assessment. "
            "Accepts text or audio, transcribes (audio only), summarises, "
            "translates into a Ugandan local language, and synthesises speech."
        ),
        version="1.0.0",
        lifespan=lifespan,
        # Hide docs in production if desired
        docs_url=None if settings.is_production else "/docs",
        redoc_url=None if settings.is_production else "/redoc",
    )

    # ── CORS ──────────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Exception handlers ────────────────────────────────────────────────────
    app.add_exception_handler(SunbirdBaseError, _sunbird_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(ValidationError, _validation_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, _generic_exception_handler)

    # ── Routes ────────────────────────────────────────────────────────────────
    app.include_router(router, prefix="/api/v1")

    return app


# Singleton used by uvicorn: `uvicorn backend.main:app`
app = create_app()
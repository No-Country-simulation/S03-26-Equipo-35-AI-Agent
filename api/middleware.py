"""Middleware de FastAPI para AutoStory Builder.

Configura:
- CORS dinámico: ["*"] en development, orígenes específicos en production
- Logging estructurado de requests (método, path, status, duración)
"""

import os
import time

import structlog
from fastapi import FastAPI, Request
from starlette.middleware.cors import CORSMiddleware

logger = structlog.get_logger()

# Orígenes permitidos en producción
PRODUCTION_ORIGINS: list[str] = [
    "http://localhost:8501",    # Streamlit local
    "https://autostory-builder.streamlit.app",  # Streamlit Cloud
]


def setup_middleware(app: FastAPI) -> None:
    """Configura todos los middleware de la aplicación.

    CORS se configura según ENVIRONMENT:
    - development: permite todos los orígenes (["*"])
    - production: solo orígenes de la whitelist

    Args:
        app: Instancia de FastAPI a configurar.
    """
    environment = os.getenv("ENVIRONMENT", "development")

    # ── CORS ──
    if environment == "development":
        origins: list[str] = ["*"]
        logger.info("cors_configured", mode="development", origins="*")
    else:
        origins = PRODUCTION_ORIGINS
        logger.info("cors_configured", mode="production", origins=origins)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Request Logging ──
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        """Registra cada request con método, path y duración."""
        start_time = time.perf_counter()

        response = await call_next(request)

        duration_ms = (time.perf_counter() - start_time) * 1000

        # No loguear health checks para evitar ruido
        if request.url.path != "/health":
            logger.info(
                "http_request",
                method=request.method,
                path=str(request.url.path),
                status_code=response.status_code,
                duration_ms=round(duration_ms, 2),
            )

        return response

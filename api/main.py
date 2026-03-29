"""FastAPI application factory para AutoStory Builder.

Punto de entrada principal del backend. Configura la app con:
- Lifespan: verifica conexión a Supabase al arrancar
- Middleware: CORS dinámico + logging estructurado
- Routers: endpoints por dominio
- Health check: /health con estado real de Supabase
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from api.middleware import setup_middleware
from api.routers import approvals, auth, rag, stories
from api.schemas import HealthResponse
from db.client import check_connection

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Gestiona el ciclo de vida de la aplicación.

    Startup: verifica conexión a Supabase.
    Si Supabase no responde → warning pero NO crashea.
    Shutdown: cierra conexiones limpiamente.
    """
    # ── Startup ──
    logger.info("autostory_startup", status="iniciando")

    # Verificar conexión a Supabase — no bloquea si falla
    supabase_ok = check_connection()
    if supabase_ok:
        logger.info("autostory_startup", supabase="connected")
    else:
        logger.warning(
            "autostory_startup",
            supabase="unreachable",
            hint="Verificar SUPABASE_URL y SUPABASE_KEY en .env",
        )

    logger.info("autostory_startup", status="listo")

    yield

    # ── Shutdown ──
    logger.info("autostory_shutdown", status="cerrado")


def create_app() -> FastAPI:
    """Crea y configura la aplicación FastAPI.

    Returns:
        Instancia de FastAPI configurada con routers y middleware.
    """
    app = FastAPI(
        title="AutoStory Builder API",
        description="API para generación de contenido narrativo con IA",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Middleware (CORS + logging)
    setup_middleware(app)

    # Routers por dominio
    app.include_router(auth.router, prefix="/auth", tags=["auth"])
    app.include_router(stories.router, prefix="/stories", tags=["stories"])
    app.include_router(rag.router, prefix="/rag", tags=["rag"])
    app.include_router(approvals.router, prefix="/approvals", tags=["approvals"])

    return app


app = create_app()


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Endpoint de health check para monitoreo y Fly.io.

    Verifica conexión a Supabase con query simple.
    Siempre retorna 200 — el campo 'supabase' indica el estado real.
    No requiere autenticación.
    """
    supabase_status = "connected" if check_connection() else "unreachable"

    return HealthResponse(
        status="ok",
        version="0.1.0",
        supabase=supabase_status,
    )


@app.get("/")
async def root() -> dict[str, str]:
    """Endpoint raíz informativo."""
    return {
        "message": "AutoStory Builder API",
        "docs": "/docs",
    }

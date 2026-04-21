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
from api.routers import approvals, golden_examples, rag, stories
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

    # Verificar conexión a Redis — no bloquea si falla
    from core.cache.redis_client import is_redis_available

    redis_ok = is_redis_available()
    if redis_ok:
        logger.info("autostory_startup", redis="connected")
    else:
        logger.info("autostory_startup", redis="not_configured", hint="Opcional: UPSTASH_REDIS_URL")

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

    app.include_router(stories.router, prefix="/stories", tags=["stories"])
    app.include_router(rag.router, prefix="/rag", tags=["rag"])
    app.include_router(approvals.router, prefix="/approvals", tags=["approvals"])
    app.include_router(golden_examples.router, prefix="/golden-examples", tags=["golden-examples"])

    return app


app = create_app()


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Endpoint de health check para monitoreo y Fly.io.

    Verifica conexión a Supabase y Redis.
    Siempre retorna 200 — los campos indican el estado real.
    No requiere autenticación.
    """
    from core.cache.redis_client import is_redis_available

    supabase_status = "connected" if check_connection() else "unreachable"
    redis_status = "connected" if is_redis_available() else "not_configured"

    return HealthResponse(
        status="ok",
        version="0.1.0",
        supabase=supabase_status,
        redis=redis_status,
    )


@app.get("/")
async def root() -> dict[str, str]:
    """Endpoint raíz informativo."""
    return {
        "message": "AutoStory Builder API",
        "docs": "/docs",
    }


@app.get("/public/{share_token}")
async def public_story(share_token: str):
    """Endpoint público para historias compartidas.

    No requiere autenticación — accesible por cualquiera con el link.
    Retorna una página HTML completa con la historia formateada.
    """
    from fastapi.responses import HTMLResponse

    from core.export.html_renderer import render_story_html
    from db.client import get_admin_client

    client = get_admin_client()

    result = (
        client.table("stories")
        .select("id, title, content, story_type, created_at, share_token")
        .eq("share_token", share_token)
        .execute()
    )

    if not result.data:
        return HTMLResponse(
            content="<h1>Historia no encontrada</h1><p>El link puede haber sido revocado.</p>",
            status_code=404,
        )

    row = result.data[0]
    html = render_story_html(
        title=row["title"],
        content=row["content"],
        story_type=row.get("story_type", "blog"),
        created_at=row.get("created_at", ""),
    )

    return HTMLResponse(content=html)

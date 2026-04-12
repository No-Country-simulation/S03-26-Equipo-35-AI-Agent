"""Rate limiter para FastAPI con Upstash Redis.

Implementa rate limiting como dependency injectable de FastAPI.
Usa Redis sliding window counter (INCR + EXPIRE).

Fallback graceful: si Redis no está disponible, deja pasar todo.

Límites generosos (fase de pruebas):
- Generación de historias: 20/hora por usuario
- Generación de imágenes: 10/hora por usuario
- Ingestión RAG: 30/hora por usuario
- Global: 120/minuto por usuario
"""

import os

import structlog
from fastapi import HTTPException, Request, status

from core.cache.redis_client import rate_limit_check

logger = structlog.get_logger()

# Límites configurables por variable de entorno (en caso de querer ajustar sin deploy)
RATE_LIMIT_GENERATE = int(os.getenv("RATE_LIMIT_GENERATE", "20"))
RATE_LIMIT_IMAGE = int(os.getenv("RATE_LIMIT_IMAGE", "10"))
RATE_LIMIT_INGEST = int(os.getenv("RATE_LIMIT_INGEST", "30"))
RATE_LIMIT_GLOBAL = int(os.getenv("RATE_LIMIT_GLOBAL", "120"))


async def _extract_user_id(request: Request) -> str:
    """Extrae un identificador único del request para rate limiting.

    Prioriza user_id del JWT si está disponible, luego IP del cliente.

    Args:
        request: Request de FastAPI.

    Returns:
        Identifier string del usuario.
    """
    # Si hay JWT parseado en el state del request
    if hasattr(request.state, "user_id"):
        return request.state.user_id

    # Fallback: usar la IP del cliente
    client_host = request.client.host if request.client else "unknown"
    return f"ip:{client_host}"


async def rate_limit_generation(request: Request) -> None:
    """Dependency de rate limiting para el endpoint de generación.

    Límite: 20 generaciones por hora por usuario.

    Raises:
        HTTPException 429 si se excede el límite.
    """
    user_id = await _extract_user_id(request)
    allowed, remaining = await rate_limit_check(
        identifier=f"generate:{user_id}",
        limit=RATE_LIMIT_GENERATE,
        window_seconds=3600,  # 1 hora
    )

    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"Límite de generación alcanzado ({RATE_LIMIT_GENERATE}/hora). "
                "Intentá de nuevo en unos minutos."
            ),
            headers={"Retry-After": "300", "X-RateLimit-Remaining": "0"},
        )

    # Agregar header informativo al response
    request.state.rate_limit_remaining = remaining


async def rate_limit_image(request: Request) -> None:
    """Dependency de rate limiting para generación de imágenes.

    Límite: 10 imágenes por hora por usuario.

    Raises:
        HTTPException 429 si se excede el límite.
    """
    user_id = await _extract_user_id(request)
    allowed, _remaining = await rate_limit_check(
        identifier=f"image:{user_id}",
        limit=RATE_LIMIT_IMAGE,
        window_seconds=3600,
    )

    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"Límite de imágenes alcanzado ({RATE_LIMIT_IMAGE}/hora). "
                "Intentá de nuevo en unos minutos."
            ),
            headers={"Retry-After": "300"},
        )


async def rate_limit_ingest(request: Request) -> None:
    """Dependency de rate limiting para ingestión RAG.

    Límite: 30 ingestiones por hora por usuario.

    Raises:
        HTTPException 429 si se excede el límite.
    """
    user_id = await _extract_user_id(request)
    allowed, _remaining = await rate_limit_check(
        identifier=f"ingest:{user_id}",
        limit=RATE_LIMIT_INGEST,
        window_seconds=3600,
    )

    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"Límite de ingestión alcanzado ({RATE_LIMIT_INGEST}/hora). "
                "Intentá de nuevo en unos minutos."
            ),
            headers={"Retry-After": "300"},
        )


async def rate_limit_global(request: Request) -> tuple[bool, int]:
    """Rate limiter global — se usa como middleware.

    Límite: 120 requests por minuto por usuario.

    Returns:
        Tupla (allowed, remaining). No lanza excepción — el middleware decide.
    """
    user_id = await _extract_user_id(request)
    return await rate_limit_check(
        identifier=f"global:{user_id}",
        limit=RATE_LIMIT_GLOBAL,
        window_seconds=60,  # 1 minuto
    )

"""Cliente centralizado de Upstash Redis.

Provee funciones helper para caché, rate limiting y estado de jobs.
Diseñado con fallback graceful: si Redis no está configurado o falla,
las funciones retornan None sin romper la aplicación.

Configuración en .env:
    UPSTASH_REDIS_URL=https://xxx.upstash.io
    UPSTASH_REDIS_TOKEN=AXxx...

Free tier (Upstash): 10,000 comandos/día — suficiente para desarrollo.
"""

import hashlib
import json
import os
from typing import Any

import structlog
from dotenv import load_dotenv

load_dotenv()

logger = structlog.get_logger()

# Singleton del cliente Redis
_redis_client = None
_redis_available = False


def _init_redis():
    """Inicializa el cliente Redis si las variables están configuradas.

    Se llama una sola vez (lazy init). Si las variables no existen
    o la conexión falla, marca Redis como no disponible.
    """
    global _redis_client, _redis_available

    url = os.getenv("UPSTASH_REDIS_URL", "")
    token = os.getenv("UPSTASH_REDIS_TOKEN", "")

    if not url or not token:
        logger.info("redis_not_configured", hint="UPSTASH_REDIS_URL y UPSTASH_REDIS_TOKEN vacíos")
        _redis_available = False
        return

    try:
        from upstash_redis import Redis

        _redis_client = Redis(url=url, token=token)
        # Test de conexión
        _redis_client.ping()
        _redis_available = True
        logger.info("redis_connected", url=url[:30] + "...")
    except Exception as e:
        logger.warning("redis_connection_failed", error=str(e)[:100])
        _redis_available = False
        _redis_client = None


def get_redis():
    """Retorna el cliente Redis o None si no está disponible.

    Returns:
        Instancia de upstash_redis.Redis o None.
    """
    global _redis_client, _redis_available

    if _redis_client is None and not _redis_available:
        _init_redis()

    return _redis_client


def is_redis_available() -> bool:
    """Verifica si Redis está disponible y conectado.

    Returns:
        True si Redis responde a PING, False en caso contrario.
    """
    client = get_redis()
    if client is None:
        return False

    try:
        client.ping()
        return True
    except Exception:
        return False


# ── Helpers de Caché ──


def make_cache_key(*parts: str) -> str:
    """Construye una cache key consistente a partir de partes.

    Para queries largas, usa SHA256 para evitar keys excesivamente largas.

    Args:
        *parts: Partes de la key (se unen con ':').

    Returns:
        Cache key como string.
    """
    raw = ":".join(parts)
    if len(raw) > 200:
        hashed = hashlib.sha256(raw.encode()).hexdigest()[:16]
        return f"{parts[0]}:{hashed}"
    return raw


async def cache_get(key: str) -> Any | None:
    """Lee un valor del caché.

    Args:
        key: Cache key.

    Returns:
        Valor deserializado o None si no existe / Redis no disponible.
    """
    client = get_redis()
    if client is None:
        return None

    try:
        value = client.get(key)
        if value is None:
            return None

        # Si es string JSON, deserializar
        if isinstance(value, str):
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value

        return value
    except Exception as e:
        logger.warning("cache_get_failed", key=key[:50], error=str(e)[:80])
        return None


async def cache_set(key: str, value: Any, ttl_seconds: int = 3600) -> bool:
    """Escribe un valor al caché con TTL.

    Args:
        key: Cache key.
        value: Valor a almacenar (se serializa a JSON si es dict/list).
        ttl_seconds: Tiempo de vida en segundos. Default: 1 hora.

    Returns:
        True si se guardó exitosamente, False en caso de error.
    """
    client = get_redis()
    if client is None:
        return False

    try:
        # Serializar a JSON si es dict/list
        if isinstance(value, (dict, list)):
            serialized = json.dumps(value, default=str)
        else:
            serialized = str(value)

        client.set(key, serialized, ex=ttl_seconds)
        return True
    except Exception as e:
        logger.warning("cache_set_failed", key=key[:50], error=str(e)[:80])
        return False


async def cache_delete(key: str) -> bool:
    """Elimina una key del caché.

    Args:
        key: Cache key a eliminar.

    Returns:
        True si se eliminó, False en caso de error.
    """
    client = get_redis()
    if client is None:
        return False

    try:
        client.delete(key)
        return True
    except Exception as e:
        logger.warning("cache_delete_failed", key=key[:50], error=str(e)[:80])
        return False


# ── Helpers de Rate Limiting ──


async def rate_limit_check(
    identifier: str,
    limit: int,
    window_seconds: int,
) -> tuple[bool, int]:
    """Verifica si un identifier excedió su rate limit (sliding window).

    Usa INCR + EXPIRE en Redis para contar requests en la ventana.

    Args:
        identifier: Key única (ej: 'generate:{user_id}').
        limit: Número máximo de requests permitidos en la ventana.
        window_seconds: Duración de la ventana en segundos.

    Returns:
        Tupla (allowed: bool, remaining: int).
        Si Redis no está disponible, siempre retorna (True, limit).
    """
    client = get_redis()
    if client is None:
        return True, limit  # Sin Redis → sin límite

    key = f"ratelimit:{identifier}"

    try:
        current = client.incr(key)

        # Si es el primer request en la ventana, setear TTL
        if current == 1:
            client.expire(key, window_seconds)

        remaining = max(0, limit - current)
        allowed = current <= limit

        if not allowed:
            logger.info(
                "rate_limit_exceeded",
                identifier=identifier[:50],
                current=current,
                limit=limit,
            )

        return allowed, remaining
    except Exception as e:
        logger.warning("rate_limit_check_failed", error=str(e)[:80])
        return True, limit  # Fallback: permitir


# ── Helpers de Background Jobs ──


async def job_set_status(
    job_id: str,
    status: str,
    progress: str = "",
    result: dict[str, Any] | None = None,
    ttl_seconds: int = 3600,
) -> bool:
    """Actualiza el estado de un job en Redis.

    Args:
        job_id: ID único del job.
        status: Estado actual ('queued', 'processing', 'completed', 'failed').
        progress: Mensaje de progreso para mostrar en el frontend.
        result: Resultado final (solo cuando status='completed').
        ttl_seconds: TTL del job en Redis. Default: 1 hora.

    Returns:
        True si se actualizó exitosamente.
    """
    job_data = {
        "status": status,
        "progress": progress,
    }
    if result is not None:
        job_data["result"] = result

    return await cache_set(f"job:{job_id}", job_data, ttl_seconds=ttl_seconds)


async def job_get_status(job_id: str) -> dict[str, Any] | None:
    """Lee el estado actual de un job.

    Args:
        job_id: ID único del job.

    Returns:
        Dict con status, progress y opcionalmente result. None si no existe.
    """
    return await cache_get(f"job:{job_id}")

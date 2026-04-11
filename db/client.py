"""Cliente Supabase para AutoStory Builder.

Expone dos funciones para obtener clientes Supabase:
- get_client(): Cliente con anon key — respeta RLS.
- get_admin_client(): Cliente con service key — bypasea RLS.

Ambos clientes se inicializan de forma lazy y se cachean como singletons.
Este módulo es independiente del framework (sin imports de FastAPI).
"""

import os

import structlog
from dotenv import load_dotenv
from supabase import Client, create_client

load_dotenv()

logger = structlog.get_logger()

# Singletons — se inicializan en la primera llamada
_client: Client | None = None
_admin_client: Client | None = None


def get_client() -> Client:
    """Retorna un cliente Supabase con anon key (respeta RLS).

    Usa la anon key que respeta Row Level Security. Adecuado para
    operaciones en el contexto del usuario autenticado.

    Returns:
        Cliente Supabase configurado con anon key.

    Raises:
        ValueError: Si SUPABASE_URL o SUPABASE_KEY no están configuradas.
    """
    global _client

    if _client is not None:
        return _client

    url: str | None = os.getenv("SUPABASE_URL")
    key: str | None = os.getenv("SUPABASE_KEY")

    if not url or not key:
        msg = (
            "SUPABASE_URL y SUPABASE_KEY deben estar configuradas en .env. "
            "Obtenerlas desde: Supabase Dashboard → Settings → API"
        )
        raise ValueError(msg)

    _client = create_client(url, key)
    logger.info("supabase_client_initialized", type="anon")
    return _client


def get_admin_client() -> Client:
    """Retorna un cliente Supabase con service key (bypasea RLS).

    Usa la service_role key que ignora Row Level Security.
    SOLO para operaciones server-side que necesitan acceso
    sin restricciones (ej: migraciones, admin tasks).

    Returns:
        Cliente Supabase configurado con service_role key.

    Raises:
        ValueError: Si SUPABASE_URL o SUPABASE_SERVICE_KEY no están configuradas.
    """
    global _admin_client

    if _admin_client is not None:
        return _admin_client

    url: str | None = os.getenv("SUPABASE_URL")
    service_key: str | None = os.getenv("SUPABASE_SERVICE_KEY")

    if not url or not service_key:
        msg = (
            "SUPABASE_URL y SUPABASE_SERVICE_KEY deben estar configuradas en .env. "
            "Obtener service_role key desde: Supabase Dashboard → Settings → API"
        )
        raise ValueError(msg)

    _admin_client = create_client(url, service_key)
    logger.info("supabase_client_initialized", type="admin")
    return _admin_client


def check_connection() -> bool:
    """Verifica que la conexión a Supabase esté activa.

    Intenta una query simple. Usa nivel WARNING si falla
    para no alarmar en desarrollo.

    Returns:
        True si la conexión es exitosa, False en caso contrario.
    """
    try:
        client = get_client()
        client.table("organizations").select("id").limit(1).execute()
        return True
    except ValueError:
        logger.warning("supabase_check_failed", reason="env_vars_missing")
        return False
    except Exception as e:
        logger.warning("supabase_check_failed", reason=str(e)[:100])
        return False

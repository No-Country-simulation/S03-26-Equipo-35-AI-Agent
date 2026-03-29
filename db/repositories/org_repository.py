"""Repositorio de organizaciones (organizations).

Acceso a la tabla `organizations` en Supabase.
"""

from typing import Any

from supabase import Client


async def get_org_by_id(
    client: Client,
    org_id: str,
) -> dict[str, Any] | None:
    """Obtiene una organización por su ID.

    Args:
        client: Cliente Supabase autenticado.
        org_id: ID único de la organización.

    Returns:
        Diccionario con datos de la organización, o None si no existe.

    Raises:
        Exception: Si Supabase no está disponible.
    """
    raise NotImplementedError


async def create_org(
    client: Client,
    name: str,
    plan: str = "free",
) -> dict[str, Any]:
    """Crea una nueva organización.

    Args:
        client: Cliente Supabase autenticado.
        name: Nombre de la organización.
        plan: Plan de suscripción (free, pro, enterprise).

    Returns:
        Diccionario con datos de la organización creada.

    Raises:
        Exception: Si Supabase no está disponible o falla la inserción.
    """
    raise NotImplementedError


async def update_org(
    client: Client,
    org_id: str,
    updates: dict[str, Any],
) -> dict[str, Any]:
    """Actualiza datos de una organización.

    Args:
        client: Cliente Supabase autenticado.
        org_id: ID único de la organización.
        updates: Campos a actualizar.

    Returns:
        Diccionario con datos actualizados.

    Raises:
        Exception: Si la organización no existe o Supabase falla.
    """
    # SEGURIDAD: Siempre filtrar por org_id
    raise NotImplementedError

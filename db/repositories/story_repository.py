"""Repositorio de historias (stories).

Acceso a la tabla `stories` en Supabase con aislamiento por org_id.
"""

from typing import Any

from supabase import Client


async def get_story_by_id(
    client: Client,
    story_id: str,
    org_id: str,
) -> dict[str, Any] | None:
    """Obtiene una historia por ID, verificando pertenencia a la organización.

    Args:
        client: Cliente Supabase autenticado.
        story_id: ID único de la historia.
        org_id: ID de la organización — requerido para aislamiento de datos.

    Returns:
        Diccionario con datos de la historia, o None si no existe.

    Raises:
        Exception: Si Supabase no está disponible.
    """
    result = (
        client.table("stories")
        .select("id, title, content, story_type, status, credits_used, llm_provider, created_by, prompt_used, metadata, created_at")
        .eq("org_id", org_id)
        .eq("id", story_id)
        .single()
        .execute()
    )
    return result.data


async def update_story_status(
    client: Client,
    story_id: str,
    org_id: str,
    new_status: str,
) -> dict[str, Any]:
    """Actualiza el estado de una historia.

    Args:
        client: Cliente Supabase autenticado.
        story_id: ID único de la historia.
        org_id: ID de la organización — requerido para aislamiento de datos.
        new_status: Nuevo estado de la historia.

    Returns:
        Diccionario con los datos actualizados.

    Raises:
        Exception: Si la historia no existe o Supabase falla.
    """
    result = (
        client.table("stories")
        .update({"status": new_status})
        .eq("org_id", org_id)
        .eq("id", story_id)
        .execute()
    )
    return result.data[0] if result.data else {}

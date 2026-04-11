"""Repositorio de historias (stories).

Acceso a la tabla `stories` en Supabase con aislamiento por org_id.
"""

from typing import Any

from supabase import Client


async def create_story(
    client: Client,
    org_id: str,
    title: str,
    content: str,
    story_type: str,
) -> dict[str, Any]:
    """Crea una nueva historia en la base de datos.

    Args:
        client: Cliente Supabase autenticado.
        org_id: ID de la organización — requerido para aislamiento de datos.
        title: Título de la historia.
        content: Contenido narrativo generado.
        story_type: Tipo de historia (ej: 'blog', 'social', 'internal').

    Returns:
        Diccionario con los datos de la historia creada, incluyendo ID.

    Raises:
        Exception: Si Supabase no está disponible o falla la inserción.
    """
    result = client.table("stories").insert({
        "org_id": org_id,
        "title": title,
        "content": content,
        "story_type": story_type,
        "status": "borrador",
    }).execute()
    return result.data[0] if result.data else {}


async def get_stories_by_org(
    client: Client,
    org_id: str,
    limit: int = 20,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """Obtiene historias de una organización con paginación.

    Args:
        client: Cliente Supabase autenticado.
        org_id: ID de la organización — requerido para aislamiento de datos.
        limit: Número máximo de resultados.
        offset: Desplazamiento para paginación.

    Returns:
        Lista de diccionarios con datos de historias.

    Raises:
        Exception: Si Supabase no está disponible.
    """
    result = (
        client.table("stories")
        .select("id, title, content, story_type, status, credits_used, llm_provider, created_by, prompt_used, created_at")
        .eq("org_id", org_id)
        .order("created_at", desc=True)
        .range(offset, offset + limit - 1)
        .execute()
    )
    return result.data


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

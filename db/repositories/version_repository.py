"""Repositorio de versiones de historias.

Operaciones CRUD sobre la tabla story_versions usando el admin client
de Supabase. Cada versión es un snapshot inmutable del contenido de
una historia antes de ser editada.
"""

from typing import Any

import structlog

logger = structlog.get_logger()


async def create_version(
    client: Any,
    story_id: str,
    org_id: str,
    title: str,
    content: str,
    edited_by: str,
    edit_summary: str = "",
) -> dict[str, Any]:
    """Crea una nueva versión (snapshot) de una historia.

    Calcula automáticamente el version_number como MAX+1 de las
    versiones existentes para esa historia.

    Args:
        client: Cliente Supabase (admin).
        story_id: ID de la historia original.
        org_id: ID de la organización (para RLS).
        title: Título de la historia al momento del snapshot.
        content: Contenido completo al momento del snapshot.
        edited_by: UUID del usuario que hizo la edición.
        edit_summary: Descripción breve del cambio (opcional).

    Returns:
        Dict con los datos de la versión creada.
    """
    # Obtener el número de versión máximo actual
    existing = (
        client.table("story_versions")
        .select("version_number")
        .eq("story_id", story_id)
        .eq("org_id", org_id)
        .order("version_number", desc=True)
        .limit(1)
        .execute()
    )

    next_version = 1
    if existing.data:
        next_version = existing.data[0]["version_number"] + 1

    result = client.table("story_versions").insert({
        "story_id": story_id,
        "org_id": org_id,
        "version_number": next_version,
        "title": title,
        "content": content,
        "edited_by": edited_by,
        "edit_summary": edit_summary,
    }).execute()

    logger.info(
        "version_created",
        story_id=story_id,
        version_number=next_version,
        org_id=org_id,
    )

    return result.data[0]


async def list_versions(
    client: Any,
    story_id: str,
    org_id: str,
) -> list[dict[str, Any]]:
    """Lista todas las versiones de una historia, más recientes primero.

    Args:
        client: Cliente Supabase (admin).
        story_id: ID de la historia.
        org_id: ID de la organización (filtro de seguridad).

    Returns:
        Lista de versiones ordenada por version_number DESC.
    """
    result = (
        client.table("story_versions")
        .select("id, story_id, version_number, title, content, edited_by, edit_summary, created_at")
        .eq("story_id", story_id)
        .eq("org_id", org_id)
        .order("version_number", desc=True)
        .execute()
    )

    return result.data


async def get_version(
    client: Any,
    version_id: str,
    org_id: str,
) -> dict[str, Any] | None:
    """Obtiene una versión específica por su ID.

    Args:
        client: Cliente Supabase (admin).
        version_id: UUID de la versión.
        org_id: ID de la organización (filtro de seguridad).

    Returns:
        Dict con los datos de la versión, o None si no existe.
    """
    result = (
        client.table("story_versions")
        .select("id, story_id, version_number, title, content, edited_by, edit_summary, created_at")
        .eq("id", version_id)
        .eq("org_id", org_id)
        .execute()
    )

    if not result.data:
        return None

    return result.data[0]

"""Repositorio de historial de aprobaciones (approval_history).

Acceso a la tabla `approval_history` en Supabase con aislamiento por org_id.
Registra cada transición de estado como un evento inmutable.
"""

from typing import Any

from supabase import Client


async def record_transition(
    client: Client,
    story_id: str,
    org_id: str,
    from_status: str,
    to_status: str,
    changed_by: str,
    comment: str = "",
) -> dict[str, Any]:
    """Registra una transición de estado en el historial.

    Args:
        client: Cliente Supabase autenticado.
        story_id: ID de la historia que cambió de estado.
        org_id: ID de la organización — requerido para aislamiento de datos.
        from_status: Estado anterior.
        to_status: Estado nuevo.
        changed_by: ID del usuario que realizó el cambio.
        comment: Comentario opcional sobre la transición.

    Returns:
        Diccionario con datos del evento registrado.

    Raises:
        Exception: Si Supabase no está disponible.
    """
    result = client.table("approval_history").insert({
        "org_id": org_id,
        "story_id": story_id,
        "from_status": from_status,
        "to_status": to_status,
        "changed_by": changed_by,
        "comment": comment,
    }).execute()
    return result.data[0] if result.data else {}


async def get_history_for_story(
    client: Client,
    story_id: str,
    org_id: str,
) -> list[dict[str, Any]]:
    """Obtiene el historial completo de aprobaciones de una historia.

    Args:
        client: Cliente Supabase autenticado.
        story_id: ID de la historia.
        org_id: ID de la organización — requerido para aislamiento de datos.

    Returns:
        Lista de eventos de transición ordenados cronológicamente.

    Raises:
        Exception: Si Supabase no está disponible.
    """
    result = (
        client.table("approval_history")
        .select("*")
        .eq("org_id", org_id)
        .eq("story_id", story_id)
        .order("created_at", desc=False)
        .execute()
    )
    return result.data

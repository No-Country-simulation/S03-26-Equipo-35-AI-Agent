"""Repositorio de ejemplos dorados (golden_examples).

Acceso a la tabla `golden_examples` en Supabase con aislamiento por org_id.
Implementa lógica FIFO: máximo 3 ejemplos por combinación (org_id, story_type, tone).
Si se agrega un 4to, se elimina automáticamente el más antiguo.
"""

from typing import Any

import structlog
from supabase import Client

logger = structlog.get_logger()

MAX_EXAMPLES_PER_COMBO = 3


async def get_examples(
    client: Client,
    org_id: str,
    story_type: str,
    tone: str,
) -> list[dict[str, Any]]:
    """Recupera los ejemplos dorados para un story_type y tone específicos.

    Args:
        client: Cliente Supabase autenticado.
        org_id: ID de la organización.
        story_type: Tipo de contenido (blog, social, instagram, etc).
        tone: Tono narrativo (profesional, inspiracional, etc).

    Returns:
        Lista de hasta 3 ejemplos dorados ordenados por fecha de creación.
    """
    result = (
        client.table("golden_examples")
        .select("id, title, content, source, created_at")
        .eq("org_id", org_id)
        .eq("story_type", story_type)
        .eq("tone", tone)
        .order("created_at", desc=False)
        .limit(MAX_EXAMPLES_PER_COMBO)
        .execute()
    )
    return result.data


async def list_all_examples(
    client: Client,
    org_id: str,
) -> list[dict[str, Any]]:
    """Lista todos los ejemplos dorados de una organización.

    Args:
        client: Cliente Supabase autenticado.
        org_id: ID de la organización.

    Returns:
        Lista completa de ejemplos dorados para mostrar en Configuración.
    """
    result = (
        client.table("golden_examples")
        .select("id, story_type, tone, title, content, source, source_story_id, created_at")
        .eq("org_id", org_id)
        .order("created_at", desc=True)
        .execute()
    )
    return result.data


async def count_examples(
    client: Client,
    org_id: str,
    story_type: str,
    tone: str,
) -> int:
    """Cuenta cuántos ejemplos existen para una combinación específica.

    Args:
        client: Cliente Supabase autenticado.
        org_id: ID de la organización.
        story_type: Tipo de contenido.
        tone: Tono narrativo.

    Returns:
        Número de ejemplos existentes.
    """
    result = (
        client.table("golden_examples")
        .select("id", count="exact")
        .eq("org_id", org_id)
        .eq("story_type", story_type)
        .eq("tone", tone)
        .execute()
    )
    return result.count or 0


async def _evict_oldest(
    client: Client,
    org_id: str,
    story_type: str,
    tone: str,
) -> None:
    """Elimina el ejemplo más antiguo si se alcanzó el límite FIFO.

    Se invoca internamente antes de insertar un nuevo ejemplo.
    """
    current_count = await count_examples(client, org_id, story_type, tone)

    if current_count >= MAX_EXAMPLES_PER_COMBO:
        # Obtener el más antiguo
        oldest = (
            client.table("golden_examples")
            .select("id")
            .eq("org_id", org_id)
            .eq("story_type", story_type)
            .eq("tone", tone)
            .order("created_at", desc=False)
            .limit(1)
            .execute()
        )
        if oldest.data:
            oldest_id = oldest.data[0]["id"]
            client.table("golden_examples").delete().eq("id", oldest_id).execute()
            logger.info(
                "golden_example_evicted",
                evicted_id=oldest_id,
                story_type=story_type,
                tone=tone,
            )


async def add_example(
    client: Client,
    org_id: str,
    story_type: str,
    tone: str,
    title: str,
    content: str,
    source: str = "manual",
    source_story_id: str | None = None,
) -> dict[str, Any]:
    """Agrega un nuevo ejemplo dorado con lógica FIFO.

    Si ya existen 3 ejemplos para la combinación (org_id, story_type, tone),
    elimina automáticamente el más antiguo antes de insertar el nuevo.

    Args:
        client: Cliente Supabase autenticado.
        org_id: ID de la organización.
        story_type: Tipo de contenido.
        tone: Tono narrativo.
        title: Título descriptivo del ejemplo.
        content: Contenido completo del post ideal.
        source: Origen del ejemplo ('manual' | 'historia').
        source_story_id: ID de la historia origen (si source='historia').

    Returns:
        Diccionario con los datos del ejemplo creado.
    """
    # FIFO: si ya hay 3, borrar el más viejo
    await _evict_oldest(client, org_id, story_type, tone)

    payload: dict[str, Any] = {
        "org_id": org_id,
        "story_type": story_type,
        "tone": tone,
        "title": title,
        "content": content,
        "source": source,
    }
    if source_story_id:
        payload["source_story_id"] = source_story_id

    result = client.table("golden_examples").insert(payload).execute()

    current_count = await count_examples(client, org_id, story_type, tone)
    logger.info(
        "golden_example_added",
        story_type=story_type,
        tone=tone,
        count=f"{current_count}/{MAX_EXAMPLES_PER_COMBO}",
        source=source,
    )

    return result.data[0] if result.data else {}


async def delete_example(
    client: Client,
    example_id: str,
    org_id: str,
) -> bool:
    """Elimina un ejemplo dorado por ID.

    Args:
        client: Cliente Supabase autenticado.
        example_id: ID del ejemplo a eliminar.
        org_id: ID de la organización — requerido para aislamiento.

    Returns:
        True si se eliminó exitosamente.
    """
    result = (
        client.table("golden_examples")
        .delete()
        .eq("id", example_id)
        .eq("org_id", org_id)
        .execute()
    )
    deleted = bool(result.data)
    if deleted:
        logger.info("golden_example_deleted", example_id=example_id)
    return deleted

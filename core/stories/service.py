"""Servicio de historias — lógica de negocio de edición y versionado.

Orquesta la interacción entre el repositorio de historias y el
repositorio de versiones. Toda edición de contenido crea un snapshot
inmutable de la versión anterior antes de aplicar los cambios.
"""

from typing import Any

import structlog

from db.client import get_admin_client
from db.repositories.version_repository import create_version, get_version, list_versions

logger = structlog.get_logger()


async def update_story_with_version(
    story_id: str,
    org_id: str,
    user_id: str,
    new_content: str | None = None,
    new_title: str | None = None,
    edit_summary: str = "",
) -> dict[str, Any]:
    """Actualiza una historia guardando un snapshot de la versión anterior.

    Flujo transaccional:
    1. Leer el contenido actual de la historia
    2. Guardar snapshot como versión inmutable en story_versions
    3. Aplicar los cambios a la historia
    4. Retornar la historia actualizada + metadata de versión

    Args:
        story_id: UUID de la historia a editar.
        org_id: UUID de la organización (seguridad).
        user_id: UUID del usuario que edita.
        new_content: Nuevo contenido (None = sin cambio).
        new_title: Nuevo título (None = sin cambio).
        edit_summary: Descripción breve del cambio.

    Returns:
        Dict con la historia actualizada y la versión creada.

    Raises:
        ValueError: Si la historia no existe o no pertenece a la org.
    """
    client = get_admin_client()

    # 1. Leer la historia actual
    current = (
        client.table("stories")
        .select("id, title, content, org_id, status")
        .eq("id", story_id)
        .eq("org_id", org_id)
        .execute()
    )

    if not current.data:
        msg = f"Historia {story_id} no encontrada en la organización."
        raise ValueError(msg)

    story = current.data[0]

    # 2. Guardar snapshot de la versión actual ANTES de modificar
    version = await create_version(
        client=client,
        story_id=story_id,
        org_id=org_id,
        title=story["title"],
        content=story["content"],
        edited_by=user_id,
        edit_summary=edit_summary,
    )

    # 3. Construir los campos a actualizar
    update_data: dict[str, Any] = {}
    if new_content is not None:
        update_data["content"] = new_content
    if new_title is not None:
        update_data["title"] = new_title

    if not update_data:
        msg = "Debe proveer al menos new_content o new_title."
        raise ValueError(msg)

    # 4. Aplicar actualización
    updated = (
        client.table("stories")
        .update(update_data)
        .eq("id", story_id)
        .eq("org_id", org_id)
        .execute()
    )

    logger.info(
        "story_updated_with_version",
        story_id=story_id,
        version_number=version["version_number"],
        fields_updated=list(update_data.keys()),
        org_id=org_id,
    )

    return {
        "story": updated.data[0] if updated.data else story,
        "version_created": version,
    }


async def restore_story_version(
    story_id: str,
    version_id: str,
    org_id: str,
    user_id: str,
) -> dict[str, Any]:
    """Restaura una historia a una versión anterior.

    Flujo:
    1. Leer la versión solicitada
    2. Guardar snapshot del contenido actual (antes de restaurar)
    3. Aplicar el contenido de la versión antigua a la historia

    Args:
        story_id: UUID de la historia.
        version_id: UUID de la versión a restaurar.
        org_id: UUID de la organización.
        user_id: UUID del usuario que restaura.

    Returns:
        Dict con la historia restaurada.

    Raises:
        ValueError: Si la versión no existe o no pertenece a la org.
    """
    client = get_admin_client()

    # 1. Leer la versión solicitada
    version = await get_version(client, version_id, org_id)
    if not version:
        msg = f"Versión {version_id} no encontrada."
        raise ValueError(msg)

    if version["story_id"] != story_id:
        msg = "La versión no pertenece a esta historia."
        raise ValueError(msg)

    # 2. Guardar snapshot actual antes de restaurar
    current = (
        client.table("stories")
        .select("title, content")
        .eq("id", story_id)
        .eq("org_id", org_id)
        .execute()
    )

    if current.data:
        await create_version(
            client=client,
            story_id=story_id,
            org_id=org_id,
            title=current.data[0]["title"],
            content=current.data[0]["content"],
            edited_by=user_id,
            edit_summary=f"Snapshot antes de restaurar a v{version['version_number']}",
        )

    # 3. Aplicar la versión antigua
    updated = (
        client.table("stories")
        .update({
            "title": version["title"],
            "content": version["content"],
        })
        .eq("id", story_id)
        .eq("org_id", org_id)
        .execute()
    )

    logger.info(
        "story_version_restored",
        story_id=story_id,
        restored_version=version["version_number"],
        org_id=org_id,
    )

    return {
        "story": updated.data[0] if updated.data else {},
        "restored_from_version": version["version_number"],
    }


async def get_story_versions(
    story_id: str,
    org_id: str,
) -> list[dict[str, Any]]:
    """Lista todas las versiones de una historia.

    Args:
        story_id: UUID de la historia.
        org_id: UUID de la organización.

    Returns:
        Lista de versiones ordenada por número descendente.
    """
    client = get_admin_client()
    return await list_versions(client, story_id, org_id)

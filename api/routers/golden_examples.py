"""Router de ejemplos dorados (golden_examples).

Endpoints para gestionar los Post Ideales que se inyectan como
contexto Few-Shot al pipeline de generación LangGraph.

Límite: 3 ejemplos por combinación (story_type + tone) por organización.
"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from api.dependencies import get_current_org
from api.schemas import CurrentUser
from db.client import get_admin_client
from db.repositories import golden_example_repository as repo

router = APIRouter()


class GoldenExampleCreate(BaseModel):
    """Schema para crear un ejemplo dorado manualmente."""
    story_type: str = Field(default="blog", description="Tipo de contenido")
    tone: str = Field(default="profesional", description="Tono narrativo")
    title: str = Field(default="", description="Título descriptivo")
    content: str = Field(min_length=20, description="Contenido del post ideal")


class GoldenExampleFromStory(BaseModel):
    """Schema para marcar una historia existente como ejemplo dorado."""
    story_type: str = Field(default="blog")
    tone: str = Field(default="profesional")


@router.get("/")
async def list_golden_examples(
    current_user: Annotated[CurrentUser, Depends(get_current_org)],
) -> list[dict[str, Any]]:
    """Lista todos los ejemplos dorados de la organización."""
    client = get_admin_client()
    return await repo.list_all_examples(client, current_user.org_id)


@router.post("/", status_code=201)
async def create_golden_example(
    data: GoldenExampleCreate,
    current_user: Annotated[CurrentUser, Depends(get_current_org)],
) -> dict[str, Any]:
    """Crea un ejemplo dorado manual (desde Configuración).

    Si ya existen 3 para la combinación story_type+tone,
    el más antiguo se elimina automáticamente (FIFO).
    """
    client = get_admin_client()
    result = await repo.add_example(
        client=client,
        org_id=current_user.org_id,
        story_type=data.story_type,
        tone=data.tone,
        title=data.title,
        content=data.content,
        source="manual",
    )
    return result


@router.post("/from-story/{story_id}", status_code=201)
async def create_from_story(
    story_id: str,
    data: GoldenExampleFromStory,
    current_user: Annotated[CurrentUser, Depends(get_current_org)],
) -> dict[str, Any]:
    """Marca una historia existente como ejemplo dorado (desde Mis Historias).

    Obtiene el contenido de la historia y lo guarda como golden example.
    Si ya existen 3 para la combinación, el más antiguo se reemplaza (FIFO).
    """
    client = get_admin_client()

    # Obtener la historia
    story_result = (
        client.table("stories")
        .select("id, title, content, story_type")
        .eq("id", story_id)
        .eq("org_id", current_user.org_id)
        .execute()
    )

    if not story_result.data:
        raise HTTPException(status_code=404, detail="Historia no encontrada")

    story = story_result.data[0]

    result = await repo.add_example(
        client=client,
        org_id=current_user.org_id,
        story_type=data.story_type or story.get("story_type", "blog"),
        tone=data.tone,
        title=story.get("title", ""),
        content=story.get("content", ""),
        source="historia",
        source_story_id=story_id,
    )
    return result


@router.delete("/{example_id}")
async def delete_golden_example(
    example_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_org)],
) -> dict[str, str]:
    """Elimina un ejemplo dorado."""
    client = get_admin_client()
    deleted = await repo.delete_example(client, example_id, current_user.org_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Ejemplo no encontrado")

    return {"status": "deleted", "id": example_id}

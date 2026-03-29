"""Router de historias (stories).

Endpoints para crear, listar y obtener historias generadas.
Toda la lógica de negocio se delega a core/ — este router solo valida y enruta.

Flujo crítico de generación:
  1. Calcular costo → 2. Deducir créditos → 3. RAG → 4. LLM → 5. Store
  Si LLM falla → Reembolsar créditos
"""

from typing import Annotated, Any

import structlog
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel

from api.dependencies import get_current_org
from api.schemas import CurrentUser
from core.llm.router import LLMRoutingError, route
from core.multimedia.storage import upload_file
from core.rag.retriever import retrieve_context
from db.client import get_client

logger = structlog.get_logger()

router = APIRouter()


# ── Schemas ──


class GenerateRequest(BaseModel):
    """Schema de request para generación de historia."""

    task: str
    story_type: str = "blog"
    brand_tone: str = "profesional"
    has_image: bool = False


class GenerateResponse(BaseModel):
    """Schema de response para generación de historia."""

    story_id: str
    title: str
    content: str
    story_type: str
    provider: str
    model: str
    credits_used: int
    latency_ms: float


class StoryResponse(BaseModel):
    """Schema de response para una historia."""

    id: str
    title: str
    content: str
    story_type: str
    status: str
    credits_used: int
    llm_provider: str | None = None
    created_at: str


# ── Endpoints ──


@router.post("/generate", response_model=GenerateResponse)
async def generate_story(
    task: str = Form(...),
    story_type: str = Form("post"),
    brand_tone: str = Form("profesional"),
    files: list[UploadFile] | None = File(None),
    current_user: CurrentUser = Depends(get_current_org),
) -> GenerateResponse:
    """Genera una nueva historia usando el pipeline LLM + RAG.

    Flujo:
    1. Recuperar contexto RAG de la organización
    2. Generar contenido con LLM
    3. Guardar historia en DB
    """
    org_id = current_user.org_id

    # RAG + LLM
    try:
        # Recuperar contexto RAG
        rag_context = await retrieve_context(
            query=task,
            org_id=org_id,
            top_k=5,
        )

        # Procesar Archivos Multimedia (Upload -> Storage)
        uploaded_assets = []
        if files:
            for f in files:
                file_bytes = await f.read()
                metadata = await upload_file(
                    file_bytes=file_bytes,
                    filename=f.filename,
                    content_type=f.content_type,
                    org_id=org_id
                )
                uploaded_assets.append({
                    "url": metadata["public_url"],
                    "filename": metadata["filename"],
                    "content_type": metadata["content_type"],
                    "bytes": file_bytes,
                })

        # Generar con LLM Multimodal
        llm_response = await route(
            task=task,
            context=rag_context,
            org_id=org_id,
            brand_tone=brand_tone,
            assets=uploaded_assets,
        )

    except Exception as e:
        logger.error(
            "story_generation_failed",
            error=str(e)[:100],
            org_id=org_id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al generar contenido",
        ) from e

    # 5. Guardar historia en DB
    try:
        client = get_client()

        # Extraer título de la primera línea del contenido (si empieza con #)
        content = llm_response.content
        title = task[:100]
        if content.startswith("#"):
            first_line = content.split("\n")[0]
            title = first_line.lstrip("# ").strip() or title

        story_result = client.table("stories").insert({
            "org_id": org_id,
            "title": f"{story_type.title()} - {task[:20]}...",
            "content": content,
            "story_type": story_type,
            "status": "borrador",
            "created_by": current_user.user_id,
            "prompt_used": task,
            "llm_provider": llm_response.provider,
            "credits_used": 0,
            "multimedia_count": len(uploaded_assets) if files else 0,
            "metadata": {
                "model": llm_response.model,
                "tokens_used": llm_response.tokens_used,
                "latency_ms": llm_response.latency_ms,
                "brand_tone": brand_tone,
            },
        }).execute()

        new_story = story_result.data[0]
        story_id = str(new_story["id"])

    except Exception as e:
        logger.error("story_save_failed", error=str(e)[:100], org_id=org_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Contenido generado pero falló al guardar en DB",
        ) from e

    logger.info(
        "story_generated",
        story_id=story_id,
        provider=llm_response.provider,
        latency_ms=llm_response.latency_ms,
        org_id=org_id,
    )

    return GenerateResponse(
        story_id=story_id,
        title=title,
        content=content,
        story_type=story_type,
        provider=llm_response.provider,
        model=llm_response.model,
        credits_used=0,
        latency_ms=llm_response.latency_ms,
    )


@router.get("/", response_model=list[StoryResponse])
async def list_stories(
    current_user: Annotated[CurrentUser, Depends(get_current_org)],
    limit: int = 20,
    offset: int = 0,
) -> list[StoryResponse]:
    """Lista las historias de la organización con paginación."""
    client = get_client()

    result = (
        client.table("stories")
        .select("id, title, content, story_type, status, credits_used, llm_provider, created_at")
        .eq("org_id", current_user.org_id)
        .order("created_at", desc=True)
        .range(offset, offset + limit - 1)
        .execute()
    )

    return [
        StoryResponse(
            id=row["id"],
            title=row["title"],
            content=row["content"][:500],  # Preview
            story_type=row["story_type"],
            status=row["status"],
            credits_used=row["credits_used"],
            llm_provider=row.get("llm_provider"),
            created_at=row["created_at"],
        )
        for row in result.data
    ]


@router.get("/{story_id}", response_model=StoryResponse)
async def get_story(
    story_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_org)],
) -> StoryResponse:
    """Obtiene una historia por ID (filtrando por org_id)."""
    client = get_client()

    result = (
        client.table("stories")
        .select("id, title, content, story_type, status, credits_used, llm_provider, created_at")
        .eq("id", story_id)
        .eq("org_id", current_user.org_id)
        .single()
        .execute()
    )

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Historia no encontrada",
        )

    row = result.data
    return StoryResponse(
        id=row["id"],
        title=row["title"],
        content=row["content"],
        story_type=row["story_type"],
        status=row["status"],
        credits_used=row["credits_used"],
        llm_provider=row.get("llm_provider"),
        created_at=row["created_at"],
    )

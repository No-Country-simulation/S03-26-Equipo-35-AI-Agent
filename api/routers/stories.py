"""Router de historias (stories).

Endpoints para crear, listar y obtener historias generadas.
Toda la lógica de negocio se delega a core/ — este router solo valida y enruta.

Flujo crítico de generación:
  1. Calcular costo → 2. Deducir créditos → 3. RAG → 4. LLM → 5. Store
  Si LLM falla → Reembolsar créditos
"""

import time
from typing import Annotated, Any

import structlog
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel

from api.dependencies import get_current_org
from api.schemas import CurrentUser
from core.agents.graph import run_generation_graph
from core.llm.prompt_builder import resolve_temperature
from core.multimedia.storage import upload_file
from db.client import get_admin_client

logger = structlog.get_logger()

router = APIRouter()

# Máximo de redes sociales que se pueden generar en una sola solicitud
MAX_NETWORKS = 3

# Redes sociales válidas
VALID_NETWORKS = {"youtube", "instagram", "facebook", "twitter", "tiktok", "linkedin"}

# Tipos válidos en la DB (CHECK constraint)
_VALID_DB_TYPES = {"blog", "social", "internal", "press", "email"}

# Mapeo de story_type del frontend a los valores del CHECK constraint
_DB_TYPE_MAP: dict[str, str] = {
    "youtube": "social",
    "instagram": "social",
    "facebook": "social",
    "twitter": "social",
    "tiktok": "social",
    "linkedin": "social",
    "post": "social",
    "comunicado interno": "internal",
    "nota de prensa": "press",
    "email marketing": "email",
}


def _resolve_db_story_type(story_type: str) -> str:
    """Mapea el story_type del frontend al valor válido para el CHECK constraint de la DB.

    Args:
        story_type: Tipo de contenido recibido del frontend.

    Returns:
        Valor compatible con el CHECK constraint de la tabla stories.
    """
    if story_type in _VALID_DB_TYPES:
        return story_type
    return _DB_TYPE_MAP.get(story_type, "blog")


# ── Schemas ──


class GenerateRequest(BaseModel):
    """Schema de request para generación de historia."""

    task: str
    story_type: str = "blog"
    tone: str = "profesional"
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


class NetworkResult(BaseModel):
    """Resultado de generación para una red social individual."""

    network: str
    story_id: str
    title: str
    content: str
    provider: str
    model: str
    latency_ms: float


class MultiGenerateResponse(BaseModel):
    """Schema de response para generación multi-red."""

    results: list[NetworkResult]
    total_latency_ms: float
    credits_used: int


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



# ── YouTube Transcript ──


class YouTubeTranscriptRequest(BaseModel):
    """Schema para solicitud de transcripción de YouTube."""
    url: str


class YouTubeTranscriptResponse(BaseModel):
    """Schema para respuesta de transcripción de YouTube."""
    text: str
    language: str
    video_id: str


@router.post("/youtube-transcript", response_model=YouTubeTranscriptResponse)
async def extract_youtube_transcript(
    request: YouTubeTranscriptRequest,
) -> YouTubeTranscriptResponse:
    """Extrae la transcripción de un video de YouTube.

    No requiere autenticación — es un utility endpoint.
    """
    from core.multimedia.youtube import get_transcript

    try:
        result = await get_transcript(request.url)
        return YouTubeTranscriptResponse(
            text=result["text"],
            language=result["language"],
            video_id=result["video_id"],
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error("youtube_transcript_failed", error=str(e)[:100])
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al extraer la transcripción del video",
        ) from e


# ── Context Scraper (referencia externa) ──


class ScrapeContextRequest(BaseModel):
    """Schema para solicitud de scraping de contexto."""
    url: str


class ScrapeContextResponse(BaseModel):
    """Schema para respuesta de scraping de contexto."""
    title: str
    text: str
    url: str
    char_count: int


@router.post("/scrape-context", response_model=ScrapeContextResponse)
async def scrape_external_context(
    request: ScrapeContextRequest,
) -> ScrapeContextResponse:
    """Extrae texto de una URL externa como contexto de referencia.

    NO persiste en la base de datos ni genera embeddings.
    El texto se usa como contexto efímero para una generación.
    """
    from core.multimedia.context_scraper import scrape_for_context

    try:
        result = await scrape_for_context(request.url)
        return ScrapeContextResponse(
            title=result["title"],
            text=result["text"],
            url=result["url"],
            char_count=result["char_count"],
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error("context_scrape_failed", error=str(e)[:100])
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al extraer contenido de la URL",
        ) from e


@router.post("/generate", response_model=GenerateResponse)
async def generate_story(
    task: str = Form(...),
    story_type: str = Form("post"),
    tone: str = Form("profesional"),
    audience: str = Form("clientes"),
    length: str = Form("medio"),
    creativity: str = Form("balanceado"),
    analytics_data: str = Form(""),
    files: list[UploadFile] | None = File(None),
    current_user: CurrentUser = Depends(get_current_org),
) -> GenerateResponse:
    """Genera una nueva historia usando el pipeline multi-agente LangGraph.

    Flujo del grafo:
    1. [RAG] Recuperar chunks de Supabase
    2. [Analista] Destilar contexto de marca con Gemini Flash
    3. [Escritor] Generar borrador con Groq 70B
    4. [QA] Validar formato + tono + alucinaciones
    5. [Reintentar si QA rechaza, máximo 2x]
    6. [Finalizar] Guardar en DB
    """
    org_id = current_user.org_id
    temperature = resolve_temperature(creativity)

    # TODO(fase-3): Reactivar sistema de créditos
    # Flujo pendiente: calcular_costo() → verificar_y_deducir() → grafo → reembolsar si falla

    # Procesar archivos multimedia (Upload → Storage) antes del grafo
    uploaded_assets: list[dict[str, Any]] = []
    if files:
        try:
            for f in files:
                file_bytes = await f.read()
                metadata = await upload_file(
                    file_bytes=file_bytes,
                    filename=f.filename,
                    content_type=f.content_type,
                    org_id=org_id,
                )
                uploaded_assets.append({
                    "url": metadata["public_url"],
                    "filename": metadata["filename"],
                    "content_type": metadata["content_type"],
                    "bytes": file_bytes,
                })
        except Exception as e:
            logger.warning("file_upload_failed", error=str(e)[:100], org_id=org_id)

    # Ejecutar el grafo multi-agente
    result = await run_generation_graph({
        "task": task,
        "org_id": org_id,
        "story_type": story_type,
        "tone": tone,
        "audience": audience,
        "length": length,
        "temperature": temperature,
        "analytics_data": analytics_data,
        "assets": uploaded_assets,
    })

    if result["status"] == "error":
        logger.error("story_generation_failed", error=result.get("error"), org_id=org_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al generar contenido",
        )

    # Guardar historia en DB
    try:
        client = get_admin_client()

        db_story_type = _resolve_db_story_type(story_type)

        content = result["final_content"]
        title = task[:100]
        if content.startswith("#"):
            first_line = content.split("\n")[0]
            title = first_line.lstrip("# ").strip() or title

        story_result = client.table("stories").insert({
            "org_id": org_id,
            "title": f"{story_type.title()} - {task[:20]}...",
            "content": content,
            "story_type": db_story_type,
            "status": "borrador",
            "created_by": current_user.user_id,
            "prompt_used": task,
            "llm_provider": result.get("provider", ""),
            "credits_used": 0,
            "multimedia_count": len(uploaded_assets),
            "metadata": {
                "network": story_type,
                "model": result.get("model", ""),
                "tokens_used": result.get("tokens_used", 0),
                "latency_ms": result.get("latency_ms", 0),
                "tone": tone,
                "audience": audience,
                "length": length,
                "creativity": creativity,
                "has_analytics": bool(analytics_data.strip()),
                "qa_approved": result.get("qa_approved", False),
                "retry_count": result.get("retry_count", 0),
                "graph_status": result.get("status", "ok"),
            },
        }).execute()

        story_id = str(story_result.data[0]["id"])

    except Exception as e:
        logger.error("story_save_failed", error=str(e)[:100], org_id=org_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Contenido generado pero falló al guardar en DB",
        ) from e

    logger.info(
        "story_generated",
        story_id=story_id,
        provider=result.get("provider"),
        qa_approved=result.get("qa_approved"),
        retry_count=result.get("retry_count", 0),
        org_id=org_id,
    )

    return GenerateResponse(
        story_id=story_id,
        title=title,
        content=content,
        story_type=story_type,
        provider=result.get("provider", ""),
        model=result.get("model", ""),
        credits_used=0,
        latency_ms=result.get("latency_ms", 0),
    )


@router.post("/generate-multi", response_model=MultiGenerateResponse)
async def generate_multi_network(
    task: str = Form(...),
    networks: str = Form(...),
    tone: str = Form("profesional"),
    audience: str = Form("clientes"),
    length: str = Form("medio"),
    creativity: str = Form("balanceado"),
    analytics_data: str = Form(""),
    files: list[UploadFile] | None = File(None),
    current_user: CurrentUser = Depends(get_current_org),
) -> MultiGenerateResponse:
    """Genera contenido para múltiples redes sociales secuencialmente.

    Recibe las redes como string separado por comas (máximo 3).
    Ejecuta la generación secuencialmente para evitar rate limits.
    """
    org_id = current_user.org_id
    temperature = resolve_temperature(creativity)

    # Parsear y validar redes
    network_list = [n.strip().lower() for n in networks.split(",") if n.strip()]
    network_list = [n for n in network_list if n in VALID_NETWORKS]

    if not network_list:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Debe seleccionar al menos una red válida: {', '.join(VALID_NETWORKS)}",
        )

    if len(network_list) > MAX_NETWORKS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Máximo {MAX_NETWORKS} redes por solicitud",
        )

    # Procesar archivos multimedia (una sola vez para todas las redes)
    uploaded_assets: list[dict[str, Any]] = []
    if files:
        try:
            for f in files:
                file_bytes = await f.read()
                metadata = await upload_file(
                    file_bytes=file_bytes,
                    filename=f.filename,
                    content_type=f.content_type,
                    org_id=org_id,
                )
                uploaded_assets.append({
                    "url": metadata["public_url"],
                    "filename": metadata["filename"],
                    "content_type": metadata["content_type"],
                    "bytes": file_bytes,
                })
        except Exception as e:
            logger.warning("multi_file_upload_failed", error=str(e)[:100], org_id=org_id)

    # Generar secuencialmente por cada red usando el grafo multi-agente
    results: list[NetworkResult] = []
    total_start = time.perf_counter()

    for network in network_list:
        try:
            result = await run_generation_graph({
                "task": task,
                "org_id": org_id,
                "story_type": network,
                "tone": tone,
                "audience": audience,
                "length": length,
                "temperature": temperature,
                "analytics_data": analytics_data,
                "assets": uploaded_assets,
            })

            # Continuar solo si el grafo no tuvo error crítico
            if result.get("status") == "error":
                raise ValueError(result.get("error", "Graph error"))

            db_story_type = _resolve_db_story_type(network)

            # Guardar en DB
            client = get_admin_client()
            content = result["final_content"]
            title = task[:100]
            if content.startswith("#"):
                first_line = content.split("\n")[0]
                title = first_line.lstrip("# ").strip() or title

            story_result = client.table("stories").insert({
                "org_id": org_id,
                "title": f"{network.title()} - {task[:20]}...",
                "content": content,
                "story_type": db_story_type,
                "status": "borrador",
                "created_by": current_user.user_id,
                "prompt_used": task,
                "llm_provider": result.get("provider", ""),
                "credits_used": 0,
                "multimedia_count": len(uploaded_assets),
                "metadata": {
                    "network": network,
                    "model": result.get("model", ""),
                    "tokens_used": result.get("tokens_used", 0),
                    "latency_ms": result.get("latency_ms", 0),
                    "tone": tone,
                    "audience": audience,
                    "length": length,
                    "creativity": creativity,
                    "generated_as_multi": True,
                    "qa_approved": result.get("qa_approved", False),
                    "retry_count": result.get("retry_count", 0),
                },
            }).execute()

            story_id = str(story_result.data[0]["id"])

            results.append(NetworkResult(
                network=network,
                story_id=story_id,
                title=title,
                content=content,
                provider=result.get("provider", ""),
                model=result.get("model", ""),
                latency_ms=result.get("latency_ms", 0),
            ))

            logger.info(
                "multi_network_generated",
                network=network,
                provider=result.get("provider"),
                qa_approved=result.get("qa_approved"),
                org_id=org_id,
            )

        except Exception as e:
            logger.error(
                "multi_network_failed",
                network=network,
                error=str(e)[:100],
                org_id=org_id,
            )
            # Continuar con las demás redes — no fallar todo por una
            results.append(NetworkResult(
                network=network,
                story_id="",
                title=f"Error generando para {network}",
                content=f"No se pudo generar contenido para {network}: {str(e)[:200]}",
                provider="error",
                model="",
                latency_ms=0,
            ))

    total_latency = (time.perf_counter() - total_start) * 1000

    return MultiGenerateResponse(
        results=results,
        total_latency_ms=round(total_latency, 2),
        credits_used=0,
    )


@router.get("/", response_model=list[StoryResponse])
async def list_stories(
    current_user: Annotated[CurrentUser, Depends(get_current_org)],
    limit: int = 20,
    offset: int = 0,
) -> list[StoryResponse]:
    """Lista las historias de la organización con paginación."""
    client = get_admin_client()

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
    client = get_admin_client()

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

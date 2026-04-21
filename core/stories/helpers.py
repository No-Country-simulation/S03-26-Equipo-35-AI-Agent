"""Helpers para generación y persistencia de historias.

Funciones utilitarias compartidas entre el router sync (stories.py),
el worker async (generation_worker.py) y el multi-network endpoint.

Centraliza lógica que antes estaba triplicada:
- Extracción de título desde contenido Markdown
- Procesamiento de archivos multimedia (Upload → Storage)
- Persistencia de historias generadas en Supabase
"""

from typing import Any

import structlog
from fastapi import UploadFile
from supabase import Client

from core.multimedia.storage import upload_file

logger = structlog.get_logger()


def extract_title_from_content(task: str, content: str) -> str:
    """Extrae el título del contenido generado, con fallback al task.

    Si el contenido comienza con un heading Markdown (#), extrae
    la primera línea como título. Caso contrario, usa los primeros
    100 caracteres del task.

    Args:
        task: Prompt original del usuario.
        content: Contenido generado por el LLM.

    Returns:
        Título limpio de máximo 100 caracteres.
    """
    title = task[:100]
    if content.startswith("#"):
        first_line = content.split("\n")[0]
        title = first_line.lstrip("# ").strip() or title
    return title[:100]


async def process_upload_files(
    files: list[UploadFile] | None,
    org_id: str,
) -> list[dict[str, Any]]:
    """Procesa y sube archivos multimedia al storage.

    Lee cada archivo, lo sube a Supabase Storage, y retorna
    la lista de assets con URLs públicas y metadatos.

    Args:
        files: Lista opcional de archivos subidos por el usuario.
        org_id: UUID de la organización.

    Returns:
        Lista de diccionarios con url, filename, content_type y bytes.
    """
    if not files:
        return []

    uploaded_assets: list[dict[str, Any]] = []
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

    return uploaded_assets


def save_generated_story(
    client: Client,
    org_id: str,
    user_id: str,
    task: str,
    content: str,
    story_type: str,
    db_story_type: str,
    result: dict[str, Any],
    uploaded_assets: list[dict[str, Any]],
    extra_metadata: dict[str, Any] | None = None,
) -> str:
    """Persiste una historia generada en la tabla stories de Supabase.

    Centraliza la lógica de inserción que antes estaba triplicada
    entre generate_story, generate_multi_network y generation_worker.

    Args:
        client: Cliente Supabase admin.
        org_id: UUID de la organización.
        user_id: UUID del usuario creador.
        task: Prompt original del usuario.
        content: Contenido generado por el LLM.
        story_type: Tipo de contenido original (ej: 'instagram', 'blog').
        db_story_type: Tipo resuelto para el CHECK constraint de la DB.
        result: Diccionario de resultado del grafo LangGraph.
        uploaded_assets: Lista de assets multimedia procesados.
        extra_metadata: Campos adicionales para el JSON metadata.

    Returns:
        UUID de la historia creada.
    """
    title = extract_title_from_content(task, content)

    metadata = {
        "network": story_type,
        "model": result.get("model", ""),
        "tokens_used": result.get("tokens_used", 0),
        "latency_ms": result.get("latency_ms", 0),
        "qa_approved": result.get("qa_approved", False),
        "retry_count": result.get("retry_count", 0),
        "graph_status": result.get("status", "ok"),
    }

    if extra_metadata:
        metadata.update(extra_metadata)

    story_result = client.table("stories").insert({
        "org_id": org_id,
        "title": title,
        "content": content,
        "story_type": db_story_type,
        "status": "borrador",
        "created_by": user_id,
        "prompt_used": task,
        "llm_provider": result.get("provider", ""),
        "credits_used": 0,
        "multimedia_count": len(uploaded_assets),
        "metadata": metadata,
    }).execute()

    return str(story_result.data[0]["id"])

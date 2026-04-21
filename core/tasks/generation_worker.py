"""Worker de generación de historias en background.

Ejecuta el grafo LangGraph de generación en un asyncio.Task separado,
actualizando el progreso en Redis para que el frontend haga polling
con mensajes reales (no rotativos hardcodeados).

Flujo:
1. El endpoint POST /stories/generate crea un job_id y lanza este worker
2. El worker actualiza el estado en Redis en cada nodo del grafo
3. El frontend consulta GET /stories/jobs/{job_id} cada 3 segundos
4. Al terminar, el worker guarda la historia en DB y marca el job como completed
"""

import time
from typing import Any

import structlog

from api.routers.stories import _resolve_db_story_type
from core.cache.redis_client import job_set_status

logger = structlog.get_logger()

# Mensajes de progreso por etapa del grafo
PROGRESS_MESSAGES = {
    "starting": "Iniciando pipeline de generación...",
    "uploading": "Procesando archivos multimedia...",
    "rag": "Recuperando contexto de marca...",
    "analyzing": "Analizando contexto con Gemini...",
    "writing": "Escribiendo narración con IA...",
    "qa": "Verificando calidad del contenido...",
    "retry": "Reescribiendo para mejorar calidad...",
    "saving": "Guardando historia en la base de datos...",
    "completed": "¡Historia generada exitosamente!",
    "failed": "Error durante la generación.",
}


async def run_generation_job(
    job_id: str,
    task: str,
    org_id: str,
    user_id: str,
    story_type: str,
    tone: str,
    audience: str,
    length: str,
    temperature: float,
    analytics_data: str,
    uploaded_assets: list[dict[str, Any]],
) -> None:
    """Ejecuta el pipeline completo de generación en background.

    Actualiza el progreso en Redis en cada paso para que el frontend
    pueda mostrar el estado real al usuario.

    Args:
        job_id: ID único del job (UUID).
        task: Prompt del usuario.
        org_id: ID de la organización.
        user_id: ID del usuario que solicitó.
        story_type: Tipo de contenido.
        tone: Tono narrativo.
        audience: Audiencia objetivo.
        length: Longitud deseada.
        temperature: Creatividad del LLM.
        analytics_data: Datos de analytics opcionales.
        uploaded_assets: Lista de archivos procesados.
    """
    start_time = time.perf_counter()

    try:
        # ── Paso 1: RAG + LLM (el grafo completo) ──
        await job_set_status(job_id, "processing", PROGRESS_MESSAGES["rag"])

        from core.agents.graph import run_generation_graph

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
            await job_set_status(
                job_id,
                "failed",
                PROGRESS_MESSAGES["failed"],
                result={"error": result.get("error", "Error desconocido")},
            )
            return

        # ── Paso 2: Guardar historia en DB ──
        await job_set_status(job_id, "processing", PROGRESS_MESSAGES["saving"])

        from core.stories.helpers import extract_title_from_content, save_generated_story
        from db.client import get_admin_client

        client = get_admin_client()

        # Resolver tipo de historia para DB (misma lógica que el router sync)
        db_story_type = _resolve_db_story_type(story_type)

        content = result["final_content"]
        latency_ms = (time.perf_counter() - start_time) * 1000

        # Inyectar latency calculada en el resultado para el helper
        result["latency_ms"] = round(latency_ms, 2)

        story_id = save_generated_story(
            client=client,
            org_id=org_id,
            user_id=user_id,
            task=task,
            content=content,
            story_type=story_type,
            db_story_type=db_story_type,
            result=result,
            uploaded_assets=uploaded_assets,
            extra_metadata={
                "tone": tone,
                "audience": audience,
                "length": length,
                "async_job": True,
            },
        )

        title = extract_title_from_content(task, content)

        # ── Paso 3: Marcar como completado ──
        await job_set_status(
            job_id,
            "completed",
            PROGRESS_MESSAGES["completed"],
            result={
                "story_id": story_id,
                "title": title,
                "content": content,
                "provider": result.get("provider", ""),
                "latency_ms": round(latency_ms, 2),
            },
        )

        logger.info(
            "background_generation_completed",
            job_id=job_id,
            story_id=story_id,
            latency_ms=round(latency_ms, 2),
            org_id=org_id,
        )

    except Exception as e:
        logger.error(
            "background_generation_failed",
            job_id=job_id,
            error=str(e)[:200],
            org_id=org_id,
        )
        await job_set_status(
            job_id,
            "failed",
            PROGRESS_MESSAGES["failed"],
            result={"error": str(e)[:200]},
        )

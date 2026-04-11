"""Router LLM para AutoStory Builder (Legacy — pre-LangGraph).

NOTA: Este módulo fue el router principal antes de la implementación
del grafo multi-agente en core/agents/graph.py. La función route()
ya no se usa en el flujo de producción — el pipeline principal
ahora es run_generation_graph() en core/agents/graph.py.

Se mantiene como fallback y referencia. Los tests unitarios
en tests/unit/test_llm_router.py validan este módulo.

Orquesta las llamadas a los proveedores LLM con fallback automático:
  1. Groq Llama 3.3 70B — composición narrativa principal
  2. OpenRouter — fallback si Groq devuelve 429 o timeout
"""

import structlog

from core.llm import LLMResponse
from core.llm.prompt_builder import build_story_prompt
from core.rag import RAGContext

logger = structlog.get_logger()


class LLMRoutingError(Exception):
    """Todos los proveedores LLM fallaron."""


async def route(
    task: str,
    context: RAGContext,
    org_id: str,
    tone: str = "profesional",
    assets: list[dict] | None = None,
    temperature: float = 0.6,
    audience: str = "clientes",
    length: str = "medio",
    story_type: str = "blog",
    analytics_data: str = "",
) -> LLMResponse:
    """Enruta una tarea al proveedor LLM adecuado con fallback.

    Flujo:
    1. Pre-procesar assets visuales con Gemini Flash
    2. Construir prompt con build_story_prompt()
    3. Intentar Groq (provider principal para composición)
    4. Si Groq falla (429/timeout) → fallback a OpenRouter
    5. Si todos fallan → LLMRoutingError

    Args:
        task: Descripción de la tarea a realizar.
        context: Contexto RAG con chunks relevantes de la organización.
        org_id: ID de la organización — para logging y trazabilidad.
        tone: Tono unificado de escritura. Default: 'profesional'.
        assets: Lista de assets multimedia a pre-procesar. Default: None.
        temperature: Temperatura para el LLM. Default: 0.6.
        audience: Audiencia destino del contenido. Default: 'clientes'.
        length: Longitud deseada del contenido. Default: 'medio'.
        story_type: Tipo de contenido o red social. Default: 'blog'.
        analytics_data: Datos numéricos/KPIs del usuario. Default: ''.

    Returns:
        LLMResponse con el contenido generado y metadata del provider.

    Raises:
        LLMRoutingError: Si todos los proveedores fallan.
        ValueError: Si la tarea está vacía.
    """
    # 1. Pre-procesar assets visuales con Gemini Flash
    visual_context = ""
    if assets:
        from core.llm.providers import gemini_provider
        for asset in assets:
            logger.info("routing_asset_to_gemini", filename=asset["filename"], org_id=org_id)
            try:
                analysis = await gemini_provider.analyze_asset(
                    file_bytes=asset["bytes"],
                    content_type=asset["content_type"]
                )
                visual_context += f"--- ANÁLISIS DEL ARCHIVO: {asset['filename']} ---\n{analysis}\n\n"
            except Exception as e:
                logger.warning("gemini_asset_analysis_failed", filename=asset["filename"], error=str(e)[:100])

    # 2. Construir prompt con personalización dinámica
    system_prompt, user_prompt = build_story_prompt(
        context=context,
        task=task,
        tone=tone,
        visual_context=visual_context,
        audience=audience,
        length=length,
        story_type=story_type,
        analytics_data=analytics_data,
    )

    # 3. Intentar Groq (provider principal)
    groq_err: str = ""
    try:
        from core.llm.providers import groq_provider

        response = await groq_provider.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=temperature,
        )

        logger.info(
            "llm_route_success",
            provider="groq",
            latency_ms=response.latency_ms,
            org_id=org_id,
        )
        return response

    except Exception as e:
        groq_err = str(e)[:100]
        logger.warning(
            "llm_route_groq_failed",
            error=groq_err,
            org_id=org_id,
        )

    # 4. Fallback a OpenRouter
    try:
        from core.llm.providers import openrouter_provider

        response = await openrouter_provider.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=temperature,
        )

        logger.info(
            "llm_route_fallback_success",
            provider="openrouter",
            latency_ms=response.latency_ms,
            org_id=org_id,
        )
        return response

    except Exception as openrouter_error:
        logger.error(
            "llm_route_all_failed",
            groq_error=groq_err,
            openrouter_error=str(openrouter_error)[:100],
            org_id=org_id,
        )
        msg = "Todos los proveedores LLM fallaron"
        raise LLMRoutingError(msg) from openrouter_error

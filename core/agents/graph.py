"""Grafo LangGraph de generación de contenido multi-agente.

Ensambla los nodos en un StateGraph de LangGraph con el siguiente flujo:

  [retrieve_rag] → [analyze_context] → [write_content] → [qa_editor]
                                                              ↓         ↓
                                                         approved   rejected + retry < MAX
                                                              ↓         ↓
                                                        [finalize]  [write_content] (reintento)
                                                                         ↓
                                                               rejected + retry >= MAX
                                                                         ↓
                                                                   [finalize]

Función pública: run_generation_graph(input_data) → ContentGenerationState
"""

import os
from typing import Any

import structlog
from langgraph.graph import END, START, StateGraph

from core.agents.nodes import (
    node_analyze_context,
    node_finalize,
    node_qa_editor,
    node_retrieve_rag,
    node_write_content,
)
from core.agents.state import ContentGenerationState

logger = structlog.get_logger()


def _should_retry_or_finalize(state: ContentGenerationState) -> str:
    """Función de decisión del grafo: ¿reintentar escritura o finalizar?

    Se ejecuta después del nodo QA para decidir el siguiente paso.
    LangGraph llama a esta función y usa su valor de retorno para
    navegar al nodo correspondiente.

    Returns:
        "write_content" — si el QA rechazó Y hay reintentos disponibles.
        "finalize"      — si el QA aprobó O se agotaron los reintentos.
    """
    qa_approved = state.get("qa_approved", False)
    status = state.get("status", "ok")
    error = state.get("error")

    # Si hay error crítico previo, finalizar sin reintento
    if error and "Writer failed" in error:
        return "finalize"

    # Si QA aprobó o se agotaron reintentos → finalizar
    if qa_approved or status == "qa_failed_max_retries":
        return "finalize"

    # Si QA rechazó y aún hay reintentos disponibles → volver al escritor
    return "write_content"


def build_generation_graph() -> StateGraph:
    """Construye y compila el grafo de generación de contenido.

    Returns:
        Grafo compilado listo para invocar con .invoke() o .ainvoke().
    """
    graph = StateGraph(ContentGenerationState)

    # ── Agregar nodos ──
    graph.add_node("retrieve_rag", node_retrieve_rag)
    graph.add_node("analyze_context", node_analyze_context)
    graph.add_node("write_content", node_write_content)
    graph.add_node("qa_editor", node_qa_editor)
    graph.add_node("finalize", node_finalize)

    # ── Definir flujo principal (aristas simples) ──
    graph.add_edge(START, "retrieve_rag")
    graph.add_edge("retrieve_rag", "analyze_context")
    graph.add_edge("analyze_context", "write_content")
    graph.add_edge("write_content", "qa_editor")

    # ── Arista condicional: QA decide si reintentar o finalizar ──
    graph.add_conditional_edges(
        "qa_editor",
        _should_retry_or_finalize,
        {
            "write_content": "write_content",  # Reintento con feedback
            "finalize": "finalize",             # Aprobado o reintentos agotados
        },
    )

    graph.add_edge("finalize", END)

    return graph.compile()


# Instancia compilada del grafo — singleton reutilizado entre requests
_compiled_graph = build_generation_graph()


async def run_generation_graph(input_data: dict[str, Any]) -> ContentGenerationState:
    """Punto de entrada principal para el pipeline de generación multi-agente.

    Inicializa el estado con valores por defecto seguros, ejecuta el grafo
    y retorna el estado final con el contenido generado.

    Args:
        input_data: Diccionario con los datos del request. Los campos no
                    provistos reciben valores por defecto.

    Returns:
        ContentGenerationState con el resultado final del grafo.
        Siempre retorna — los errores están en state["error"] y state["status"].
    """
    # Estado inicial con defaults seguros
    initial_state: ContentGenerationState = {
        # Input del usuario
        "task": input_data.get("task", ""),
        "org_id": input_data.get("org_id", ""),
        "story_type": input_data.get("story_type", "blog"),
        "tone": input_data.get("tone", "profesional"),
        "audience": input_data.get("audience", "clientes"),
        "length": input_data.get("length", "medio"),
        "temperature": input_data.get("temperature", 0.6),
        "analytics_data": input_data.get("analytics_data", ""),
        "assets": input_data.get("assets", []),

        # Estado interno — inicializado vacío
        "rag_chunks": [],
        "brand_insights": "",
        "visual_context": "",
        "draft_content": "",
        "qa_feedback": "",
        "qa_approved": False,
        "retry_count": 0,

        # Output final — inicializado vacío
        "final_content": "",
        "provider": "",
        "model": "",
        "latency_ms": 0.0,
        "tokens_used": 0,

        # Control de errores
        "error": None,
        "status": "ok",
    }

    logger.info(
        "generation_graph_start",
        task_length=len(initial_state["task"]),
        story_type=initial_state["story_type"],
        org_id=initial_state["org_id"],
    )

    try:
        # Configurar LangSmith si está disponible
        config: dict[str, Any] = {}
        langsmith_key = os.getenv("LANGSMITH_API_KEY")
        if langsmith_key:
            config["metadata"] = {
                "org_id": initial_state["org_id"],
                "story_type": initial_state["story_type"],
            }

        final_state: ContentGenerationState = await _compiled_graph.ainvoke(
            initial_state,
            config=config if config else None,
        )

        logger.info(
            "generation_graph_done",
            status=final_state.get("status"),
            qa_approved=final_state.get("qa_approved"),
            retry_count=final_state.get("retry_count", 0),
            provider=final_state.get("provider"),
            org_id=final_state["org_id"],
        )

        return final_state

    except Exception as e:
        logger.error("generation_graph_crashed", error=str(e)[:200], org_id=initial_state["org_id"])
        # Retornar estado con error — nunca propagar excepción al endpoint
        initial_state["error"] = str(e)
        initial_state["status"] = "error"
        return initial_state

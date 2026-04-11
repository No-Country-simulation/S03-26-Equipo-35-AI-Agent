"""Estado tipado del grafo de generación de contenido.

Define el TypedDict que fluye entre todos los nodos del grafo LangGraph.
Cada nodo recibe el estado completo y retorna un dict parcial con
los campos que modifica.
"""

from typing import Any, TypedDict


class ContentGenerationState(TypedDict):
    """Estado completo del pipeline de generación multi-agente.

    Fluye entre todos los nodos del grafo. Cada nodo modifica
    solo los campos de su responsabilidad.
    """

    # ── Input del usuario (inmutables en el grafo) ──
    task: str
    org_id: str
    story_type: str
    tone: str
    audience: str
    length: str
    temperature: float
    analytics_data: str
    assets: list[dict[str, Any]]

    # ── Estado interno — producido por cada nodo ──
    rag_chunks: list[dict[str, Any]]   # Chunks RAG crudos del retriever
    brand_insights: str                # Brief destilado por el Analista
    visual_context: str                # Análisis de assets por Gemini Flash
    draft_content: str                 # Borrador del Agente Escritor
    qa_feedback: str                   # Correcciones del Editor QA (vacío si aprobó)
    qa_approved: bool                  # True cuando el QA da el visto bueno
    retry_count: int                   # Número de reintentos del ciclo Escritor→QA

    # ── Output final ──
    final_content: str
    provider: str
    model: str
    latency_ms: float
    tokens_used: int

    # ── Control de errores (patrón LangGraph — errores al estado, nunca excepciones) ──
    error: str | None
    status: str   # "ok" | "qa_failed_max_retries" | "error"

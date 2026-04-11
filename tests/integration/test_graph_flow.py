"""Tests de integración para el flujo completo del grafo LangGraph.

Mockea todos los LLMs (Gemini, Groq, OpenRouter) y Supabase.
Verifica el flujo happy path, el ciclo de reintento de QA
y el comportamiento cuando se agotan los reintentos.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.agents.graph import run_generation_graph
from core.llm import LLMResponse

# ── Fixtures ──

MOCK_RAG_CHUNKS = [
    {"text": "AutoStory es una empresa de tecnología educativa.", "index": 0, "metadata": {}},
    {"text": "Nuestro tono es cercano y profesional.", "index": 1, "metadata": {}},
]

MOCK_BRAND_INSIGHTS = """## Brief de Marca

**Identidad:** AutoStory es una plataforma EdTech enfocada en narrativas de impacto.

**Vocabulario propio:** narrativa, impacto, transformación

**Tono:** Cercano y profesional
"""

MOCK_DRAFT_BLOG = """# El poder de las narrativas en la educación

La educación ha cambiado. Las historias son el nuevo lenguaje del aprendizaje.

## Por qué las narrativas funcionan

Los datos demuestran que el storytelling aumenta la retención en un 70%.

## El futuro es narrativo

AutoStory está construyendo ese futuro.
"""

MOCK_TWITTER_DRAFT_VALID = """1/ Las narrativas cambian cómo aprendemos.

2/ El storytelling aumenta la retención en un 70%.

3/ AutoStory construye ese puente entre datos y emoción.

4/ En 2025, el contenido sin historia no conecta.

5/ Seguinos para más insights sobre narrativas y educación."""

MOCK_GROQ_RESPONSE = LLMResponse(
    content=MOCK_DRAFT_BLOG,
    provider="groq",
    model="llama-3.3-70b-versatile",
    tokens_used=500,
    latency_ms=1200.0,
)

MOCK_GEMINI_RESPONSE = LLMResponse(
    content=MOCK_BRAND_INSIGHTS,
    provider="gemini",
    model="gemini-2.0-flash",
    tokens_used=300,
    latency_ms=800.0,
)

BASE_INPUT = {
    "task": "Escribe un blog post sobre el impacto de las narrativas en la educación",
    "org_id": "test-org-123",
    "story_type": "blog",
    "tone": "profesional",
    "audience": "clientes",
    "length": "medio",
    "temperature": 0.6,
    "analytics_data": "",
    "assets": [],
}


# ── Tests del flujo happy path ──

@pytest.mark.asyncio
async def test_graph_happy_path_blog():
    """Flujo completo: RAG → Analista → Escritor → QA aprueba → Finaliza."""
    mock_rag_result = MagicMock()
    mock_rag_result.chunks = [
        MagicMock(text=c["text"], index=c["index"], metadata=c["metadata"])
        for c in MOCK_RAG_CHUNKS
    ]

    qa_approval_response = LLMResponse(
        content="APROBADO",
        provider="groq",
        model="llama-3.3-70b-versatile",
        tokens_used=50,
        latency_ms=500.0,
    )

    with patch("core.agents.nodes.retrieve_context", new_callable=AsyncMock) as mock_rag, \
         patch("core.llm.providers.gemini_provider.generate", new_callable=AsyncMock) as mock_gemini, \
         patch("core.llm.providers.groq_provider.generate", new_callable=AsyncMock) as mock_groq:

        mock_rag.return_value = mock_rag_result
        mock_gemini.return_value = MOCK_GEMINI_RESPONSE
        # Groq se llama 2 veces: Escritor + QA
        mock_groq.side_effect = [MOCK_GROQ_RESPONSE, qa_approval_response]

        result = await run_generation_graph(BASE_INPUT)

    assert result["status"] == "ok"
    assert result["qa_approved"] is True
    assert result["retry_count"] == 0
    assert result["final_content"] == MOCK_DRAFT_BLOG
    assert result["provider"] == "groq"
    assert result["error"] is None


@pytest.mark.asyncio
async def test_graph_qa_retry_then_approve():
    """QA rechaza en primer intento, escritor reintenta y QA aprueba."""
    mock_rag_result = MagicMock()
    mock_rag_result.chunks = [
        MagicMock(text=c["text"], index=c["index"], metadata=c["metadata"])
        for c in MOCK_RAG_CHUNKS
    ]

    qa_reject_response = LLMResponse(
        content="RECHAZADO\nCorrecciones requeridas:\n1. El título necesita ser más específico.",
        provider="groq",
        model="llama-3.3-70b-versatile",
        tokens_used=80,
        latency_ms=600.0,
    )
    qa_approve_response = LLMResponse(
        content="APROBADO",
        provider="groq",
        model="llama-3.3-70b-versatile",
        tokens_used=50,
        latency_ms=400.0,
    )

    with patch("core.agents.nodes.retrieve_context", new_callable=AsyncMock) as mock_rag, \
         patch("core.llm.providers.gemini_provider.generate", new_callable=AsyncMock) as mock_gemini, \
         patch("core.llm.providers.groq_provider.generate", new_callable=AsyncMock) as mock_groq:

        mock_rag.return_value = mock_rag_result
        mock_gemini.return_value = MOCK_GEMINI_RESPONSE
        # Secuencia: Escritor1 → QA_rechaza → Escritor2 → QA_aprueba
        mock_groq.side_effect = [
            MOCK_GROQ_RESPONSE,   # Escritor intento 1
            qa_reject_response,   # QA rechaza
            MOCK_GROQ_RESPONSE,   # Escritor intento 2 (reintento)
            qa_approve_response,  # QA aprueba
        ]

        result = await run_generation_graph(BASE_INPUT)

    assert result["status"] == "ok"
    assert result["qa_approved"] is True
    assert result["retry_count"] == 1  # Un reintento
    assert result["final_content"] != ""
    assert result["error"] is None


@pytest.mark.asyncio
async def test_graph_max_retries_exceeded():
    """QA rechaza 2 veces → grafo finaliza con qa_failed_max_retries."""
    mock_rag_result = MagicMock()
    mock_rag_result.chunks = [
        MagicMock(text=c["text"], index=c["index"], metadata=c["metadata"])
        for c in MOCK_RAG_CHUNKS
    ]

    qa_reject = LLMResponse(
        content="RECHAZADO\nCorrecciones requeridas:\n1. El contenido no cumple el formato.",
        provider="groq",
        model="llama-3.3-70b-versatile",
        tokens_used=80,
        latency_ms=600.0,
    )

    with patch("core.agents.nodes.retrieve_context", new_callable=AsyncMock) as mock_rag, \
         patch("core.llm.providers.gemini_provider.generate", new_callable=AsyncMock) as mock_gemini, \
         patch("core.llm.providers.groq_provider.generate", new_callable=AsyncMock) as mock_groq:

        mock_rag.return_value = mock_rag_result
        mock_gemini.return_value = MOCK_GEMINI_RESPONSE
        # Escritor → QA rechaza → Escritor → QA rechaza (max alcanzado)
        mock_groq.side_effect = [
            MOCK_GROQ_RESPONSE,
            qa_reject,
            MOCK_GROQ_RESPONSE,
            qa_reject,
        ]

        result = await run_generation_graph(BASE_INPUT)

    # El grafo no crashea — finaliza de todas formas
    assert result["status"] == "qa_failed_max_retries"
    assert result["qa_approved"] is False
    assert result["final_content"] != ""  # Devuelve el último borrador
    assert result["error"] is None


@pytest.mark.asyncio
async def test_graph_rag_failure_continues():
    """Si RAG falla, el grafo continúa con chunks vacíos."""
    with patch("core.agents.nodes.retrieve_context", new_callable=AsyncMock) as mock_rag, \
         patch("core.llm.providers.gemini_provider.generate", new_callable=AsyncMock) as mock_gemini, \
         patch("core.llm.providers.groq_provider.generate", new_callable=AsyncMock) as mock_groq:

        mock_rag.side_effect = Exception("Supabase connection error")
        mock_gemini.return_value = MOCK_GEMINI_RESPONSE
        mock_groq.side_effect = [
            MOCK_GROQ_RESPONSE,
            LLMResponse(content="APROBADO", provider="groq", model="test", tokens_used=10, latency_ms=100.0),
        ]

        result = await run_generation_graph(BASE_INPUT)

    # RAG falla pero el grafo continúa — rag_chunks vacío, error en estado
    assert result["rag_chunks"] == []
    # El grafo no debe crashear completamente
    assert "status" in result

"""Fixtures compartidos para la suite de tests de AutoStory Builder.

Proporciona fixtures reutilizables para org isolation, mocking de
providers LLM, y datos de ejemplo para testing.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from core.rag import Chunk, RAGContext

# ══════════════════════════════════════════════════════════
# Fixtures de organizaciones — para tests de aislamiento RLS
# ══════════════════════════════════════════════════════════


@pytest.fixture
def org_a() -> dict[str, str]:
    """Organización A para tests de multitenancy."""
    return {
        "id": "org-aaaa-1111-2222-333333333333",
        "name": "Empresa Alpha",
        "plan": "pro",
    }


@pytest.fixture
def org_b() -> dict[str, str]:
    """Organización B — debe estar completamente aislada de A."""
    return {
        "id": "org-bbbb-4444-5555-666666666666",
        "name": "Empresa Beta",
        "plan": "free",
    }


# ══════════════════════════════════════════════════════════
# Fixtures de LLM providers — mocks sin llamadas reales
# ══════════════════════════════════════════════════════════


@pytest.fixture
def mock_groq() -> AsyncMock:
    """Mock del provider Groq — no hace llamadas reales a la API."""
    mock = AsyncMock()
    mock.generate.return_value = MagicMock(
        content="Historia generada por mock de Groq",
        provider="groq",
        model="llama-3.3-70b-versatile",
        tokens_used=150,
        latency_ms=200.0,
    )
    return mock


@pytest.fixture
def mock_cohere() -> AsyncMock:
    """Mock del provider Cohere — retorna embeddings de 1024 dims."""
    mock = AsyncMock()
    # Embedding de 1024 dimensiones (Cohere embed-multilingual-v3)
    mock.embed.return_value = [[0.1] * 1024]
    return mock


# ══════════════════════════════════════════════════════════
# Fixtures de datos de ejemplo
# ══════════════════════════════════════════════════════════


@pytest.fixture
def sample_rag_context(org_a: dict[str, str]) -> RAGContext:
    """Contexto RAG de ejemplo con chunks de prueba."""
    return RAGContext(
        query="historia sobre innovación tecnológica",
        org_id=org_a["id"],
        total_results=2,
        chunks=[
            Chunk(
                text="Nuestra empresa lidera la innovación en software desde 2015.",
                index=0,
                source_url="https://example.com/about",
            ),
            Chunk(
                text="Los valores de la marca incluyen transparencia y excelencia.",
                index=1,
                source_url="https://example.com/values",
            ),
        ],
    )


@pytest.fixture
def sample_story() -> dict:
    """Historia de ejemplo para tests."""
    return {
        "id": "story-1111-2222-3333-444444444444",
        "org_id": "org-aaaa-1111-2222-333333333333",
        "title": "Innovación que Transforma",
        "content": "En el corazón de nuestra empresa late la innovación...",
        "story_type": "blog",
        "status": "borrador",
        "credits_used": 1,
    }


# ══════════════════════════════════════════════════════════
# Fixtures de base de datos de testing
# ══════════════════════════════════════════════════════════


@pytest.fixture
def db_test() -> MagicMock:
    """Mock del cliente Supabase para testing.

    En tests de integración, reemplazar con cliente real
    apuntando a SUPABASE_TEST_URL.
    """
    mock_client = MagicMock()
    # Simular respuesta de query
    mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value = (
        MagicMock(data=[], count=0)
    )
    return mock_client

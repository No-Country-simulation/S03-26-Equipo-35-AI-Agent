"""Tests unitarios del LLM router y prompt builder.

Verifica routing, fallback y construcción de prompts.
Usa mocks para providers — no necesita API keys.
"""

from unittest.mock import AsyncMock, patch

import pytest

from core.llm import LLMResponse
from core.llm.prompt_builder import _load_system_prompt, build_story_prompt
from core.llm.router import LLMRoutingError, route
from core.rag import Chunk, RAGContext


class TestPromptBuilder:
    """Tests del constructor de prompts."""

    def test_prompt_includes_rag_context(self) -> None:
        """El prompt incluye el contexto RAG como información de marca.

        Arrange: RAGContext con 2 chunks
        Act: build_story_prompt
        Assert: El user_prompt contiene el texto de los chunks
        """
        context = RAGContext(
            query="test",
            chunks=[
                Chunk(text="Somos una empresa de tecnología.", index=0),
                Chunk(text="Nuestros valores son innovación y calidad.", index=1),
            ],
            org_id="org-1",
            total_results=2,
        )

        system_prompt, user_prompt = build_story_prompt(
            context=context,
            task="Escribe un blog post sobre nuestros valores",
        )

        assert "empresa de tecnología" in user_prompt
        assert "innovación y calidad" in user_prompt
        assert len(system_prompt) > 0

    def test_prompt_5_axes_structure(self) -> None:
        """El user prompt tiene la estructura de los 5 ejes.

        Assert: Contiene Tarea, Tono de Marca, Restricciones, Contexto de Marca
        """
        context = RAGContext(
            query="test",
            chunks=[Chunk(text="Marca de ejemplo.", index=0)],
            org_id="org-1",
        )

        _, user_prompt = build_story_prompt(
            context=context,
            task="Escribe un comunicado",
            brand_tone="formal",
        )

        assert "## Tarea" in user_prompt
        assert "## Tono de Marca" in user_prompt
        assert "## Restricciones" in user_prompt
        assert "## Contexto de Marca" in user_prompt

    def test_empty_task_raises(self) -> None:
        """Tarea vacía lanza ValueError."""
        context = RAGContext(query="", chunks=[], org_id="org-1")

        with pytest.raises(ValueError, match="vacía"):
            build_story_prompt(context=context, task="")

    def test_empty_context_shows_note(self) -> None:
        """Sin chunks RAG, el prompt incluye una nota informativa."""
        context = RAGContext(query="test", chunks=[], org_id="org-1")

        _, user_prompt = build_story_prompt(
            context=context,
            task="Escribe algo",
        )

        assert "No hay contexto de marca disponible" in user_prompt

    def test_load_system_prompt(self) -> None:
        """_load_system_prompt carga el archivo story_generator.md."""
        content = _load_system_prompt("story_generator")
        assert "escritor profesional" in content.lower() or "storytelling" in content.lower()

    def test_load_nonexistent_prompt_raises(self) -> None:
        """System prompt inexistente lanza FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            _load_system_prompt("nonexistent_prompt")


class TestLLMRouter:
    """Tests del router LLM con fallback."""

    @pytest.mark.asyncio
    async def test_groq_is_primary_provider(self) -> None:
        """Groq es el proveedor principal — se intenta primero.

        Arrange: Mock de groq_provider exitoso
        Act: route()
        Assert: Respuesta viene de groq
        """
        mock_response = LLMResponse(
            content="Historia generada",
            provider="groq",
            model="llama-3.3-70b-versatile",
            tokens_used=100,
            latency_ms=500.0,
        )

        context = RAGContext(query="test", chunks=[], org_id="org-1")

        with patch(
            "core.llm.providers.groq_provider.generate",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await route(
                task="Escribe un blog post",
                context=context,
                org_id="org-1",
            )

        assert result.provider == "groq"
        assert result.content == "Historia generada"

    @pytest.mark.asyncio
    async def test_fallback_to_openrouter_on_groq_failure(self) -> None:
        """Si Groq falla, OpenRouter toma el relevo.

        Arrange: Mock groq falla, mock openrouter exitoso
        Act: route()
        Assert: Respuesta viene de openrouter
        """
        mock_openrouter_response = LLMResponse(
            content="Historia desde OpenRouter",
            provider="openrouter",
            model="meta-llama/llama-3.3-70b-instruct",
            tokens_used=120,
            latency_ms=800.0,
        )

        context = RAGContext(query="test", chunks=[], org_id="org-1")

        with (
            patch(
                "core.llm.providers.groq_provider.generate",
                new_callable=AsyncMock,
                side_effect=Exception("Rate limit exceeded"),
            ),
            patch(
                "core.llm.providers.openrouter_provider.generate",
                new_callable=AsyncMock,
                return_value=mock_openrouter_response,
            ),
        ):
            result = await route(
                task="Escribe un blog post",
                context=context,
                org_id="org-1",
            )

        assert result.provider == "openrouter"
        assert result.content == "Historia desde OpenRouter"

    @pytest.mark.asyncio
    async def test_all_providers_fail_raises_routing_error(self) -> None:
        """Si todos fallan, se lanza LLMRoutingError.

        Arrange: Ambos providers fallan
        Act: route()
        Assert: LLMRoutingError
        """
        context = RAGContext(query="test", chunks=[], org_id="org-1")

        with (
            patch(
                "core.llm.providers.groq_provider.generate",
                new_callable=AsyncMock,
                side_effect=Exception("Groq down"),
            ),
            patch(
                "core.llm.providers.openrouter_provider.generate",
                new_callable=AsyncMock,
                side_effect=Exception("OpenRouter down"),
            ),pytest.raises(LLMRoutingError, match="fallaron")
        ):
            await route(
                task="Escribe un blog post",
                context=context,
                org_id="org-1",
            )

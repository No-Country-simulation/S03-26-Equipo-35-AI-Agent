"""Tests de aislamiento RLS (Row Level Security).

🔴 CRÍTICO — CI bloquea si fallan.
Verifica que org_A no puede ver datos de org_B bajo ninguna circunstancia.
"""

from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
class TestRLSIsolation:
    """Suite de tests para verificar aislamiento de datos por organización."""

    async def test_org_a_cannot_see_org_b_stories(
        self,
        org_a: dict[str, str],
        org_b: dict[str, str],
        db_test,
    ) -> None:
        """Verifica que org_A no puede acceder a historias de org_B."""
        from db.repositories.story_repository import get_story_by_id

        # Act
        await get_story_by_id(db_test, "fake-story-id", org_a["id"])

        # Assert: Asegurar que el filtro org_id === org_a['id'] se inyectó en Supabase SDK
        db_test.table.assert_called_with("stories")
        db_test.table().select().eq.assert_any_call("org_id", org_a["id"])

        # Asegurar explícitamente que org_B jamás es consultado
        for call in db_test.table().select().eq.call_args_list:
            if call[0][0] == "org_id":
                assert call[0][1] != org_b["id"], "¡Peligro! Filtro de Org B detectado."

    @patch("core.rag.retriever.cache_get", new_callable=AsyncMock, return_value=None)
    @patch("core.rag.retriever.cache_set", new_callable=AsyncMock, return_value=True)
    @patch("core.rag.retriever.get_admin_client")
    @patch("core.rag.retriever.embed_query")
    async def test_org_a_cannot_see_org_b_embeddings(
        self,
        mock_embed_query,
        mock_get_admin_client,
        mock_cache_set,
        mock_cache_get,
        org_a: dict[str, str],
        org_b: dict[str, str],
        db_test,
    ) -> None:
        """Verifica que los embeddings de org_B no son visibles para org_A."""
        from core.rag.retriever import retrieve_context

        # Arrange
        mock_get_admin_client.return_value = db_test
        db_test.rpc.return_value.execute.return_value.data = []
        mock_embed_query.return_value = [0.1] * 1024

        # Act
        await retrieve_context("prueba aislamientos", org_a["id"])

        # Assert: Verificar que RPC incluye filtro obligatorio p_org_id = org_A
        # V2: ahora llama match_embeddings_hybrid con query_text adicional
        db_test.rpc.assert_called_with(
            "match_embeddings_hybrid",
            {
                "query_embedding": mock_embed_query.return_value,
                "query_text": "prueba aislamientos",
                "match_threshold": 0.3,
                "match_count": 5,
                "match_org_id": org_a["id"]
            }
        )


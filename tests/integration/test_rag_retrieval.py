"""Tests de retrieval RAG.

🟡 IMPORTANTE
Verifica que el retrieval retorna solo documentos de la misma organización.
"""

import pytest


class TestRAGRetrieval:
    """Tests de búsqueda semántica con aislamiento por org."""

    def test_retrieval_returns_only_own_org_docs(
        self,
        org_a: dict[str, str],
        org_b: dict[str, str],
    ) -> None:
        """Retrieval solo retorna documentos de la organización del usuario.

        Arrange: Embeddings para org_A y org_B en la DB
        Act: Buscar desde org_A
        Assert: Solo chunks de org_A en los resultados
        """
        # Arrange
        # TODO: Insertar embeddings para ambas orgs

        # Act
        # TODO: Ejecutar retrieve_context con org_a["id"]

        # Assert
        # TODO: Verificar que todos los chunks pertenecen a org_A
        pytest.skip("TODO: Implementar cuando retriever esté listo")

    def test_retrieval_respects_top_k(
        self,
        org_a: dict[str, str],
    ) -> None:
        """Retrieval respeta el parámetro top_k.

        Arrange: 10 embeddings para org_A
        Act: Buscar con top_k=3
        Assert: Exactamente 3 resultados
        """
        pytest.skip("TODO: Implementar cuando retriever esté listo")

    def test_retrieval_returns_empty_for_no_matches(
        self,
        org_a: dict[str, str],
    ) -> None:
        """Retrieval retorna contexto vacío si no hay matches.

        Arrange: Sin embeddings para org_A
        Act: Buscar desde org_A
        Assert: RAGContext con chunks vacíos
        """
        pytest.skip("TODO: Implementar cuando retriever esté listo")

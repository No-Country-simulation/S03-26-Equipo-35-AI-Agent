"""Tests unitarios del chunker RAG.

Verifica la lógica de chunking con sliding window y overlap.
No requiere API keys ni conexión a servicios externos.
"""

import pytest

from core.rag import Chunk
from core.rag.chunker import chunk_content


class TestChunker:
    """Tests del chunker de contenido."""

    def test_basic_chunking(self) -> None:
        """Texto largo se divide en múltiples chunks.

        Arrange: Texto de 1000 palabras
        Act: chunk_content con chunk_size=100
        Assert: Múltiples chunks generados
        """
        words = ["word"] * 1000
        content = " ".join(words)

        chunks = chunk_content(content, source_url="https://example.com", chunk_size=100, overlap=10)

        assert len(chunks) > 1
        assert all(isinstance(c, Chunk) for c in chunks)
        assert all(c.source_url == "https://example.com" for c in chunks)

    def test_overlap_between_chunks(self) -> None:
        """Chunks consecutivos comparten palabras en el overlap.

        Arrange: Texto con palabras numeradas
        Act: chunk_content con chunk_size=10, overlap=3
        Assert: Las últimas 3 palabras del chunk N aparecen al inicio del chunk N+1
        """
        words = [f"w{i}" for i in range(30)]
        content = " ".join(words)

        chunks = chunk_content(content, chunk_size=10, overlap=3)

        assert len(chunks) >= 2

        # Verificar overlap entre primer y segundo chunk
        first_words = chunks[0].text.split()
        second_words = chunks[1].text.split()
        overlap_from_first = first_words[-3:]
        overlap_in_second = second_words[:3]
        assert overlap_from_first == overlap_in_second

    def test_empty_content_raises_value_error(self) -> None:
        """Contenido vacío lanza ValueError.

        Arrange: String vacío
        Act: chunk_content
        Assert: ValueError
        """
        with pytest.raises(ValueError, match="vacío"):
            chunk_content("")

    def test_whitespace_only_raises_value_error(self) -> None:
        """Contenido solo con whitespace lanza ValueError.

        Arrange: String con solo espacios
        Act: chunk_content
        Assert: ValueError
        """
        with pytest.raises(ValueError, match="vacío"):
            chunk_content("   \n\t   ")

    def test_single_chunk_for_short_content(self) -> None:
        """Texto corto genera un solo chunk.

        Arrange: Texto de 10 palabras (menor que chunk_size default 512)
        Act: chunk_content
        Assert: Exactamente 1 chunk
        """
        content = "Este es un texto corto para probar el chunking."

        chunks = chunk_content(content)

        assert len(chunks) == 1
        assert chunks[0].index == 0
        assert chunks[0].text == content

    def test_chunk_size_must_exceed_overlap(self) -> None:
        """chunk_size <= overlap lanza ValueError.

        Arrange: chunk_size=10, overlap=10
        Act: chunk_content
        Assert: ValueError
        """
        with pytest.raises(ValueError, match="mayor que overlap"):
            chunk_content("test content", chunk_size=10, overlap=10)

    def test_chunk_size_less_than_overlap_raises(self) -> None:
        """chunk_size < overlap lanza ValueError."""
        with pytest.raises(ValueError, match="mayor que overlap"):
            chunk_content("test content", chunk_size=5, overlap=10)

    def test_chunks_are_indexed_sequentially(self) -> None:
        """Los chunks tienen índices secuenciales 0, 1, 2...

        Arrange: Texto largo
        Act: chunk_content
        Assert: Índices van de 0 a N-1
        """
        words = ["word"] * 500
        content = " ".join(words)

        chunks = chunk_content(content, chunk_size=100, overlap=10)

        for i, chunk in enumerate(chunks):
            assert chunk.index == i

    def test_cleans_excessive_whitespace(self) -> None:
        """El chunker limpia whitespace excesivo antes de dividir.

        Arrange: Texto con múltiples espacios y newlines
        Act: chunk_content
        Assert: El texto resultante no tiene whitespace doble
        """
        content = "palabra1   palabra2\n\npárrafo2   con    espacios"

        chunks = chunk_content(content)

        assert "  " not in chunks[0].text
        assert "\n" not in chunks[0].text

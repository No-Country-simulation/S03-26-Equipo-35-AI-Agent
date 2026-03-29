"""Chunker de contenido para el pipeline RAG.

Divide contenido largo en fragmentos (chunks) de tamaño fijo
con overlap para mantener coherencia entre chunks adyacentes.

Configuración por defecto: 512 tokens, 50 tokens de overlap.
Usa tokenización por palabras como aproximación de tokens.
"""

import re

from core.rag import Chunk


def chunk_content(
    content: str,
    source_url: str = "",
    chunk_size: int = 512,
    overlap: int = 50,
) -> list[Chunk]:
    """Divide contenido en chunks de tamaño fijo con overlap.

    Usa tokenización por palabras como aproximación de tokens.
    El overlap entre chunks adyacentes asegura que el contexto
    semántico no se pierda en los bordes.

    Args:
        content: Texto completo a dividir en chunks.
        source_url: URL de origen del contenido (para trazabilidad).
        chunk_size: Tamaño máximo de cada chunk en tokens (aprox. palabras).
                    Default: 512.
        overlap: Número de tokens de solapamiento entre chunks consecutivos.
                 Default: 50.

    Returns:
        Lista de Chunks indexados secuencialmente.

    Raises:
        ValueError: Si chunk_size <= overlap o si el contenido está vacío.
    """
    if chunk_size <= overlap:
        msg = f"chunk_size ({chunk_size}) debe ser mayor que overlap ({overlap})"
        raise ValueError(msg)

    # Limpiar whitespace excesivo
    cleaned = re.sub(r"\s+", " ", content).strip()

    if not cleaned:
        msg = "El contenido está vacío después de limpiar whitespace"
        raise ValueError(msg)

    # Tokenización por palabras
    words = cleaned.split()

    # Si el texto cabe en un solo chunk, retornar directamente
    if len(words) <= chunk_size:
        return [
            Chunk(
                text=" ".join(words),
                index=0,
                source_url=source_url,
            )
        ]

    # Sliding window con overlap
    chunks: list[Chunk] = []
    step = chunk_size - overlap
    positions = list(range(0, len(words), step))

    for index, start in enumerate(positions):
        chunk_words = words[start : start + chunk_size]

        # No crear chunks muy pequeños al final
        if len(chunk_words) < overlap and chunks:
            # Agregar las palabras restantes al último chunk
            last_chunk = chunks[-1]
            combined = last_chunk.text + " " + " ".join(chunk_words)
            chunks[-1] = Chunk(
                text=combined,
                index=last_chunk.index,
                source_url=source_url,
            )
            break

        chunks.append(
            Chunk(
                text=" ".join(chunk_words),
                index=index,
                source_url=source_url,
            )
        )

        # Si ya procesamos todas las palabras, parar
        if start + chunk_size >= len(words):
            break

    return chunks

"""Embedder de chunks usando Cohere embed-multilingual-v3.

Genera vectores de embedding de 1024 dimensiones para cada chunk de texto.
IMPORTANTE: Cohere embed-multilingual-v3 genera 1024 dims, NO 1536.

Usa batch processing (hasta 96 textos por request) para eficiencia.
"""

import os
import time

import cohere
import structlog
from dotenv import load_dotenv

from core.rag import Chunk, EmbeddedChunk

load_dotenv()

logger = structlog.get_logger()

# Límite de Cohere: 96 textos por request
COHERE_BATCH_SIZE = 96

# Modelo de embedding (Cohere embed-multilingual-v3 genera vectores de 1024 dims)
COHERE_MODEL = "embed-multilingual-v3.0"


def _get_cohere_client() -> cohere.ClientV2:
    """Inicializa y retorna el cliente Cohere.

    Returns:
        Cliente Cohere configurado.

    Raises:
        ValueError: Si COHERE_API_KEY no está configurada.
    """
    api_key = os.getenv("COHERE_API_KEY")
    if not api_key:
        msg = (
            "COHERE_API_KEY debe estar configurada en .env. "
            "Obtener en: dashboard.cohere.com"
        )
        raise ValueError(msg)
    return cohere.ClientV2(api_key=api_key)


async def embed_chunks(
    chunks: list[Chunk],
    org_id: str,
) -> list[EmbeddedChunk]:
    """Genera embeddings para una lista de chunks usando Cohere.

    Utiliza el modelo embed-multilingual-v3.0 con input_type='search_document'.
    Procesa en batches de 96 para respetar el límite de Cohere.

    Args:
        chunks: Lista de chunks de texto a embeder.
        org_id: ID de la organización — para trazabilidad y logging.

    Returns:
        Lista de EmbeddedChunks con vectores de 1024 dimensiones.

    Raises:
        ValueError: Si la lista de chunks está vacía o COHERE_API_KEY falta.
        cohere.ApiError: Si Cohere devuelve un error.
    """
    if not chunks:
        msg = "La lista de chunks está vacía"
        raise ValueError(msg)

    client = _get_cohere_client()
    start_time = time.perf_counter()
    embedded_chunks: list[EmbeddedChunk] = []

    # Procesar en batches
    for batch_start in range(0, len(chunks), COHERE_BATCH_SIZE):
        batch = chunks[batch_start : batch_start + COHERE_BATCH_SIZE]
        texts = [chunk.text for chunk in batch]

        response = client.embed(
            texts=texts,
            model=COHERE_MODEL,
            input_type="search_document",
            embedding_types=["float"],
        )

        # Extraer embeddings de la respuesta
        embeddings = response.embeddings.float_

        for chunk, embedding in zip(batch, embeddings, strict=True):
            embedded_chunks.append(
                EmbeddedChunk(chunk=chunk, embedding=embedding)
            )

    duration_ms = (time.perf_counter() - start_time) * 1000

    logger.info(
        "embedder_success",
        total_chunks=len(chunks),
        batches=len(range(0, len(chunks), COHERE_BATCH_SIZE)),
        duration_ms=round(duration_ms, 2),
        org_id=org_id,
    )

    return embedded_chunks


async def embed_query(query: str) -> list[float]:
    """Genera embedding para una query de búsqueda.

    Usa input_type='search_query' de Cohere para optimizar
    el embedding para búsqueda semántica.

    Args:
        query: Texto de la query de búsqueda.

    Returns:
        Vector de 1024 dimensiones.

    Raises:
        ValueError: Si la query está vacía o COHERE_API_KEY falta.
    """
    if not query.strip():
        msg = "La query está vacía"
        raise ValueError(msg)

    client = _get_cohere_client()

    response = client.embed(
        texts=[query],
        model=COHERE_MODEL,
        input_type="search_query",
        embedding_types=["float"],
    )

    embedding = response.embeddings.float_[0]

    logger.info(
        "embedder_query",
        query_length=len(query),
        embedding_dims=len(embedding),
    )

    return embedding

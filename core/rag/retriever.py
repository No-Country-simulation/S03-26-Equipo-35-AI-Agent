"""Retriever semántico para el pipeline RAG.

Recupera chunks relevantes de la base vectorial (Supabase + pgvector)
filtrando siempre por org_id para aislamiento de datos.

Usa la función RPC match_embeddings de Supabase para búsqueda vectorial.

SEGURIDAD: Todo retrieval debe incluir filtro .eq("org_id", org_id).
"""

import structlog

from core.rag import Chunk, RAGContext
from core.rag.embedder import embed_query
from db.client import get_admin_client

logger = structlog.get_logger()

# Threshold mínimo de similarity para incluir un resultado
DEFAULT_MATCH_THRESHOLD = 0.3


async def retrieve_context(
    query: str,
    org_id: str,
    top_k: int = 5,
    match_threshold: float = DEFAULT_MATCH_THRESHOLD,
) -> RAGContext:
    """Recupera chunks relevantes para una query dentro de una organización.

    Realiza búsqueda semántica usando cosine similarity contra los
    embeddings almacenados en Supabase (pgvector). Siempre filtra
    por org_id para garantizar aislamiento entre organizaciones.

    Flujo:
    1. Embedear la query con Cohere (input_type='search_query')
    2. Llamar RPC match_embeddings en Supabase con filtro org_id
    3. Convertir resultados a list[Chunk]
    4. Retornar RAGContext

    Args:
        query: Texto de búsqueda semántica.
        org_id: ID de la organización — requerido para aislamiento de datos.
                Nunca se omite este filtro.
        top_k: Número de chunks a retornar. Default: 5.
        match_threshold: Similarity mínima para incluir un resultado. Default: 0.3.

    Returns:
        RAGContext con chunks relevantes y metadata de la búsqueda.

    Raises:
        ValueError: Si org_id está vacío o query está vacía.
    """
    if not org_id:
        msg = "org_id es requerido para retrieval — aislamiento de datos obligatorio"
        raise ValueError(msg)

    if not query.strip():
        msg = "La query de búsqueda está vacía"
        raise ValueError(msg)

    # 1. Embedear la query
    query_embedding = await embed_query(query)

    # 2. Llamar RPC match_embeddings en Supabase
    client = get_admin_client()

    result = client.rpc(
        "match_embeddings",
        {
            "query_embedding": query_embedding,
            "match_org_id": org_id,
            "match_count": top_k,
            "match_threshold": match_threshold,
        },
    ).execute()

    # 3. Convertir resultados a list[Chunk]
    chunks: list[Chunk] = []
    for row in result.data:
        chunks.append(
            Chunk(
                text=row["chunk_text"],
                index=row["chunk_index"],
                source_url="",
                metadata={
                    "similarity": str(row["similarity"]),
                    "document_id": str(row["document_id"]),
                    "embedding_id": str(row["id"]),
                },
            )
        )

    logger.info(
        "retriever_success",
        query_length=len(query),
        results_count=len(chunks),
        org_id=org_id,
        top_k=top_k,
    )

    # 4. Retornar RAGContext
    return RAGContext(
        query=query,
        chunks=chunks,
        org_id=org_id,
        total_results=len(chunks),
    )

"""Retriever semántico para el pipeline RAG.

Recupera chunks relevantes de la base vectorial (Supabase + pgvector)
filtrando siempre por org_id para aislamiento de datos.

Usa la función RPC match_embeddings de Supabase para búsqueda vectorial.

Incluye caché semántico con Redis: queries repetidas en la misma org
se resuelven instantáneamente sin llamar a Cohere ni Supabase.

SEGURIDAD: Todo retrieval debe incluir filtro .eq("org_id", org_id).
"""

import structlog

from core.cache.redis_client import cache_get, cache_set, make_cache_key
from core.rag import Chunk, RAGContext
from core.rag.embedder import embed_query
from db.client import get_admin_client

logger = structlog.get_logger()

# Threshold mínimo de similarity para incluir un resultado
DEFAULT_MATCH_THRESHOLD = 0.3

# TTL del caché semántico: 1 hora
RAG_CACHE_TTL = 3600


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

    Incluye caché semántico: si la misma query para la misma org
    fue ejecutada recientemente, retorna el resultado cacheado
    sin llamar a Cohere ni Supabase.

    Flujo:
    1. Verificar caché Redis → si hit, retornar instantáneamente
    2. Embedear la query con Cohere (input_type='search_query')
    3. Llamar RPC match_embeddings en Supabase con filtro org_id
    4. Convertir resultados a list[Chunk]
    5. Cachear resultado en Redis con TTL de 1 hora
    6. Retornar RAGContext

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

    # 1. Verificar caché semántico
    cache_key = make_cache_key("rag", org_id, query.strip().lower())
    cached = await cache_get(cache_key)

    if cached is not None:
        logger.info(
            "retriever_cache_hit",
            query_length=len(query),
            org_id=org_id,
            results_count=cached.get("total_results", 0),
        )
        # Reconstruir RAGContext desde caché
        chunks = [
            Chunk(
                text=c["text"],
                index=c["index"],
                source_url=c.get("source_url", ""),
                metadata=c.get("metadata", {}),
            )
            for c in cached.get("chunks", [])
        ]
        return RAGContext(
            query=cached["query"],
            chunks=chunks,
            org_id=org_id,
            total_results=cached["total_results"],
        )

    # 2. Embedear la query
    query_embedding = await embed_query(query)

    # 3. Llamar RPC match_embeddings_hybrid en Supabase (Fase 2: RAG Híbrido)
    # Fallback automático a match_embeddings si la función híbrida no existe aún
    client = get_admin_client()

    try:
        result = client.rpc(
            "match_embeddings_hybrid",
            {
                "query_embedding": query_embedding,
                "query_text": query.strip(),
                "match_org_id": org_id,
                "match_count": top_k,
                "match_threshold": match_threshold,
            },
        ).execute()
        logger.info("retriever_hybrid_rpc_used", org_id=org_id)
    except Exception as hybrid_err:
        logger.info(
            "retriever_hybrid_fallback",
            reason=str(hybrid_err)[:80],
            org_id=org_id,
        )
        result = client.rpc(
            "match_embeddings",
            {
                "query_embedding": query_embedding,
                "match_org_id": org_id,
                "match_count": top_k,
                "match_threshold": match_threshold,
            },
        ).execute()

    # 4. Convertir resultados a list[Chunk]
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

    # 5. Cachear resultado en Redis
    cache_data = {
        "query": query,
        "total_results": len(chunks),
        "chunks": [
            {
                "text": c.text,
                "index": c.index,
                "source_url": c.source_url,
                "metadata": c.metadata,
            }
            for c in chunks
        ],
    }
    await cache_set(cache_key, cache_data, ttl_seconds=RAG_CACHE_TTL)

    # 6. Retornar RAGContext
    return RAGContext(
        query=query,
        chunks=chunks,
        org_id=org_id,
        total_results=len(chunks),
    )


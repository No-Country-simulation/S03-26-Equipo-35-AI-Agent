"""Repositorio de documentos y embeddings RAG.

Acceso a las tablas `documents` y `embeddings` en Supabase
con aislamiento por org_id. Centraliza todas las operaciones
de persistencia del pipeline RAG.
"""

from typing import Any

import structlog
from supabase import Client

from core.rag import EmbeddedChunk

logger = structlog.get_logger()


async def create_document(
    client: Client,
    org_id: str,
    source_url: str,
    title: str,
    raw_content: str,
    doc_type: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Crea un documento en la tabla `documents`.

    Args:
        client: Cliente Supabase (admin — bypasea RLS).
        org_id: ID de la organización — requerido para aislamiento.
        source_url: URL de origen del documento.
        title: Título del documento.
        raw_content: Contenido textual completo.
        doc_type: Tipo de documento ('web', 'file', 'text', 'youtube').
        metadata: Metadatos adicionales del documento.

    Returns:
        Diccionario con los datos del documento creado, incluyendo ID.

    Raises:
        Exception: Si Supabase falla en la inserción.
    """
    result = client.table("documents").insert({
        "org_id": org_id,
        "source_url": source_url,
        "title": title,
        "raw_content": raw_content,
        "doc_type": doc_type,
        "metadata": metadata or {},
    }).execute()

    return result.data[0] if result.data else {}


async def create_embeddings_batch(
    client: Client,
    org_id: str,
    document_id: str,
    embedded_chunks: list[EmbeddedChunk],
) -> int:
    """Inserta un lote de embeddings asociados a un documento.

    Args:
        client: Cliente Supabase (admin — bypasea RLS).
        org_id: ID de la organización — requerido para aislamiento.
        document_id: ID del documento padre.
        embedded_chunks: Lista de chunks con sus vectores de embedding.

    Returns:
        Cantidad de embeddings insertados.

    Raises:
        Exception: Si Supabase falla en la inserción.
    """
    rows = [
        {
            "org_id": org_id,
            "document_id": document_id,
            "chunk_text": ec.chunk.text,
            "chunk_index": ec.chunk.index,
            "embedding": ec.embedding,
            "metadata": ec.chunk.metadata,
        }
        for ec in embedded_chunks
    ]

    client.table("embeddings").insert(rows).execute()

    logger.info(
        "rag_embeddings_created",
        document_id=document_id,
        count=len(rows),
        org_id=org_id,
    )
    return len(rows)


async def get_documents_by_org(
    client: Client,
    org_id: str,
) -> list[dict[str, Any]]:
    """Lista los documentos ingestados de una organización.

    Args:
        client: Cliente Supabase (admin — bypasea RLS).
        org_id: ID de la organización — requerido para aislamiento.

    Returns:
        Lista de diccionarios con datos de documentos, ordenados por fecha.

    Raises:
        Exception: Si Supabase no está disponible.
    """
    result = (
        client.table("documents")
        .select("id, title, doc_type, source_url, created_at")
        .eq("org_id", org_id)
        .order("created_at", desc=True)
        .execute()
    )
    return result.data


async def delete_document_and_embeddings(
    client: Client,
    document_id: str,
    org_id: str,
) -> bool:
    """Elimina un documento y sus embeddings asociados.

    Verifica que el documento pertenezca a la organización antes de eliminar.
    Elimina embeddings primero (FK), luego el documento.

    Args:
        client: Cliente Supabase (admin — bypasea RLS).
        document_id: ID del documento a eliminar.
        org_id: ID de la organización — requerido para aislamiento.

    Returns:
        True si el documento existía y fue eliminado, False si no se encontró.

    Raises:
        Exception: Si Supabase falla en la eliminación.
    """
    # Verificar pertenencia
    doc_check = (
        client.table("documents")
        .select("id")
        .eq("id", document_id)
        .eq("org_id", org_id)
        .execute()
    )

    if not doc_check.data:
        return False

    # Eliminar embeddings primero (FK constraint)
    client.table("embeddings").delete().eq("document_id", document_id).execute()

    # Eliminar documento
    client.table("documents").delete().eq("id", document_id).eq("org_id", org_id).execute()

    logger.info(
        "rag_document_deleted",
        document_id=document_id,
        org_id=org_id,
    )
    return True

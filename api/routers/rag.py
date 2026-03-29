"""Router de pipeline RAG.

Endpoints para ingestión de contenido y búsqueda semántica.
Flujo de ingestión: scrape → chunk → embed → store en Supabase.
"""

from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, HttpUrl

from api.dependencies import get_current_org
from api.schemas import CurrentUser
from core.rag.chunker import chunk_content
from core.rag.embedder import embed_chunks
from core.rag.retriever import retrieve_context
from core.rag.scraper import scrape_url
from db.client import get_admin_client

logger = structlog.get_logger()

router = APIRouter()


# ── Schemas ──


class IngestRequest(BaseModel):
    """Schema de request para ingestión de contenido."""

    url: HttpUrl
    title: str = ""


class IngestResponse(BaseModel):
    """Schema de response para ingestión de contenido."""

    document_id: str
    chunks_count: int
    tier_used: str
    message: str = "Contenido ingestado exitosamente"


class SearchRequest(BaseModel):
    """Schema de request para búsqueda semántica."""

    query: str
    top_k: int = 5


class ChunkResponse(BaseModel):
    """Un chunk individual en la respuesta de búsqueda."""

    text: str
    index: int
    similarity: str = ""
    document_id: str = ""


class SearchResponse(BaseModel):
    """Schema de response para búsqueda semántica."""

    query: str
    chunks: list[ChunkResponse]
    total_results: int
    org_id: str


# ── Endpoints ──


@router.post("/ingest", response_model=IngestResponse)
async def ingest_content(
    request: IngestRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_org)],
) -> IngestResponse:
    """Ingesta contenido de una URL al pipeline RAG.

    Flujo completo: scrape → chunk → embed → store en Supabase.
    Requiere autenticación — org_id se extrae del JWT.
    """
    org_id = current_user.org_id
    url = str(request.url)

    try:
        # 1. Scrape
        scraped = await scrape_url(url, org_id)

        # 2. Chunk
        chunks = chunk_content(
            content=scraped.raw_text,
            source_url=scraped.url,
        )

        # 3. Embed
        embedded = await embed_chunks(chunks, org_id)

        # 4. Store en Supabase
        client = get_admin_client()

        # 4a. Crear documento
        doc_result = client.table("documents").insert({
            "org_id": org_id,
            "source_url": scraped.url,
            "title": request.title or scraped.title,
            "raw_content": scraped.raw_text,
            "doc_type": "web",
            "metadata": scraped.metadata,
        }).execute()

        document_id = doc_result.data[0]["id"]

        # 4b. Insertar embeddings
        embedding_rows = [
            {
                "org_id": org_id,
                "document_id": document_id,
                "chunk_text": ec.chunk.text,
                "chunk_index": ec.chunk.index,
                "embedding": ec.embedding,
                "metadata": ec.chunk.metadata,
            }
            for ec in embedded
        ]

        client.table("embeddings").insert(embedding_rows).execute()

        logger.info(
            "rag_ingest_success",
            document_id=document_id,
            chunks_count=len(chunks),
            org_id=org_id,
        )

        # Determinar qué tier se usó
        tier_used = scraped.metadata.get("tier", "unknown")

        return IngestResponse(
            document_id=document_id,
            chunks_count=len(chunks),
            tier_used=tier_used,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error("rag_ingest_failed", error=str(e)[:200], org_id=org_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al ingestar contenido",
        ) from e


@router.post("/search", response_model=SearchResponse)
async def search_context(
    request: SearchRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_org)],
) -> SearchResponse:
    """Busca contexto relevante en la base de conocimiento de la organización.

    Requiere autenticación — org_id se extrae del JWT para aislamiento.
    """
    org_id = current_user.org_id

    try:
        rag_context = await retrieve_context(
            query=request.query,
            org_id=org_id,
            top_k=request.top_k,
        )

        chunks_response = [
            ChunkResponse(
                text=chunk.text,
                index=chunk.index,
                similarity=chunk.metadata.get("similarity", ""),
                document_id=chunk.metadata.get("document_id", ""),
            )
            for chunk in rag_context.chunks
        ]

        return SearchResponse(
            query=rag_context.query,
            chunks=chunks_response,
            total_results=rag_context.total_results,
            org_id=org_id,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error("rag_search_failed", error=str(e)[:200], org_id=org_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al buscar contexto",
        ) from e

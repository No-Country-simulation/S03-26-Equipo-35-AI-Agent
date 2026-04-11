"""Router de pipeline RAG.

Endpoints para ingestión de contenido y búsqueda semántica.
Flujo de ingestión: scrape → chunk → embed → store en Supabase.
"""

from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
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


# ── Ingestión de Archivos ──


class IngestFileResponse(BaseModel):
    """Schema de response para ingestión de archivo."""

    document_id: str
    chunks_count: int
    filename: str
    file_type: str
    message: str = "Archivo ingestado exitosamente"


@router.post("/ingest-file", response_model=IngestFileResponse)
async def ingest_file(
    file: UploadFile = File(...),
    title: str = Form(""),
    current_user: CurrentUser = Depends(get_current_org),
) -> IngestFileResponse:
    """Ingesta un archivo (PDF, DOCX, TXT) al pipeline RAG.

    Flujo: extraer texto → chunk → embed → store en Supabase.
    """
    from core.rag.file_extractor import extract_text_from_file

    org_id = current_user.org_id

    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    ALLOWED_TYPES = {
        "application/pdf", 
        "text/plain", 
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    }

    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Tipo de archivo no permitido"
        )

    file.file.seek(0, 2)
    size = file.file.tell()
    if size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, 
            detail="Archivo muy grande (máximo 50MB)"
        )
    file.file.seek(0)

    try:
        file_bytes = await file.read()
        text = await extract_text_from_file(
            file_bytes=file_bytes,
            filename=file.filename or "unknown",
            content_type=file.content_type or "",
        )

        # chunk → embed → store
        chunks = chunk_content(content=text, source_url=file.filename or "uploaded_file")
        embedded = await embed_chunks(chunks, org_id)

        client = get_admin_client()
        doc_result = client.table("documents").insert({
            "org_id": org_id,
            "source_url": f"file://{file.filename}",
            "title": title or file.filename or "Archivo sin título",
            "raw_content": text,
            "doc_type": "file",
            "metadata": {
                "filename": file.filename,
                "content_type": file.content_type,
                "size_bytes": len(file_bytes),
            },
        }).execute()

        document_id = doc_result.data[0]["id"]

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
            "rag_ingest_file_success",
            document_id=document_id,
            filename=file.filename,
            chunks_count=len(chunks),
            org_id=org_id,
        )

        from core.rag.file_extractor import detect_file_type
        file_type = detect_file_type(file.filename or "", file.content_type or "") or "unknown"

        return IngestFileResponse(
            document_id=document_id,
            chunks_count=len(chunks),
            filename=file.filename or "unknown",
            file_type=file_type,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error(
            "rag_ingest_file_failed",
            error=str(e)[:200],
            org_id=org_id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al ingestar archivo",
        ) from e


# ── Ingestión de Texto Libre ──


class IngestTextRequest(BaseModel):
    """Schema para ingestión de texto libre."""

    text: str
    title: str = "Texto manual"


class IngestTextResponse(BaseModel):
    """Schema de response para ingestión de texto."""

    document_id: str
    chunks_count: int
    message: str = "Texto ingestado exitosamente"


@router.post("/ingest-text", response_model=IngestTextResponse)
async def ingest_text(
    request: IngestTextRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_org)],
) -> IngestTextResponse:
    """Ingesta texto libre al pipeline RAG.

    El usuario pega guidelines de marca, tono de voz, misión, etc.
    Flujo: texto → chunk → embed → store en Supabase.
    """
    org_id = current_user.org_id

    if len(request.text.strip()) < 20:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El texto debe tener al menos 20 caracteres.",
        )

    try:
        chunks = chunk_content(content=request.text, source_url="manual_text")
        embedded = await embed_chunks(chunks, org_id)

        client = get_admin_client()
        doc_result = client.table("documents").insert({
            "org_id": org_id,
            "source_url": "manual://text",
            "title": request.title,
            "raw_content": request.text,
            "doc_type": "text",
            "metadata": {"source": "manual_input"},
        }).execute()

        document_id = doc_result.data[0]["id"]

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
            "rag_ingest_text_success",
            document_id=document_id,
            chunks_count=len(chunks),
            org_id=org_id,
        )

        return IngestTextResponse(
            document_id=document_id,
            chunks_count=len(chunks),
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error("rag_ingest_text_failed", error=str(e)[:200], org_id=org_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al ingestar texto",
        ) from e


# ── Ingestión de YouTube ──


class IngestYouTubeRequest(BaseModel):
    """Schema para ingestión de video de YouTube."""

    url: str
    title: str = ""


class IngestYouTubeResponse(BaseModel):
    """Schema de response para ingestión de YouTube."""

    document_id: str
    chunks_count: int
    language: str
    video_id: str
    message: str = "Transcripción de YouTube ingestada exitosamente"


@router.post("/ingest-youtube", response_model=IngestYouTubeResponse)
async def ingest_youtube(
    request: IngestYouTubeRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_org)],
) -> IngestYouTubeResponse:
    """Ingesta la transcripción de un video de YouTube al pipeline RAG.

    Flujo: extraer transcripción → chunk → embed → store en Supabase.
    """
    from core.multimedia.youtube import get_transcript

    org_id = current_user.org_id

    try:
        transcript = await get_transcript(request.url)
        text = transcript["text"]
        language = transcript["language"]
        video_id = transcript["video_id"]

        chunks = chunk_content(content=text, source_url=request.url)
        embedded = await embed_chunks(chunks, org_id)

        client = get_admin_client()
        doc_result = client.table("documents").insert({
            "org_id": org_id,
            "source_url": request.url,
            "title": request.title or f"YouTube: {video_id}",
            "raw_content": text,
            "doc_type": "youtube",
            "metadata": {
                "video_id": video_id,
                "language": language,
                "source": "youtube_transcript",
            },
        }).execute()

        document_id = doc_result.data[0]["id"]

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
            "rag_ingest_youtube_success",
            document_id=document_id,
            video_id=video_id,
            chunks_count=len(chunks),
            org_id=org_id,
        )

        return IngestYouTubeResponse(
            document_id=document_id,
            chunks_count=len(chunks),
            language=language,
            video_id=video_id,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error(
            "rag_ingest_youtube_failed",
            error=str(e)[:200],
            org_id=org_id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al ingestar YouTube",
        ) from e


# ── Listar Documentos Ingestados ──


class DocumentResponse(BaseModel):
    """Schema de un documento ingestado."""

    id: str
    title: str
    doc_type: str
    source_url: str
    created_at: str


class DocumentListResponse(BaseModel):
    """Schema de response para listado de documentos."""

    documents: list[DocumentResponse]
    total: int


@router.get("/documents", response_model=DocumentListResponse)
async def list_documents(
    current_user: Annotated[CurrentUser, Depends(get_current_org)],
) -> DocumentListResponse:
    """Lista los documentos ingestados de la organización.

    Filtrado por org_id del JWT — cada org solo ve sus documentos.
    """
    org_id = current_user.org_id

    try:
        client = get_admin_client()
        result = (
            client.table("documents")
            .select("id, title, doc_type, source_url, created_at")
            .eq("org_id", org_id)
            .order("created_at", desc=True)
            .execute()
        )

        documents = [
            DocumentResponse(
                id=row["id"],
                title=row["title"],
                doc_type=row["doc_type"],
                source_url=row["source_url"],
                created_at=row["created_at"],
            )
            for row in result.data
        ]

        return DocumentListResponse(
            documents=documents,
            total=len(documents),
        )

    except Exception as e:
        logger.error("rag_list_docs_failed", error=str(e)[:200], org_id=org_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al listar documentos",
        ) from e


# ── Eliminar Documento ──


class DeleteDocumentResponse(BaseModel):
    """Schema de response para eliminación de documento."""

    document_id: str
    message: str = "Documento eliminado exitosamente"


@router.delete("/documents/{document_id}", response_model=DeleteDocumentResponse)
async def delete_document(
    document_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_org)],
) -> DeleteDocumentResponse:
    """Elimina un documento y sus embeddings asociados.

    Verifica que el documento pertenezca a la organización del JWT
    antes de eliminarlo — nunca se puede eliminar documentos ajenos.
    """
    org_id = current_user.org_id

    try:
        client = get_admin_client()

        # Verificar que el documento pertenece a esta org
        doc_check = (
            client.table("documents")
            .select("id")
            .eq("id", document_id)
            .eq("org_id", org_id)
            .execute()
        )

        if not doc_check.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Documento no encontrado o no pertenece a tu organización.",
            )

        # Eliminar embeddings asociados primero (FK)
        client.table("embeddings").delete().eq("document_id", document_id).execute()

        # Eliminar el documento
        client.table("documents").delete().eq("id", document_id).eq("org_id", org_id).execute()

        logger.info(
            "rag_document_deleted",
            document_id=document_id,
            org_id=org_id,
        )

        return DeleteDocumentResponse(document_id=document_id)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("rag_delete_failed", error=str(e)[:200], org_id=org_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al eliminar el documento",
        ) from e

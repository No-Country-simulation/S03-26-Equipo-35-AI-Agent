-- ══════════════════════════════════════════════════════════
-- Migration 006: Función RPC match_embeddings
-- AutoStory Builder — Búsqueda vectorial semántica
-- Requiere: tabla embeddings (migration 002)
-- ══════════════════════════════════════════════════════════

-- Función para búsqueda de embeddings por cosine similarity
-- Filtra SIEMPRE por org_id — aislamiento entre organizaciones
CREATE OR REPLACE FUNCTION match_embeddings(
    query_embedding vector(1024),
    match_org_id UUID,
    match_count INT DEFAULT 5,
    match_threshold FLOAT DEFAULT 0.3
)
RETURNS TABLE (
    id UUID,
    chunk_text TEXT,
    chunk_index INT,
    similarity FLOAT,
    metadata JSONB,
    document_id UUID
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    RETURN QUERY
    SELECT
        e.id,
        e.chunk_text,
        e.chunk_index,
        (1 - (e.embedding <=> query_embedding))::FLOAT AS similarity,
        e.metadata,
        e.document_id
    FROM embeddings e
    WHERE e.org_id = match_org_id
      AND (1 - (e.embedding <=> query_embedding)) > match_threshold
    ORDER BY e.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

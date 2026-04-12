-- ══════════════════════════════════════════════════════════
-- Migration 011: Búsqueda Híbrida (Vectorial + Full-Text)
-- AutoStory Builder — RAG Avanzado con Reciprocal Rank Fusion
-- Requiere: tabla embeddings (migration 002)
-- ══════════════════════════════════════════════════════════

-- NOTA: Por los límites de memoria (32MB) de la capa gratuita de Supabase,
-- el cálculo de Full-Text Search (FTS) se hace dinámicamente ("on the fly")
-- en la query. Para el volumen MVP de datos, es igual de instantáneo y evita
-- crashear la base de datos con columnas STORED o índices GIN.

-- Función RPC de Búsqueda Híbrida con Reciprocal Rank Fusion (RRF)
-- Combina similitud coseno (semántica) con ts_rank (palabras clave exactas)
-- para que no se pierdan nombres propios, cifras ni datos concretos.
CREATE OR REPLACE FUNCTION match_embeddings_hybrid(
    query_embedding vector(1024),
    query_text TEXT,
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
DECLARE
    rrf_k CONSTANT INT := 60;  -- Constante RRF (estándar de la literatura)
BEGIN
    RETURN QUERY
    WITH
    -- Sub-ranking 1: Similitud vectorial (semántica)
    semantic AS (
        SELECT
            e.id,
            e.chunk_text,
            e.chunk_index,
            (1 - (e.embedding <=> query_embedding))::FLOAT AS cosine_sim,
            e.metadata,
            e.document_id,
            ROW_NUMBER() OVER (ORDER BY e.embedding <=> query_embedding) AS sem_rank
        FROM embeddings e
        WHERE e.org_id = match_org_id
          AND (1 - (e.embedding <=> query_embedding)) > match_threshold
    ),
    -- Sub-ranking 2: Full-Text Search (palabras clave exactas)
    keyword AS (
        SELECT
            e.id,
            ts_rank(to_tsvector('spanish', e.chunk_text), plainto_tsquery('spanish', query_text)) AS kw_score,
            ROW_NUMBER() OVER (
                ORDER BY ts_rank(to_tsvector('spanish', e.chunk_text), plainto_tsquery('spanish', query_text)) DESC
            ) AS kw_rank
        FROM embeddings e
        WHERE e.org_id = match_org_id
          AND to_tsvector('spanish', e.chunk_text) @@ plainto_tsquery('spanish', query_text)
    ),
    -- Fusión RRF: combinar ambos rankings
    fused AS (
        SELECT
            s.id,
            s.chunk_text,
            s.chunk_index,
            s.cosine_sim AS similarity,
            s.metadata,
            s.document_id,
            -- Score RRF: suma de inversos de posición en cada ranking
            (1.0 / (rrf_k + s.sem_rank))
            + COALESCE((1.0 / (rrf_k + k.kw_rank)), 0)
            AS rrf_score
        FROM semantic s
        LEFT JOIN keyword k ON s.id = k.id
    )
    SELECT
        f.id,
        f.chunk_text,
        f.chunk_index,
        f.similarity,
        f.metadata,
        f.document_id
    FROM fused f
    ORDER BY f.rrf_score DESC
    LIMIT match_count;
END;
$$;

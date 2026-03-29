-- ══════════════════════════════════════════════════════════
-- Migration 002: Crear tabla embeddings + documents
-- AutoStory Builder — RAG Pipeline
-- IMPORTANTE: vector(1024) — Cohere embed-multilingual-v3
-- ══════════════════════════════════════════════════════════

-- Extensión pgvector (debe estar habilitada en Supabase)
CREATE EXTENSION IF NOT EXISTS vector;

-- Tabla de documentos fuente
CREATE TABLE IF NOT EXISTS documents (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id      UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    source_url  TEXT,
    title       TEXT NOT NULL,
    raw_content TEXT NOT NULL,
    doc_type    TEXT NOT NULL DEFAULT 'web' CHECK (doc_type IN ('web', 'pdf', 'text', 'image')),
    metadata    JSONB DEFAULT '{}',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_documents_org_id ON documents (org_id);

-- Tabla de embeddings (chunks)
CREATE TABLE IF NOT EXISTS embeddings (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id      UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_text  TEXT NOT NULL,
    chunk_index INT NOT NULL,
    embedding   vector(1024) NOT NULL,  -- Cohere embed-multilingual-v3 = 1024 dims
    metadata    JSONB DEFAULT '{}',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_embeddings_org_id ON embeddings (org_id);
CREATE INDEX IF NOT EXISTS idx_embeddings_document_id ON embeddings (document_id);

-- Index IVFFlat para búsqueda vectorial eficiente
-- NOTA: Crear después de tener datos (>1000 rows recomendado)
-- lists = sqrt(n_rows) como regla general
CREATE INDEX IF NOT EXISTS idx_embeddings_vector
    ON embeddings
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- ── Row Level Security ──
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE embeddings ENABLE ROW LEVEL SECURITY;

-- Políticas: solo acceso a datos de la propia organización
CREATE POLICY "documents_select_own"
    ON documents FOR SELECT
    USING (org_id::text = auth.jwt() ->> 'org_id');

CREATE POLICY "documents_insert_own"
    ON documents FOR INSERT
    WITH CHECK (org_id::text = auth.jwt() ->> 'org_id');

CREATE POLICY "documents_delete_own"
    ON documents FOR DELETE
    USING (org_id::text = auth.jwt() ->> 'org_id');

CREATE POLICY "embeddings_select_own"
    ON embeddings FOR SELECT
    USING (org_id::text = auth.jwt() ->> 'org_id');

CREATE POLICY "embeddings_insert_own"
    ON embeddings FOR INSERT
    WITH CHECK (org_id::text = auth.jwt() ->> 'org_id');

CREATE POLICY "embeddings_delete_own"
    ON embeddings FOR DELETE
    USING (org_id::text = auth.jwt() ->> 'org_id');

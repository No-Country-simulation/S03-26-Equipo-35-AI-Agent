-- ══════════════════════════════════════════════════════════
-- Migration 003: Crear tabla stories
-- AutoStory Builder — Contenido narrativo generado
-- ══════════════════════════════════════════════════════════

-- Tipo enum para estados de aprobación
DO $$ BEGIN
    CREATE TYPE story_status AS ENUM (
        'borrador',
        'en_revision',
        'aprobado',
        'rechazado',
        'publicado'
    );
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

CREATE TABLE IF NOT EXISTS stories (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id          UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    title           TEXT NOT NULL,
    content         TEXT NOT NULL DEFAULT '',
    story_type      TEXT NOT NULL DEFAULT 'blog' CHECK (story_type IN ('blog', 'social', 'internal', 'press', 'email')),
    status          story_status NOT NULL DEFAULT 'borrador',
    created_by      UUID NOT NULL,
    prompt_used     TEXT,
    rag_context_ids UUID[] DEFAULT '{}',
    llm_provider    TEXT,
    credits_used    INT NOT NULL DEFAULT 0,
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_stories_org_id ON stories (org_id);
CREATE INDEX IF NOT EXISTS idx_stories_status ON stories (status);
CREATE INDEX IF NOT EXISTS idx_stories_created_by ON stories (created_by);
CREATE INDEX IF NOT EXISTS idx_stories_created_at ON stories (created_at DESC);

-- ── Row Level Security ──
ALTER TABLE stories ENABLE ROW LEVEL SECURITY;

CREATE POLICY "stories_select_own"
    ON stories FOR SELECT
    USING (org_id::text = auth.jwt() ->> 'org_id');

CREATE POLICY "stories_insert_own"
    ON stories FOR INSERT
    WITH CHECK (org_id::text = auth.jwt() ->> 'org_id');

CREATE POLICY "stories_update_own"
    ON stories FOR UPDATE
    USING (org_id::text = auth.jwt() ->> 'org_id');

-- Trigger para updated_at
CREATE TRIGGER trigger_stories_updated_at
    BEFORE UPDATE ON stories
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

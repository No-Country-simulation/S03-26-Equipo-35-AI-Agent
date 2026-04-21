-- ══════════════════════════════════════════════════════════
-- Migration 010: Crear tabla golden_examples
-- AutoStory Builder — Post Dorados (Dynamic Few-Shot)
-- Requiere: tabla organizations (migration 001)
-- ══════════════════════════════════════════════════════════

-- Almacena publicaciones "ideales" que se inyectan como ejemplos
-- al LLM para que imite su estilo, tono y estructura.
-- Límite de 3 por combinación (org_id, story_type, tone) enforced en app.

CREATE TABLE IF NOT EXISTS golden_examples (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id          UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    story_type      TEXT NOT NULL DEFAULT 'blog',
    tone            TEXT NOT NULL DEFAULT 'profesional',
    title           TEXT NOT NULL DEFAULT '',
    content         TEXT NOT NULL,
    source          TEXT NOT NULL DEFAULT 'manual' CHECK (source IN ('manual', 'historia')),
    source_story_id UUID REFERENCES stories(id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_golden_org_type_tone
    ON golden_examples (org_id, story_type, tone);

-- ── Row Level Security ──
ALTER TABLE golden_examples ENABLE ROW LEVEL SECURITY;

CREATE POLICY "golden_select_own"
    ON golden_examples FOR SELECT
    USING (org_id::text = auth.jwt() ->> 'org_id');

CREATE POLICY "golden_insert_own"
    ON golden_examples FOR INSERT
    WITH CHECK (org_id::text = auth.jwt() ->> 'org_id');

CREATE POLICY "golden_delete_own"
    ON golden_examples FOR DELETE
    USING (org_id::text = auth.jwt() ->> 'org_id');

-- ══════════════════════════════════════════════════════════
-- Migration 005: Crear tabla approval_history
-- AutoStory Builder — Historial de transiciones de aprobación
-- ══════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS approval_history (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    story_id    UUID NOT NULL REFERENCES stories(id) ON DELETE CASCADE,
    org_id      UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    from_status story_status NOT NULL,
    to_status   story_status NOT NULL,
    changed_by  UUID NOT NULL,
    role        TEXT NOT NULL CHECK (role IN ('editor', 'revisor', 'admin')),
    comment     TEXT DEFAULT '',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- NOTA: Tabla inmutable — cada entrada es un evento histórico
-- No se permiten UPDATE ni DELETE

CREATE INDEX IF NOT EXISTS idx_approval_history_story_id ON approval_history (story_id);
CREATE INDEX IF NOT EXISTS idx_approval_history_org_id ON approval_history (org_id);
CREATE INDEX IF NOT EXISTS idx_approval_history_created_at ON approval_history (created_at DESC);

-- ── Row Level Security ──
ALTER TABLE approval_history ENABLE ROW LEVEL SECURITY;

CREATE POLICY "approval_history_select_own"
    ON approval_history FOR SELECT
    USING (org_id::text = auth.jwt() ->> 'org_id');

CREATE POLICY "approval_history_insert_own"
    ON approval_history FOR INSERT
    WITH CHECK (org_id::text = auth.jwt() ->> 'org_id');

-- NO crear políticas de UPDATE o DELETE — el historial es inmutable

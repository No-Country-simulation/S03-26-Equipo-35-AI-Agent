-- Migración 008: Tabla de versiones de historias
-- Propósito: Versionado completo de contenido editado manualmente.
-- Cada vez que un usuario edita una historia, se guarda un snapshot
-- del contenido anterior como versión inmutable.

CREATE TABLE IF NOT EXISTS story_versions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    story_id UUID NOT NULL REFERENCES stories(id) ON DELETE CASCADE,
    org_id UUID NOT NULL REFERENCES organizations(id),
    version_number INTEGER NOT NULL DEFAULT 1,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    edited_by UUID,
    edit_summary TEXT DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Índice para queries frecuentes: listar versiones de una historia
CREATE INDEX idx_story_versions_story_id
    ON story_versions(story_id, version_number DESC);

-- Índice para filtro por organización (RLS performance)
CREATE INDEX idx_story_versions_org_id
    ON story_versions(org_id);

-- RLS: cada organización solo ve sus versiones
ALTER TABLE story_versions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "story_versions_org_isolation"
    ON story_versions
    FOR ALL
    USING (org_id = auth.uid()::uuid);

-- Política para service role (admin client)
CREATE POLICY "story_versions_service_role"
    ON story_versions
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

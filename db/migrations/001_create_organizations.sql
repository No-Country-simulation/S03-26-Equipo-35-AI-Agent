-- ══════════════════════════════════════════════════════════
-- Migration 001: Crear tabla organizations
-- AutoStory Builder — Multitenancy base
-- ══════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS organizations (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT NOT NULL,
    plan        TEXT NOT NULL DEFAULT 'free' CHECK (plan IN ('free', 'pro', 'enterprise')),
    settings    JSONB DEFAULT '{}',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Índice para búsqueda por nombre
CREATE INDEX IF NOT EXISTS idx_organizations_name ON organizations (name);

-- ── Row Level Security ──
ALTER TABLE organizations ENABLE ROW LEVEL SECURITY;

-- Política: los usuarios solo ven su propia organización
CREATE POLICY "organizations_select_own"
    ON organizations
    FOR SELECT
    USING (id = (auth.jwt() ->> 'org_id')::UUID);

CREATE POLICY "organizations_update_own"
    ON organizations
    FOR UPDATE
    USING (id = (auth.jwt() ->> 'org_id')::UUID);

-- Trigger para actualizar updated_at
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_organizations_updated_at
    BEFORE UPDATE ON organizations
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();
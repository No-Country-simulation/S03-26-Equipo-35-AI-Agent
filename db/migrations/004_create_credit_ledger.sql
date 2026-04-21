-- ══════════════════════════════════════════════════════════
-- Migration 004: Crear tabla credit_ledger
-- AutoStory Builder — Sistema de créditos (ledger inmutable)
-- ══════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS credit_ledger (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id      UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    amount      INT NOT NULL,  -- positivo=recarga, negativo=consumo
    operation   TEXT NOT NULL CHECK (operation IN ('purchase', 'deduction', 'refund', 'bonus', 'adjustment')),
    story_id    UUID REFERENCES stories(id) ON DELETE SET NULL,
    description TEXT DEFAULT '',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- NOTA: No hay UPDATE ni DELETE en un ledger — es inmutable por diseño
-- Las correcciones se hacen con entries de tipo 'refund' o 'adjustment'

CREATE INDEX IF NOT EXISTS idx_credit_ledger_org_id ON credit_ledger (org_id);
CREATE INDEX IF NOT EXISTS idx_credit_ledger_created_at ON credit_ledger (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_credit_ledger_operation ON credit_ledger (operation);

-- ── Row Level Security ──
ALTER TABLE credit_ledger ENABLE ROW LEVEL SECURITY;

CREATE POLICY "credit_ledger_select_own"
    ON credit_ledger FOR SELECT
    USING (org_id::text = auth.jwt() ->> 'org_id');

CREATE POLICY "credit_ledger_insert_own"
    ON credit_ledger FOR INSERT
    WITH CHECK (org_id::text = auth.jwt() ->> 'org_id');

-- NO crear políticas de UPDATE o DELETE — el ledger es inmutable

-- Vista materializada para balance actual por org (opcional, para performance)
-- CREATE MATERIALIZED VIEW credit_balances AS
-- SELECT org_id, SUM(amount) as balance
-- FROM credit_ledger
-- GROUP BY org_id;

-- ══════════════════════════════════════════════════════════
-- Migration 007: Función RPC get_credit_balance
-- AutoStory Builder — Balance de créditos por organización
-- Requiere: tabla credit_ledger (migration 004)
-- ══════════════════════════════════════════════════════════

-- Función para obtener el balance actual de créditos de una org
CREATE OR REPLACE FUNCTION get_credit_balance(p_org_id UUID)
RETURNS INT
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    balance INT;
BEGIN
    SELECT COALESCE(SUM(amount), 0)
    INTO balance
    FROM credit_ledger
    WHERE org_id = p_org_id;

    RETURN balance;
END;
$$;

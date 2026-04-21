-- Migración 009: Share token para publicación web
-- Propósito: Permitir compartir historias con una URL pública sin autenticación.
-- El share_token es un UUID único que se genera al publicar.
-- Revocar el acceso = eliminar el share_token (NULL).

ALTER TABLE stories ADD COLUMN IF NOT EXISTS share_token UUID UNIQUE;

-- Índice parcial: solo indexar las historias que están compartidas
CREATE INDEX IF NOT EXISTS idx_stories_share_token
    ON stories(share_token) WHERE share_token IS NOT NULL;

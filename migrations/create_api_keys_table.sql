-- Migración: Crear tabla api_keys
-- Fecha: 2025-01-XX
-- Descripción: Crea la tabla para almacenar API keys de usuarios con hash SHA-256

-- ============================================
-- Crear tabla api_keys
-- ============================================
CREATE TABLE IF NOT EXISTS api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    key_hash TEXT NOT NULL UNIQUE,
    name TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    last_used_at TIMESTAMP
);

-- Crear índices para búsquedas rápidas
CREATE INDEX IF NOT EXISTS idx_api_keys_key_hash ON api_keys(key_hash);
CREATE INDEX IF NOT EXISTS idx_api_keys_user_id ON api_keys(user_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_last_used_at ON api_keys(last_used_at);

-- Comentarios en la tabla y columnas
COMMENT ON TABLE api_keys IS 'Almacena las API keys hasheadas de los usuarios';
COMMENT ON COLUMN api_keys.key_hash IS 'Hash SHA-256 de la API key (nunca almacenar la key en texto plano)';
COMMENT ON COLUMN api_keys.name IS 'Nombre/descripción opcional de la API key para facilitar su gestión';
COMMENT ON COLUMN api_keys.last_used_at IS 'Última vez que se usó esta API key (para auditoría)';

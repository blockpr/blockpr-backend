import hashlib
import secrets
from datetime import datetime
from uuid import uuid4, UUID

from app.config.database import get_db_pool
from app.models.api_key import ApiKey


def _hash_api_key(key: str) -> str:
    """SHA-256 hash usado para almacenar API keys sin exponer el valor original."""
    return hashlib.sha256(key.encode()).hexdigest()


def _generate_api_key() -> str:
    """Genera una nueva API key con prefijo bpk_."""
    # Generar 32 caracteres alfanuméricos seguros
    random_part = secrets.token_urlsafe(32)
    return f"bpk_{random_part}"


async def generate_api_key(user_id: UUID, name: str | None = None) -> tuple[str, ApiKey]:
    """
    Genera una nueva API key para un usuario.
    
    Args:
        user_id: UUID del usuario
        name: Nombre opcional para la API key
        
    Returns:
        Tupla con (api_key_en_texto_plano, ApiKey_object)
        
    Raises:
        ValueError: Si el usuario no existe o está inactivo
    """
    pool = get_db_pool()
    async with pool.acquire() as conn:
        # Verificar que el usuario existe y está activo
        user_row = await conn.fetchrow(
            "SELECT id, is_active FROM users WHERE id = $1",
            user_id
        )
        if not user_row:
            raise ValueError("User not found")
        if not user_row["is_active"]:
            raise ValueError("User account is inactive")
        
        # Generar la API key
        api_key = _generate_api_key()
        key_hash = _hash_api_key(api_key)
        
        # Verificar que el hash no existe (muy improbable pero por seguridad)
        existing = await conn.fetchrow(
            "SELECT id FROM api_keys WHERE key_hash = $1",
            key_hash
        )
        if existing:
            # Si por alguna razón existe, generar otra
            api_key = _generate_api_key()
            key_hash = _hash_api_key(api_key)
        
        # Insertar en la base de datos
        now = datetime.utcnow()
        
        # Debug: log el name que se va a insertar
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Inserting API key with name: {repr(name)}, type: {type(name)}")
        
        row = await conn.fetchrow(
            """
            INSERT INTO api_keys (id, user_id, key_hash, name, created_at)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING *
            """,
            uuid4(), user_id, key_hash, name, now
        )
        
        logger.info(f"Inserted row name value: {repr(row.get('name'))}, type: {type(row.get('name'))}")
        
        api_key_obj = ApiKey.from_dict(dict(row))
        logger.info(f"ApiKey object name: {repr(api_key_obj.name)}")
        return api_key, api_key_obj


async def validate_api_key(key: str) -> tuple[UUID, UUID] | None:
    """
    Valida una API key y retorna el user_id y api_key_id si es válida.
    Actualiza last_used_at.
    
    Args:
        key: API key en texto plano
        
    Returns:
        Tupla (user_id, api_key_id) si es válida, None si no lo es
    """
    if not key or not key.startswith("bpk_"):
        return None
    
    key_hash = _hash_api_key(key)
    pool = get_db_pool()
    async with pool.acquire() as conn:
        # Buscar la key y verificar que el usuario esté activo
        row = await conn.fetchrow(
            """
            SELECT ak.id, ak.user_id
            FROM api_keys ak
            JOIN users u ON u.id = ak.user_id
            WHERE ak.key_hash = $1 AND u.is_active = true
            """,
            key_hash
        )
        
        if not row:
            return None
        
        api_key_id = row["id"]
        user_id = row["user_id"]
        
        # Actualizar last_used_at
        await conn.execute(
            "UPDATE api_keys SET last_used_at = $1 WHERE id = $2",
            datetime.utcnow(), api_key_id
        )
        
        return user_id, api_key_id


async def list_user_api_keys(user_id: UUID) -> list[ApiKey]:
    """
    Lista todas las API keys de un usuario (sin mostrar la key completa).
    
    Args:
        user_id: UUID del usuario
        
    Returns:
        Lista de objetos ApiKey
    """
    pool = get_db_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, user_id, key_hash, name, created_at, last_used_at
            FROM api_keys
            WHERE user_id = $1
            ORDER BY created_at DESC
            """,
            user_id
        )
        
        return [ApiKey.from_dict(dict(row)) for row in rows]


async def delete_api_key(api_key_id: UUID, user_id: UUID) -> bool:
    """
    Elimina una API key verificando que pertenezca al usuario.
    
    Args:
        api_key_id: UUID de la API key a eliminar
        user_id: UUID del usuario (para verificar ownership)
        
    Returns:
        True si se eliminó correctamente, False si no existe o no pertenece al usuario
    """
    pool = get_db_pool()
    async with pool.acquire() as conn:
        # Verificar ownership y eliminar
        result = await conn.execute(
            """
            DELETE FROM api_keys
            WHERE id = $1 AND user_id = $2
            """,
            api_key_id, user_id
        )
        
        # result devuelve el número de filas afectadas
        return result == "DELETE 1"


async def revoke_api_key(api_key_id: UUID, user_id: UUID) -> bool:
    """Alias para delete_api_key."""
    return await delete_api_key(api_key_id, user_id)

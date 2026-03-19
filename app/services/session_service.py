from typing import Optional
from uuid import UUID

from app.config.database import get_db_pool


async def create_user_session(
    user_id: Optional[UUID],
    device_name: Optional[str],
    device_specs: Optional[str],
    action: Optional[str],
) -> None:
    """Insert a login or logout event into the user_sessions table."""
    pool = get_db_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO user_sessions (user_id, device_name, device_specs, action)
            VALUES ($1, $2, $3, $4)
            """,
            user_id,
            device_name,
            device_specs,
            action,
        )

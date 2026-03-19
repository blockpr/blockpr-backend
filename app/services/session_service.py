from typing import Optional
from uuid import UUID
from datetime import datetime, timezone
from app.config.database import get_db_pool


async def create_user_session(
    user_id: Optional[UUID],
    device_name: Optional[str],
    device_specs: Optional[str],
    is_opened: Optional[bool],
) -> None:
    """Insert a login or logout event into the user_sessions table."""
    pool = get_db_pool()
    async with pool.acquire() as conn:

        session = await conn.fetchrow(
            """
            SELECT * FROM user_sessions WHERE user_id = $1 AND device_name = $2 AND device_specs = $3	
            """,
            user_id,
            device_name,
            device_specs,
        )
        print(f"is_opened: {is_opened}")
        if session:
            date = datetime.now(timezone.utc)
            await conn.execute(
                """
                UPDATE user_sessions SET is_opened = $1, updated_at = $2 WHERE id = $3
                """,
                is_opened,
                date,
                session["id"],
            )
        else:
            await conn.execute(
                """
                INSERT INTO user_sessions (user_id, device_name, device_specs, is_opened)
                VALUES ($1, $2, $3, $4)
                """,
                user_id,
                device_name,
                device_specs,
                is_opened,
                )
import hashlib
import secrets
from datetime import datetime, timedelta
from uuid import uuid4

import bcrypt

from app.config.database import get_db_pool
from app.models.user import User
from app.utils.jwt_utils import create_access_token

REFRESH_TOKEN_EXPIRE_DAYS = int(__import__("os").getenv("REFRESH_TOKEN_EXPIRE_DAYS", "30"))


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def _hash_token(token: str) -> str:
    """SHA-256 hash used to store refresh tokens without exposing raw value."""
    return hashlib.sha256(token.encode()).hexdigest()


async def _create_refresh_token(conn, user_id) -> str:
    """Insert a new refresh token record and return the raw (unhashed) token."""
    raw_token = secrets.token_urlsafe(64)
    token_hash = _hash_token(raw_token)
    now = datetime.utcnow()
    expires_at = now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    await conn.execute(
        """
        INSERT INTO user_tokens (id, user_id, token_hash, type, expires_at, used, created_at)
        VALUES ($1, $2, $3, 'refresh', $4, false, $5)
        """,
        uuid4(), user_id, token_hash, expires_at, now,
    )
    return raw_token


# ---------------------------------------------------------------------------
# Public service functions
# ---------------------------------------------------------------------------

async def register_user(
    email: str,
    password: str,
    company_name: str,
    tax_id: str | None = None,
    contact_name: str | None = None,
    contact_phone: str | None = None,
    address: str | None = None,
    city: str | None = None,
    country: str | None = None,
) -> tuple[User, str, str]:
    """
    Create a new user account.
    Returns (user, access_token, refresh_token).
    Raises ValueError if the e-mail is already taken.
    """
    pool = get_db_pool()
    async with pool.acquire() as conn:
        existing = await conn.fetchrow(
            "SELECT id FROM users WHERE email = $1", email
        )
        if existing:
            raise ValueError("Email already registered")

        password_hash = _hash_password(password)
        now = datetime.utcnow()
        user_id = uuid4()

        row = await conn.fetchrow(
            """
            INSERT INTO users (
                id, company_name, tax_id, email, password_hash,
                contact_name, contact_phone, address, city, country,
                email_verified, is_active, created_at, updated_at
            ) VALUES (
                $1, $2, $3, $4, $5,
                $6, $7, $8, $9, $10,
                false, true, $11, $11
            ) RETURNING *
            """,
            user_id, company_name, tax_id, email, password_hash,
            contact_name, contact_phone, address, city, country, now,
        )
        user = User.from_dict(dict(row))

        access_token = create_access_token(str(user.id), user.email)
        refresh_token = await _create_refresh_token(conn, user.id)

        return user, access_token, refresh_token


async def login_user(email: str, password: str) -> tuple[User, str, str]:
    """
    Authenticate a user with e-mail + password.
    Returns (user, access_token, refresh_token).
    Raises ValueError on invalid credentials or inactive account.
    """
    pool = get_db_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM users WHERE email = $1 AND is_active = true", email
        )
        # Use constant-time comparison to prevent user-enumeration via timing
        if not row or not _verify_password(password, row["password_hash"]):
            raise ValueError("Invalid credentials")

        user = User.from_dict(dict(row))

        await conn.execute(
            "UPDATE users SET last_login_at = $1 WHERE id = $2",
            datetime.utcnow(), user.id,
        )

        access_token = create_access_token(str(user.id), user.email)
        refresh_token = await _create_refresh_token(conn, user.id)

        return user, access_token, refresh_token


async def refresh_access_token(refresh_token: str) -> tuple[str, str]:
    """
    Rotate a refresh token: mark the old one as used and issue a new pair.
    Returns (new_access_token, new_refresh_token).
    Raises ValueError if the token is invalid, expired, or already used.
    """
    token_hash = _hash_token(refresh_token)
    pool = get_db_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT ut.id, ut.user_id, u.email
            FROM user_tokens ut
            JOIN users u ON u.id = ut.user_id
            WHERE ut.token_hash = $1
              AND ut.type = 'refresh'
              AND ut.used = false
              AND ut.expires_at > now()
              AND u.is_active = true
            """,
            token_hash,
        )
        if not row:
            raise ValueError("Invalid or expired refresh token")

        # Token rotation: invalidate the consumed token
        await conn.execute(
            "UPDATE user_tokens SET used = true WHERE id = $1", row["id"]
        )

        access_token = create_access_token(str(row["user_id"]), row["email"])
        new_refresh_token = await _create_refresh_token(conn, row["user_id"])

        return access_token, new_refresh_token


async def logout_user(refresh_token: str) -> None:
    """Invalidate a refresh token so it can no longer be used."""
    token_hash = _hash_token(refresh_token)
    pool = get_db_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE user_tokens SET used = true "
            "WHERE token_hash = $1 AND type = 'refresh'",
            token_hash,
        )


async def get_user_by_id(user_id: str) -> User | None:
    """Fetch an active user by their UUID."""
    pool = get_db_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM users WHERE id = $1 AND is_active = true",
            __import__("uuid").UUID(user_id),
        )
        return User.from_dict(dict(row)) if row else None

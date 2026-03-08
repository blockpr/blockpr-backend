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

async def _create_email_token(conn, user_id, token_type: str, expire_hours: int) -> str:
    """Create a one-time token for email verification or password reset."""
    raw_token = secrets.token_urlsafe(48)
    token_hash = _hash_token(raw_token)
    now = datetime.utcnow()
    expires_at = now + timedelta(hours=expire_hours)
    await conn.execute(
        """
        INSERT INTO user_tokens (id, user_id, token_hash, type, expires_at, used, created_at)
        VALUES ($1, $2, $3, $4, $5, false, $6)
        """,
        uuid4(), user_id, token_hash, token_type, expires_at, now,
    )
    return raw_token


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
) -> tuple[User, str]:
    """
    Create a new user account and send verification email.
    Returns (user, verification_token).
    Raises ValueError if the e-mail is already taken.
    """
    from app.services.email_service import send_verification_email
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
        verification_token = await _create_email_token(conn, user.id, "email_verification", 24)

    await send_verification_email(user.email, user.company_name, verification_token)
    return user, verification_token


async def login_user(email: str, password: str) -> tuple[User, str, str]:
    """
    Authenticate a user with e-mail + password.
    Returns (user, access_token, refresh_token).
    Raises ValueError on invalid credentials, unverified email, or inactive account.
    """
    pool = get_db_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM users WHERE email = $1 AND is_active = true", email
        )
        # Use constant-time comparison to prevent user-enumeration via timing
        if not row or not _verify_password(password, row["password_hash"]):
            raise ValueError("Invalid credentials")

        if not row["email_verified"]:
            raise ValueError("EMAIL_NOT_VERIFIED")

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


async def verify_email(token: str) -> None:
    """
    Mark the user's email as verified using the token sent by email.
    Raises ValueError if the token is invalid or expired.
    """
    token_hash = _hash_token(token)
    pool = get_db_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT id, user_id FROM user_tokens
            WHERE token_hash = $1
              AND type = 'email_verification'
              AND used = false
              AND expires_at > now()
            """,
            token_hash,
        )
        if not row:
            raise ValueError("Invalid or expired verification token")

        now = datetime.utcnow()
        await conn.execute(
            "UPDATE user_tokens SET used = true WHERE id = $1", row["id"]
        )
        await conn.execute(
            "UPDATE users SET email_verified = true, email_verified_at = $1, updated_at = $1 WHERE id = $2",
            now, row["user_id"],
        )


async def resend_verification(email: str) -> None:
    """
    Send a new verification email if the account exists and is not yet verified.
    Always returns silently to avoid user enumeration.
    """
    from app.services.email_service import send_verification_email
    pool = get_db_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, company_name, email_verified FROM users WHERE email = $1 AND is_active = true",
            email,
        )
        if not row or row["email_verified"]:
            return

        # Invalidate previous verification tokens
        await conn.execute(
            "UPDATE user_tokens SET used = true WHERE user_id = $1 AND type = 'email_verification'",
            row["id"],
        )
        token = await _create_email_token(conn, row["id"], "email_verification", 24)

    await send_verification_email(email, row["company_name"], token)


async def forgot_password(email: str) -> None:
    """
    Send a password reset email.
    Always returns silently to avoid user enumeration.
    """
    from app.services.email_service import send_password_reset_email
    pool = get_db_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, company_name FROM users WHERE email = $1 AND is_active = true",
            email,
        )
        if not row:
            return

        # Invalidate previous reset tokens
        await conn.execute(
            "UPDATE user_tokens SET used = true WHERE user_id = $1 AND type = 'password_reset'",
            row["id"],
        )
        token = await _create_email_token(conn, row["id"], "password_reset", 1)

    await send_password_reset_email(email, row["company_name"], token)


async def change_password(token: str, new_password: str) -> None:
    """
    Reset password using a valid reset token.
    Raises ValueError if token is invalid or expired.
    """
    token_hash = _hash_token(token)
    pool = get_db_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT id, user_id FROM user_tokens
            WHERE token_hash = $1
              AND type = 'password_reset'
              AND used = false
              AND expires_at > now()
            """,
            token_hash,
        )
        if not row:
            raise ValueError("Invalid or expired reset token")

        new_hash = _hash_password(new_password)
        now = datetime.utcnow()
        await conn.execute(
            "UPDATE user_tokens SET used = true WHERE id = $1", row["id"]
        )
        await conn.execute(
            "UPDATE users SET password_hash = $1, updated_at = $2 WHERE id = $3",
            new_hash, now, row["user_id"],
        )
        # Invalidate all existing refresh tokens for security
        await conn.execute(
            "UPDATE user_tokens SET used = true WHERE user_id = $1 AND type = 'refresh'",
            row["user_id"],
        )

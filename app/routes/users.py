from uuid import UUID

from quart import Blueprint, jsonify, request

from app.config.database import get_db_pool
from app.utils.jwt_utils import require_auth

bp = Blueprint("users", __name__, url_prefix="/users")

@bp.route("/update-profile", methods=["POST"])
@require_auth
async def update_profile():
    data = await request.get_json(silent=True) or {}
    # Campos opcionales de perfil
    company_name = data.get("company_name")
    contact_name = data.get("contact_name")
    address = data.get("address")
    contact_phone = data.get("contact_phone")
    tax_id = data.get("tax_id")

    # Normalizar strings (trim); si no es string, se deja tal cual
    def _normalize(value):
        if isinstance(value, str):
            return value.strip()
        return value

    company_name = _normalize(company_name)
    contact_name = _normalize(contact_name)
    address = _normalize(address)
    contact_phone = _normalize(contact_phone)
    tax_id = _normalize(tax_id)

    # Si no se envía ningún campo, devolver error
    if all(
        field is None
        for field in (company_name, contact_name, address, contact_phone, tax_id)
    ):
        return jsonify({"error": "At least one field must be provided"}), 400

    user_id = UUID(request.user_id)
    pool = get_db_pool()

    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                UPDATE users
                SET
                    company_name  = COALESCE($2, company_name),
                    contact_name  = COALESCE($3, contact_name),
                    address       = COALESCE($4, address),
                    contact_phone = COALESCE($5, contact_phone),
                    tax_id        = COALESCE($6, tax_id),
                    updated_at    = NOW()
                WHERE id = $1 AND is_active = true
                RETURNING *
                """,
                user_id,
                company_name,
                contact_name,
                address,
                contact_phone,
                tax_id,
            )

        if not row:
            return jsonify({"error": "User not found"}), 404

        # Respuesta alineada con /auth/me
        return (
            jsonify(
                {
                    "id": str(row["id"]),
                    "email": row["email"],
                    "company_name": row["company_name"],
                    "tax_id": row["tax_id"],
                    "contact_name": row["contact_name"],
                    "contact_phone": row["contact_phone"],
                    "address": row["address"],
                    "city": row["city"],
                    "country": row["country"],
                    "email_verified": row["email_verified"],
                    "last_login_at": row["last_login_at"].isoformat()
                    if row["last_login_at"]
                    else None,
                    "created_at": row["created_at"].isoformat(),
                }
            ),
            200,
        )
    except Exception as exc:  # pragma: no cover - fallback genérico
        return jsonify({"error": f"Failed to update profile: {str(exc)}"}), 500
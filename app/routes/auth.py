from quart import Blueprint, jsonify, request

from app.services.auth_service import (
    login_user,
    logout_user,
    refresh_access_token,
    register_user,
)
from app.utils.jwt_utils import require_auth

bp = Blueprint("auth", __name__, url_prefix="/auth")


@bp.route("/register", methods=["POST"])
async def register():
    data = await request.get_json(silent=True) or {}

    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    company_name = data.get("company_name", "").strip()

    if not email or not password or not company_name:
        return jsonify({"error": "email, password and company_name are required"}), 400

    if len(password) < 8:
        return jsonify({"error": "Password must be at least 8 characters"}), 400

    try:
        user, access_token, refresh_token = await register_user(
            email=email,
            password=password,
            company_name=company_name,
            tax_id=data.get("tax_id"),
            contact_name=data.get("contact_name"),
            contact_phone=data.get("contact_phone"),
            address=data.get("address"),
            city=data.get("city"),
            country=data.get("country"),
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 409

    return jsonify({
        "user": {
            "id": str(user.id),
            "email": user.email,
            "company_name": user.company_name,
        },
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "Bearer",
    }), 201


@bp.route("/login", methods=["POST"])
async def login():
    data = await request.get_json(silent=True) or {}

    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({"error": "email and password are required"}), 400

    try:
        user, access_token, refresh_token = await login_user(email, password)
    except ValueError:
        return jsonify({"error": "Invalid credentials"}), 401

    return jsonify({
        "user": {
            "id": str(user.id),
            "email": user.email,
            "company_name": user.company_name,
        },
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "Bearer",
    })


@bp.route("/refresh", methods=["POST"])
async def refresh():
    data = await request.get_json(silent=True) or {}
    token = data.get("refresh_token", "")

    if not token:
        return jsonify({"error": "refresh_token is required"}), 400

    try:
        access_token, new_refresh_token = await refresh_access_token(token)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 401

    return jsonify({
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "token_type": "Bearer",
    })


@bp.route("/logout", methods=["POST"])
async def logout():
    data = await request.get_json(silent=True) or {}
    token = data.get("refresh_token", "")

    if not token:
        return jsonify({"error": "refresh_token is required"}), 400

    await logout_user(token)
    return jsonify({"message": "Logged out successfully"})


@bp.route("/me", methods=["GET"])
@require_auth
async def me():
    from app.services.auth_service import get_user_by_id
    user = await get_user_by_id(request.user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify({
        "id": str(user.id),
        "email": user.email,
        "company_name": user.company_name,
        "tax_id": user.tax_id,
        "contact_name": user.contact_name,
        "contact_phone": user.contact_phone,
        "address": user.address,
        "city": user.city,
        "country": user.country,
        "email_verified": user.email_verified,
        "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
        "created_at": user.created_at.isoformat(),
    })

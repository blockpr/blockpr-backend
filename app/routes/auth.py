from quart import Blueprint, jsonify, request, current_app
from quart.wrappers.response import Response
from quart.utils import run_sync

from uuid import UUID

from app.services.api_key_service import (
    delete_api_key,
    generate_api_key,
    list_user_api_keys,
)
from app.services.auth_service import (
    change_password,
    forgot_password,
    login_user,
    logout_user,
    refresh_access_token,
    register_user,
    resend_verification,
    verify_email,
)
from app.services.session_service import create_user_session
from app.utils.jwt_utils import require_auth, decode_access_token

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
        user, verification_token = await register_user(
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
        "message": "Account created. Please verify your email before logging in.",
        "user": {
            "id": str(user.id),
            "email": user.email,
            "company_name": user.company_name,
        },
    }), 201


@bp.route("/login", methods=["POST"])
async def login():
    data = await request.get_json(silent=True) or {}

    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    device_name = data.get("device_name")
    device_specs = data.get("device_specs")
    action = data.get("action", "login")
    if not email or not password:
        return jsonify({"error": "email and password are required"}), 400

    try:
        user, access_token, refresh_token = await login_user(email, password)
    except ValueError as exc:
        if str(exc) == "EMAIL_NOT_VERIFIED":
            return jsonify({"error": "Please verify your email before logging in."}), 403
        return jsonify({"error": "Invalid credentials"}), 401

    try:
        await create_user_session(user.id, device_name, device_specs, action)
    except Exception as exc:
        print(f"Error creating user session: {exc}")
        return jsonify({"error": "Failed to create user session"}), 500

    # Create response with user data
    response: Response = await run_sync(jsonify)({
        "message": "Login exitoso",
        "user": {
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
        },
    })

    # Set cookie with access token
    is_secure = not current_app.config.get('DEBUG', False)
    response.set_cookie(
        "token",
        access_token,
        httponly=True,
        samesite="Lax",
        secure=is_secure,
        path="/",
        max_age=60 * 60 * 24 * 14  # 14 days
    )
    return response


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
    """Logout user and clear cookie"""
    # Try to get refresh_token from body (for API clients)
    data = await request.get_json(silent=True) or {}
    refresh_token = data.get("refresh_token", "")
    device_name = data.get("device_name")
    device_specs = data.get("device_specs")
    action = data.get("action", "logout")

    if refresh_token:
        await logout_user(refresh_token)

    try:
        token_cookie = request.cookies.get("token")
        if token_cookie:
            payload = decode_access_token(token_cookie)
            if payload:
                await create_user_session(payload["sub"], device_name, device_specs, action)
    except Exception:
        pass

    # Clear cookie
    response: Response = await run_sync(jsonify)({"message": "Logged out successfully"})
    # Usar delete_cookie para asegurarnos de que el navegador invalida la cookie
    response.delete_cookie("token", path="/")
    return response


@bp.route("/verify-email", methods=["POST"])
async def verify_email_route():
    data = await request.get_json(silent=True) or {}
    token = data.get("token", "")

    if not token:
        return jsonify({"error": "token is required"}), 400

    try:
        await verify_email(token)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify({"message": "Email verified successfully. You can now log in."})


@bp.route("/resend-verification", methods=["POST"])
async def resend_verification_route():
    data = await request.get_json(silent=True) or {}
    email = data.get("email", "").strip().lower()

    if not email:
        return jsonify({"error": "email is required"}), 400

    await resend_verification(email)
    return jsonify({"message": "If the account exists and is unverified, a new email has been sent."})


@bp.route("/forgot-password", methods=["POST"])
async def forgot_password_route():
    data = await request.get_json(silent=True) or {}
    email = data.get("email", "").strip().lower()

    if not email:
        return jsonify({"error": "email is required"}), 400

    await forgot_password(email)
    return jsonify({"message": "If an account with that email exists, a reset link has been sent."})


@bp.route("/change-password", methods=["POST"])
async def change_password_route():
    data = await request.get_json(silent=True) or {}
    token = data.get("token", "")
    new_password = data.get("new_password", "")

    if not token or not new_password:
        return jsonify({"error": "token and new_password are required"}), 400

    if len(new_password) < 8:
        return jsonify({"error": "Password must be at least 8 characters"}), 400

    try:
        await change_password(token, new_password)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify({"message": "Password changed successfully. Please log in again."})


@bp.route("/me", methods=["GET"])
@require_auth
async def me():
    """Get current user from cookie or Bearer token"""
    from app.services.auth_service import get_user_by_id

    user_id = request.user_id
    user = await get_user_by_id(user_id)
    if not user:
        return jsonify({"error": "Usuario no encontrado"}), 404
    
    return jsonify({
        "user": {
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
        }
    })


@bp.route("/api-keys", methods=["POST"])
@require_auth
async def create_api_key():
    """Generar una nueva API key para el usuario autenticado."""
    data = await request.get_json() or {}
    name = data.get("name")
    
    # Debug: log el name recibido
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Received data: {data}")
    logger.info(f"Received name: {repr(name)}, type: {type(name)}")
    
    # Validar y limpiar el nombre
    if name is not None:
        if isinstance(name, str):
            name = name.strip()
            # Si después de strip queda vacío, convertir a None
            if not name:
                name = None
        else:
            # Si no es string, convertir a None
            name = None
    
    logger.info(f"Processed name: {repr(name)}, type: {type(name)}")
    
    try:
        user_id = UUID(request.user_id)
        api_key, api_key_obj = await generate_api_key(user_id, name)
        
        logger.info(f"Created API key with name: {repr(api_key_obj.name)}")
        
        return jsonify({
            "api_key": api_key,  # Solo se muestra una vez
            "id": str(api_key_obj.id),
            "name": api_key_obj.name,
            "created_at": api_key_obj.created_at.isoformat(),
        }), 201
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        logger.error(f"Error creating API key: {str(exc)}", exc_info=True)
        return jsonify({"error": f"Failed to create API key: {str(exc)}"}), 500


@bp.route("/api-keys", methods=["GET"])
@require_auth
async def list_api_keys():
    """Listar todas las API keys del usuario autenticado."""
    try:
        user_id = UUID(request.user_id)
        api_keys = await list_user_api_keys(user_id)
        
        return jsonify([
            {
                "id": str(ak.id),
                "name": ak.name,
                "created_at": ak.created_at.isoformat(),
                "last_used_at": ak.last_used_at.isoformat() if ak.last_used_at else None,
            }
            for ak in api_keys
        ])
    except Exception as exc:
        return jsonify({"error": f"Failed to list API keys: {str(exc)}"}), 500


@bp.route("/api-keys/<api_key_id>", methods=["DELETE"])
@require_auth
async def delete_api_key_route(api_key_id: str):
    """Eliminar una API key del usuario autenticado."""
    try:
        user_id = UUID(request.user_id)
        api_key_uuid = UUID(api_key_id)
        
        deleted = await delete_api_key(api_key_uuid, user_id)
        
        if not deleted:
            return jsonify({"error": "API key not found or does not belong to user"}), 404
        
        return jsonify({"message": "API key deleted successfully"})
    except ValueError as exc:
        return jsonify({"error": f"Invalid UUID: {str(exc)}"}), 400
    except Exception as exc:
        return jsonify({"error": f"Failed to delete API key: {str(exc)}"}), 500

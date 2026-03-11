from functools import wraps

from quart import jsonify, request

from app.services.api_key_service import validate_api_key


def require_api_key(f):
    """
    Decorator que requiere una API key válida en el header.
    
    La API key puede venir en:
    - Header 'X-API-Key': bpk_...
    - Header 'Authorization': Bearer bpk_...
    
    Si la key es válida, establece:
    - request.user_id: UUID del usuario
    - request.api_key_id: UUID de la API key
    
    Retorna 401 si la key es inválida o falta.
    """
    @wraps(f)
    async def decorated(*args, **kwargs):
        api_key = None
        
        # Buscar en X-API-Key header
        if "X-API-Key" in request.headers:
            api_key = request.headers["X-API-Key"]
        # O buscar en Authorization header
        elif "Authorization" in request.headers:
            auth_header = request.headers["Authorization"]
            if auth_header.startswith("Bearer "):
                api_key = auth_header[7:]
            else:
                api_key = auth_header
        
        if not api_key:
            return jsonify({"error": "Missing API key. Provide X-API-Key header or Authorization: Bearer <key>"}), 401
        
        # Validar la API key
        result = await validate_api_key(api_key)
        if not result:
            return jsonify({"error": "Invalid API key"}), 401
        
        user_id, api_key_id = result
        
        # Establecer en el request para uso en el endpoint
        request.user_id = str(user_id)
        request.api_key_id = str(api_key_id)
        
        return await f(*args, **kwargs)
    
    return decorated

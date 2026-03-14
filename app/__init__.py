from quart import Quart
from quart_cors import cors
from app.config.database import init_db, close_db
from app.routes import register_routes
import os


def create_app():
    """Create and configure the Quart application"""
    # Crear app con configuración inicial para evitar KeyError
    # El problema es que Quart accede a config durante __init__
    app = Quart(
        __name__,
        static_folder=None,  # Deshabilitar static files para evitar el error
        static_url_path=None
    )
    
    # Establecer configuración necesaria
    app.config["PROVIDE_AUTOMATIC_OPTIONS"] = True
    
    # Configurar CORS para permitir credenciales
    # Cuando usas credentials: 'include', no puedes usar allow_origin="*"
    # Necesitas especificar el origen o usar allow_credentials=True
    allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:3001").split(",")
    
    app = cors(
        app,
        allow_origin=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        allow_headers=["Content-Type", "Authorization", "X-API-Key"],
    )
    
    # Register routes
    register_routes(app)
    
    # Database lifecycle
    @app.before_serving
    async def startup():
        await init_db()
    
    @app.after_serving
    async def shutdown():
        await close_db()
    
    return app

from quart import Quart
from quart_cors import cors
from app.config.database import init_db, close_db
from app.routes import register_routes


def create_app():
    """Create and configure the Quart application"""
    app = Quart(__name__)
    app = cors(app, allow_origin="*")
    
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

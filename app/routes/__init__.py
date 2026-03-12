from app.routes import auth, health, hashes, public_api
from app.routes import users

def register_routes(app):
    """Register all routes with the application"""
    app.register_blueprint(health.bp)
    app.register_blueprint(hashes.bp)
    app.register_blueprint(auth.bp)
    app.register_blueprint(public_api.bp)
    app.register_blueprint(users.bp)
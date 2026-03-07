from app.routes import auth, health


def register_routes(app):
    """Register all routes with the application"""
    app.register_blueprint(health.bp)
    app.register_blueprint(auth.bp)

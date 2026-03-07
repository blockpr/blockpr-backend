from app.routes import health


def register_routes(app):
    """Register all routes with the application"""
    app.register_blueprint(health.bp)

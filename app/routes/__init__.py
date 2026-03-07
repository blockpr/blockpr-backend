from app.routes import health, hash_test


def register_routes(app):
    """Register all routes with the application"""
    app.register_blueprint(health.bp)
    app.register_blueprint(hash_test.bp)
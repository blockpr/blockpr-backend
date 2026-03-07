from quart import Blueprint

bp = Blueprint("health", __name__)


@bp.route("/health")
async def health():
    """Health check endpoint"""
    return {"status": "ok", "message": "API is running"}

from quart import Blueprint, jsonify

health_bp = Blueprint('health', __name__)


@health_bp.route("/health", methods=["GET"])
async def health():
    """Health check endpoint for ALB and Docker"""
    return jsonify({
        "status": "healthy",
        "service": "ml-server",
        "port": 5001
    })


@health_bp.route("/ping", methods=["GET"])
async def ping():
    """Simple ping endpoint"""
    return jsonify({"message": "Hi from YouWoAI"})

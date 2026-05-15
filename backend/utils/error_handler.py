"""
Global HTTP error handlers — consistent JSON envelope: {success, error}.
"""
from flask import jsonify


def register_error_handlers(app):

    @app.errorhandler(400)
    def bad_request(e):
        return jsonify({"success": False, "error": str(e.description)}), 400

    @app.errorhandler(401)
    def unauthorized(e):
        return jsonify({"success": False, "error": "Authentication required."}), 401

    @app.errorhandler(403)
    def forbidden(e):
        return jsonify({"success": False, "error": "You do not have permission to perform this action."}), 403

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"success": False, "error": "The requested resource was not found."}), 404

    @app.errorhandler(405)
    def method_not_allowed(e):
        return jsonify({"success": False, "error": "HTTP method not allowed."}), 405

    @app.errorhandler(409)
    def conflict(e):
        return jsonify({"success": False, "error": str(e.description)}), 409

    @app.errorhandler(422)
    def unprocessable(e):
        return jsonify({"success": False, "error": str(e.description)}), 422

    @app.errorhandler(429)
    def too_many_requests(e):
        return jsonify({"success": False, "error": "Too many requests. Please slow down."}), 429

    @app.errorhandler(500)
    def internal_error(e):
        app.logger.error(f"Internal Server Error: {e}", exc_info=True)
        return jsonify({"success": False, "error": "An internal server error occurred."}), 500


def success_response(data=None, message=None, status=200, **kwargs):
    """Helper to build consistent success response."""
    resp = {"success": True}
    if message:
        resp["message"] = message
    if data is not None:
        resp["data"] = data
    resp.update(kwargs)
    return jsonify(resp), status


def error_response(message: str, status: int = 400):
    """Helper to build consistent error response."""
    return jsonify({"success": False, "error": message}), status


def paginated_response(items: list, page: int, per_page: int, total: int):
    return jsonify({
        "success": True,
        "data": items,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "pages": (total + per_page - 1) // per_page,
        }
    })

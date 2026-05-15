import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

from extensions import db, jwt, socketio
from utils.logger import setup_logger
from utils.error_handler import register_error_handlers

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend")

JWT_SECRET = "SW-2026-XkQ9mPvLr3nYtUwAeJhBdCzFgNsKoIqRx"

def create_app():
    app = Flask(__name__, static_folder=None)

    from dotenv import load_dotenv
    load_dotenv()

    db_user = os.getenv("DB_USER", "root")
    db_pass = os.getenv("DB_PASSWORD", "")
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "3306")
    db_name = os.getenv("DB_NAME", "smart_warehouse")

    app.config["SQLALCHEMY_DATABASE_URI"] = (
        f"mysql+pymysql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}?charset=utf8mb4"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SQLALCHEMY_POOL_RECYCLE"]        = 280
    app.config["SQLALCHEMY_POOL_PRE_PING"]       = True

    app.config["JWT_SECRET_KEY"]            = JWT_SECRET
    app.config["JWT_ACCESS_TOKEN_EXPIRES"]  = 3600
    app.config["JWT_REFRESH_TOKEN_EXPIRES"] = 604800
    app.config["JWT_TOKEN_LOCATION"]        = ["headers"]
    app.config["JWT_HEADER_NAME"]           = "Authorization"
    app.config["JWT_HEADER_TYPE"]           = "Bearer"
    app.config["JWT_DECODE_ALGORITHMS"]     = ["HS256"]

    app.config["MAX_FAILED_LOGINS"] = 5
    app.config["LOCKOUT_MINUTES"]   = 15
    app.config["BCRYPT_ROUNDS"]     = 4

    log_dir     = os.getenv("LOG_DIR", "logs")
    reports_dir = os.getenv("REPORTS_DIR", "reports")
    app.config["LOG_DIR"]       = log_dir
    app.config["REPORTS_DIR"]   = reports_dir
    app.config["LOG_MAX_BYTES"] = 10 * 1024 * 1024
    app.config["LOG_BACKUPS"]   = 5
    app.config["DEBUG"]         = True

    db.init_app(app)
    jwt.init_app(app)

    CORS(app, resources={r"/api/*": {"origins": "*"}},
         allow_headers=["Content-Type", "Authorization"],
         methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
         supports_credentials=False)

    @app.after_request
    def add_cors(response):
        response.headers["Access-Control-Allow-Origin"]  = "*"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
        return response

    @app.before_request
    def handle_options():
        if request.method == "OPTIONS":
            r = jsonify({})
            r.headers["Access-Control-Allow-Origin"]  = "*"
            r.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
            r.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
            return r, 200

    socketio.init_app(app, cors_allowed_origins="*", logger=False, engineio_logger=False)

    os.makedirs(log_dir,     exist_ok=True)
    os.makedirs(reports_dir, exist_ok=True)
    setup_logger(app, app.config)

    @jwt.token_in_blocklist_loader
    def check_revoked(jwt_header, jwt_payload):
        from models import TokenBlocklist
        jti = jwt_payload["jti"]; return db.session.get(TokenBlocklist, jti) is not None

    @jwt.revoked_token_loader
    def revoked_cb(h, p):
        return {"success": False, "error": "Token revoked."}, 401

    @jwt.expired_token_loader
    def expired_cb(h, p):
        return {"success": False, "error": "Token expired."}, 401

    @jwt.invalid_token_loader
    def invalid_cb(e):
        return {"success": False, "error": f"Invalid token: {e}"}, 422

    @jwt.unauthorized_loader
    def missing_cb(e):
        return {"success": False, "error": "Authorization token required."}, 401

    from routes.auth          import auth_bp
    from routes.users         import users_bp
    from routes.products      import products_bp
    from routes.inventory     import inventory_bp
    from routes.orders        import orders_bp
    from routes.shipments     import shipments_bp
    from routes.suppliers     import suppliers_bp
    from routes.warehouses    import warehouses_bp
    from routes.reports       import reports_bp
    from routes.notifications import notifications_bp

    app.register_blueprint(auth_bp,          url_prefix="/api/auth")
    app.register_blueprint(users_bp,         url_prefix="/api/users")
    app.register_blueprint(products_bp,      url_prefix="/api/products")
    app.register_blueprint(inventory_bp,     url_prefix="/api/inventory")
    app.register_blueprint(orders_bp,        url_prefix="/api/orders")
    app.register_blueprint(shipments_bp,     url_prefix="/api/shipments")
    app.register_blueprint(suppliers_bp,     url_prefix="/api/suppliers")
    app.register_blueprint(warehouses_bp,    url_prefix="/api/warehouses")
    app.register_blueprint(reports_bp,       url_prefix="/api/reports")
    app.register_blueprint(notifications_bp, url_prefix="/api/notifications")

    from routes.uploads import uploads_bp
    app.register_blueprint(uploads_bp, url_prefix="/api/upload")

    register_error_handlers(app)

    @app.get("/api/health")
    def health():
        return {"success": True, "message": "Smart Warehouse API running.",
                "jwt_key_length": len(JWT_SECRET)}

    IMAGES_DIR = os.path.join(FRONTEND_DIR, "images")

    @app.route("/images/<path:filename>")
    def serve_image(filename):
        return send_from_directory(IMAGES_DIR, filename)

    @app.route("/")
    def index():
        return send_from_directory(FRONTEND_DIR, "login.html")

    @app.route("/<path:filename>")
    def serve_frontend(filename):
        if filename.startswith("api/"):
            return jsonify({"success": False, "error": "Not found"}), 404
        try:
            return send_from_directory(FRONTEND_DIR, filename)
        except Exception:
            return send_from_directory(FRONTEND_DIR, "login.html")

    return app

if __name__ == "__main__":
    application = create_app()
    socketio.run(application, host="0.0.0.0", port=5000,
                 debug=True, use_reloader=False)

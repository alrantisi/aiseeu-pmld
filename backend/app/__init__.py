from urllib.parse import urlsplit

from flask import Flask, jsonify, request, session

from .config import Config
from .extensions import db


def create_app():
    app = Flask(__name__)

    app.config.from_object(Config)

    @app.before_request
    def require_login_for_api():
        path = request.path
        if request.method == "OPTIONS" or not path.startswith("/api/"):
            return None
        if path.startswith("/api/auth/"):
            return None
        if path.startswith("/api/cameras/") and path.endswith("/feed"):
            return None
        if "user_id" not in session:
            return jsonify({"status": "error", "message": "Anda harus login terlebih dahulu"}), 401
        return None

    @app.after_request
    def add_local_frontend_cors(response):
        origin = request.headers.get("Origin")
        is_local_origin = origin == "null"
        if origin and origin != "null":
            parsed_origin = urlsplit(origin)
            is_local_origin = (
                parsed_origin.scheme == "http"
                and parsed_origin.hostname in {"localhost", "127.0.0.1"}
            )

        if is_local_origin:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type"
            response.headers.add("Vary", "Origin")

        return response

    db.init_app(app)

    from .routes.camera_routes import camera_bp
    from .routes.roi_routes import roi_bp
    from app.routes.auth import auth_bp
    from app.routes.log_routes import log_bp

    app.register_blueprint(camera_bp)
    app.register_blueprint(roi_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(log_bp)

    @app.get("/")
    def home():
        return {
            "status": "success",
            "message": "Vehicle Detection Backend is running"
        }

    return app
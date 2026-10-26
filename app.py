"""
StockTrade Application Factory (app.py)
Flask 3 with Blueprints, Server-Side Sessions, CSRF, Rate-Limiting, and Security Headers.
"""
import os
from datetime import datetime
from flask import Flask, request, jsonify, render_template, redirect, url_for, session, send_from_directory, abort
from flask_login import LoginManager, current_user
from flask_wtf.csrf import CSRFProtect, generate_csrf
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from config import config_by_name, Config
from models.db import init_db_engines
from models.user import User
from repositories.user_repo import UserRepository
from utils.formatters import format_inr, format_pct, format_qty

# Extensions
login_manager = LoginManager()
csrf = CSRFProtect()
limiter = Limiter(key_func=get_remote_address)

@login_manager.user_loader
def load_user(user_id: str) -> User | None:
    """Flask-Login user loader callback."""
    if not user_id or not user_id.isdigit():
        return None
    user_dict = UserRepository.get_by_id(int(user_id))
    if not user_dict:
        return None
    return User(user_dict)

def create_app(config_name: str = "default") -> Flask:
    """Application factory for StockTrade."""
    app = Flask(__name__)
    
    # Load configuration
    cfg_class = config_by_name.get(config_name, config_by_name["default"])
    app.config.from_object(cfg_class)
    # Ensure environment variables take precedence over cached class defaults
    if os.getenv("SECRET_KEY"):
        app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")

    # Enforce strict secret key requirement in production
    if config_name == "production" or os.getenv("FLASK_ENV") == "production":
        secret = app.config.get("SECRET_KEY", "")
        known_placeholders = {
            "stocktrade-insecure-default-change-me-immediately-32b",
            "stocktrade-secure-random-session-secret-key-32bytes-min",
            "change-me",
            "secret",
            "default"
        }
        if not secret or secret in known_placeholders or "insecure-default" in secret or len(secret) < 32:
            raise ValueError(
                "CRITICAL SECURITY CONFIGURATION ERROR: SECRET_KEY must be explicitly set "
                "in production environment to a unique cryptographically secure random string (minimum 32 bytes). "
                "Generate one via: python -c 'import secrets; print(secrets.token_hex(32))'"
            )

    # Initialize database connection pools
    init_db_engines(app.config)

    # Initialize extensions
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please sign in to access this page."
    login_manager.login_message_category = "info"

    csrf.init_app(app)
    limiter.init_app(app)

    # Register Jinja custom filters
    app.jinja_env.filters["inr"] = format_inr
    app.jinja_env.filters["pct"] = format_pct
    app.jinja_env.filters["qty"] = format_qty

    # Register context processors
    @app.context_processor
    def inject_globals():
        return {
            "current_time": datetime.now().strftime("%H:%M:%S"),
            "current_year": datetime.now().year,
            "csrf_token": generate_csrf
        }

    # Security headers middleware
    @app.after_request
    def set_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        # Pass CSRF token in header for AJAX client ease
        response.headers["X-CSRFToken"] = generate_csrf()
        return response

    # Unified Error Handlers
    def handle_error(code: int, message: str, exc: Exception = None):
        is_api = request.path.startswith("/api/") or request.headers.get("Accept") == "application/json"
        if is_api:
            return jsonify({
                "ok": False,
                "error": {
                    "code": f"HTTP_{code}",
                    "message": message,
                    "details": str(exc) if app.debug else None
                }
            }), code
        try:
            return render_template(f"errors/{code}.html", error_message=message), code
        except Exception:
            return render_template("errors/500.html", error_message=message), code

    @app.errorhandler(400)
    def bad_request(e):
        return handle_error(400, "Bad Request: Invalid parameters provided.", e)

    @app.errorhandler(401)
    def unauthorized(e):
        return handle_error(401, "Authentication required to access this resource.", e)

    @app.errorhandler(403)
    def forbidden(e):
        return handle_error(403, "Access Forbidden: You do not possess the required permissions.", e)

    @app.errorhandler(404)
    def not_found(e):
        return handle_error(404, "Requested resource not found.", e)

    @app.errorhandler(409)
    def conflict(e):
        return handle_error(409, "Conflict: Price moved or request state conflict.", e)

    @app.errorhandler(422)
    def unprocessable(e):
        return handle_error(422, "Unprocessable Entity: Validation error.", e)

    @app.errorhandler(429)
    def rate_limit(e):
        return handle_error(429, "Too Many Requests: Rate limit exceeded. Please slow down.", e)

    @app.errorhandler(500)
    def server_error(e):
        return handle_error(500, "Internal Server Error: An unexpected error occurred.", e)

    # Register Blueprints
    from routes.auth import auth_bp
    from routes.market import market_bp
    from routes.investor import investor_bp
    from routes.broker import broker_bp
    from routes.admin import admin_bp
    from routes.ai import ai_bp
    from routes.reports import reports_bp

    app.register_blueprint(auth_bp)
    csrf.exempt(auth_bp)
    app.register_blueprint(market_bp)
    app.register_blueprint(investor_bp)
    app.register_blueprint(broker_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(ai_bp)
    app.register_blueprint(reports_bp)

    # React SPA Static Assets & Index
    dist_dir = os.path.join(app.root_path, "static", "dist")

    @app.route("/favicon.ico")
    def favicon():
        return "", 204

    @app.route("/assets/<path:filename>")
    def serve_assets(filename):
        return send_from_directory(os.path.join(dist_dir, "assets"), filename)

    # Root index route
    @app.route("/", strict_slashes=False)
    @app.route("/app", strict_slashes=False)
    def index():
        index_file = os.path.join(dist_dir, "index.html")
        if os.path.exists(index_file):
            return send_from_directory(dist_dir, "index.html")
        if current_user.is_authenticated:
            if current_user.role == "ADMIN":
                return redirect(url_for("admin.overview"))
            elif current_user.role == "BROKER":
                return redirect(url_for("broker.clients"))
            else:
                return redirect(url_for("investor.dashboard"))
        return redirect(url_for("auth.login"))

    # Health check endpoint
    @app.route("/health")
    def health():
        return jsonify({
            "status": "healthy",
            "system": "StockTrade Simulated Platform",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }), 200

    return app

if __name__ == "__main__":
    from services.market_simulator import MarketSimulator
    app = create_app(os.getenv("FLASK_ENV", "development"))
    # Start market simulator background worker
    sim = MarketSimulator.get_instance()
    sim.start()
    port = int(os.getenv("PORT", 5000))
    print(f"\n[StockTrade] Platform ready at http://127.0.0.1:{port}")
    app.run(host="127.0.0.1", port=port, debug=False)


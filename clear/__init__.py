"""Application factory. No server or database is created at import time."""
import os
import secrets
from pathlib import Path

from flask import Flask, jsonify, request, session
from werkzeug.exceptions import HTTPException


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        MAX_CONTENT_LENGTH=2 * 1024 * 1024,
        MAX_FORM_MEMORY_SIZE=2 * 1024 * 1024,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("CLEAR_HTTPS") == "1",
        DATABASE=str(Path(app.instance_path) / "clear.sqlite3"),
    )
    if test_config:
        app.config.update(test_config)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    if not app.config.get("SECRET_KEY"):
        secret_path = Path(app.instance_path) / ".secret"
        if not secret_path.exists():
            try:
                with secret_path.open("x") as handle:
                    handle.write(secrets.token_hex(32))
            except FileExistsError:
                pass
        app.config["SECRET_KEY"] = os.environ.get("CLEAR_SECRET_KEY") or secret_path.read_text()

    from . import repository
    from .routes import bp
    from . import i18n
    repository.init_app(app)
    i18n.init_app(app)
    app.register_blueprint(bp)

    @app.before_request
    def protect_mutations():
        if "owner" not in session:
            session["owner"] = secrets.token_hex(24)
            session["csrf"] = secrets.token_hex(24)
        if request.method in {"POST", "PUT", "DELETE", "PATCH"}:
            token = request.headers.get("X-CSRF-Token", "")
            if not secrets.compare_digest(token, session["csrf"]):
                return jsonify(error="This session has changed. Refresh the page and try again."), 403

    @app.after_request
    def security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; font-src 'self'; connect-src 'self'; "
            "frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        )
        if not request.path.startswith("/static/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.errorhandler(HTTPException)
    def http_error(error):
        message = "File too large. The complete upload must be under 2 MB." if error.code == 413 else error.description
        return jsonify(error=message), error.code

    @app.errorhandler(Exception)
    def unexpected_error(error):
        app.logger.exception("Unexpected request failure")
        return jsonify(error="Something went wrong. Your active dataset has not been replaced. Please retry."), 500

    return app

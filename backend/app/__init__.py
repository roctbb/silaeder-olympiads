from urllib.parse import urlsplit

from flask import Flask, jsonify
from flask_cors import CORS
from redis.exceptions import RedisError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from .config import Config
from .extensions import db, migrate, oauth, server_session


def _credentialed_cors_origins(values: list[str]) -> list[str]:
    origins = []
    local_hosts = {"localhost", "127.0.0.1", "::1"}
    for value in values:
        try:
            parsed = urlsplit(value)
            _ = parsed.port
        except ValueError as exc:
            raise RuntimeError("CORS_ORIGINS содержит некорректный origin") from exc
        if (
            "*" in value
            or "\\" in value
            or any(character.isspace() for character in value)
            or parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or (parsed.scheme == "http" and parsed.hostname not in local_hosts)
            or parsed.username is not None
            or parsed.password is not None
            or parsed.path not in {"", "/"}
            or parsed.query
            or parsed.fragment
        ):
            raise RuntimeError(
                "CORS с credentials требует явных HTTPS origins без путей "
                "(HTTP разрешён только локально)"
            )
        origins.append(value.rstrip("/"))
    return origins


def _secure_service_url(value: str, setting_name: str) -> None:
    try:
        parsed = urlsplit(value)
        _ = parsed.port
    except ValueError as exc:
        raise RuntimeError(f"{setting_name} содержит некорректный URL") from exc
    local_hosts = {"localhost", "127.0.0.1", "::1"}
    if (
        not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or "\\" in value
        or any(character.isspace() for character in value)
        or (
            parsed.scheme != "https"
            and not (parsed.scheme == "http" and parsed.hostname in local_hosts)
        )
    ):
        raise RuntimeError(
            f"{setting_name} должен быть HTTPS URL (HTTP разрешён только локально)"
        )


def create_app(config_object: type[Config] | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_object or Config)

    secret = app.config.get("SECRET_KEY")
    if (
        not app.config.get("TESTING")
        and not app.config.get("ALLOW_INSECURE_DEV_SECRET")
        and (not isinstance(secret, (str, bytes)) or len(secret) < 32)
    ):
        raise RuntimeError(
            "SECRET_KEY должен содержать не менее 32 символов; "
            "dev-fallback разрешается только через ALLOW_INSECURE_DEV_SECRET=true"
        )

    cors_origins = _credentialed_cors_origins(app.config["CORS_ORIGINS"])
    _secure_service_url(app.config["CRM_OIDC_ISSUER"], "CRM_OIDC_ISSUER")
    _secure_service_url(app.config["CRM_NOTIFICATION_URL"], "CRM_NOTIFICATION_URL")

    db.init_app(app)
    migrate.init_app(app, db)
    server_session.init_app(app)
    oauth.init_app(app)
    oauth.register(
        name="crm",
        client_id=app.config["CRM_OIDC_CLIENT_ID"],
        client_secret=app.config["CRM_OIDC_CLIENT_SECRET"],
        server_metadata_url=(
            f'{app.config["CRM_OIDC_ISSUER"]}/.well-known/openid-configuration'
        ),
        client_kwargs={
            "scope": app.config["CRM_OIDC_SCOPES"],
            "code_challenge_method": "S256",
        },
    )
    CORS(
        app,
        resources={r"/api/*": {"origins": cors_origins}},
        supports_credentials=True,
    )

    from . import models  # noqa: F401
    from .api.admin import admin_bp
    from .api.personal import personal_bp
    from .api.public import public_bp
    from .auth import auth_bp
    from .cli import register_commands

    app.register_blueprint(public_bp, url_prefix="/api/v1")
    app.register_blueprint(personal_bp, url_prefix="/api/v1")
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp, url_prefix="/api/admin")
    register_commands(app)

    @app.get("/api/live")
    def live():
        return jsonify(status="ok")

    @app.get("/api/health")
    def health():
        checks = {"database": "ok", "redis": "ok"}
        try:
            db.session.execute(text("SELECT 1"))
        except SQLAlchemyError:
            try:
                db.session.rollback()
            except SQLAlchemyError:
                pass
            checks["database"] = "error"

        redis_client = app.config.get("SESSION_REDIS")
        if redis_client is not None:
            try:
                redis_client.ping()
            except RedisError:
                checks["redis"] = "error"

        if "error" in checks.values():
            return jsonify(status="unavailable", checks=checks), 503
        return jsonify(status="ok")

    return app

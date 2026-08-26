from __future__ import annotations

import secrets
from datetime import UTC, datetime
from functools import wraps
from urllib.parse import urlsplit

from authlib.integrations.base_client.errors import OAuthError
from flask import Blueprint, current_app, g, jsonify, redirect, request, session
from requests import RequestException
from sqlalchemy import select

from .extensions import db, oauth
from .models import User

auth_bp = Blueprint("auth", __name__)


def _oidc_is_configured() -> bool:
    return bool(
        current_app.config.get("CRM_OIDC_CLIENT_ID")
        and current_app.config.get("CRM_OIDC_CLIENT_SECRET")
    )


def _crm_client():
    return oauth.create_client("crm")


def _backend_url(path: str) -> str:
    return f'{current_app.config["APP_BASE_URL"]}{path}'


def _safe_next(value: str | None) -> str:
    candidate = (value or "/").strip()
    parsed = urlsplit(candidate)
    if (
        not candidate.startswith("/")
        or candidate.startswith("//")
        or parsed.scheme
        or parsed.netloc
        or "\\" in candidate
        or any(ord(character) < 32 or ord(character) == 127 for character in candidate)
    ):
        return "/"
    return candidate


def _frontend_url(path: str = "/") -> str:
    return f'{current_app.config["FRONTEND_BASE_URL"]}{_safe_next(path)}'


def _origin(value: str) -> tuple[str, str, int | None] | None:
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError:
        return None
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
    ):
        return None
    return parsed.scheme, parsed.hostname.casefold(), port


def _safe_provider_logout_url(value: str | None) -> str | None:
    if not value or _origin(value) != _origin(current_app.config["CRM_OIDC_ISSUER"]):
        return None
    return value


def _rotate_session_id() -> None:
    regenerate = getattr(current_app.session_interface, "regenerate", None)
    if callable(regenerate):
        # Flask-Session only rotates a non-empty session. At this point it still
        # contains the one-time OIDC state/nonce and therefore can be regenerated.
        regenerate(session)


def _serialize_user(user: User) -> dict:
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "preferred_username": user.preferred_username,
        "role": user.crm_role,
        "object_type": user.object_type,
        "grade": user.grade,
    }


def current_user() -> User | None:
    user_id = session.get("user_id")
    if not user_id:
        return None
    cached = getattr(g, "current_user", None)
    if cached is not None and cached.id == user_id:
        return cached
    user = db.session.get(User, user_id)
    if user is None:
        session.clear()
        return None
    g.current_user = user
    return user


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if current_user() is None:
            return jsonify(error="Требуется вход через ЛК Силаэдр"), 401
        return view(*args, **kwargs)

    return wrapped


def csrf_protected(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        expected = session.get("csrf_token")
        supplied = request.headers.get("X-CSRF-Token", "")
        if not expected or not supplied or not secrets.compare_digest(expected, supplied):
            return jsonify(error="Недействительный CSRF-токен"), 403
        return view(*args, **kwargs)

    return wrapped


def _session_document(user: User | None):
    if user is None:
        return {
            "authenticated": False,
            "user": None,
            "csrf_token": None,
            "login_url": "/api/v1/auth/login",
        }
    token = session.get("csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["csrf_token"] = token
    return {
        "authenticated": True,
        "user": _serialize_user(user),
        "csrf_token": token,
        "login_url": "/api/v1/auth/login",
    }


@auth_bp.get("/api/v1/auth/session")
def auth_session():
    return jsonify(_session_document(current_user()))


@auth_bp.after_request
def disable_auth_response_caching(response):
    response.headers["Cache-Control"] = "private, no-store"
    return response


@auth_bp.get("/api/v1/auth/login")
def oidc_login():
    if not _oidc_is_configured():
        return jsonify(error="Вход через ЛК Силаэдр пока не настроен"), 503
    session["post_login_next"] = _safe_next(request.args.get("next"))
    client = _crm_client()
    if client is None:
        return jsonify(error="Вход через ЛК Силаэдр пока не настроен"), 503
    # Authlib stores and validates state, nonce and the PKCE verifier in the
    # server-side session. The registered client only permits PKCE S256.
    return client.authorize_redirect(_backend_url("/auth/crm/callback"))


def _claim(identity: dict, name: str, fallback=None):
    value = identity.get(name)
    return fallback if value in (None, "") else value


@auth_bp.get("/auth/crm/callback")
def oidc_callback():
    if not _oidc_is_configured():
        return jsonify(error="Вход через ЛК Силаэдр пока не настроен"), 503
    client = _crm_client()
    if client is None:
        return jsonify(error="Вход через ЛК Силаэдр пока не настроен"), 503
    try:
        # Authlib validates state, nonce, the authorization response, the ID
        # token signature and standard iss/aud/exp/iat claims using discovery.
        token = client.authorize_access_token()
        id_claims = dict(token.get("userinfo") or {})
        fresh_identity = dict(client.userinfo(token=token))
    except (OAuthError, RequestException, KeyError, TypeError, ValueError):
        return jsonify(error="Не удалось подтвердить вход через ЛК Силаэдр"), 400

    id_subject = id_claims.get("sub")
    subject = fresh_identity.get("sub")
    if (
        not isinstance(id_subject, str)
        or not isinstance(subject, str)
        or not subject
        or len(subject) > 255
        or id_subject != subject
    ):
        return jsonify(error="ЛК вернул несогласованные данные пользователя"), 400

    issuer = current_app.config["CRM_OIDC_ISSUER"]
    token_issuer = id_claims.get("iss")
    if not isinstance(token_issuer, str) or token_issuer != issuer:
        return jsonify(error="ЛК вернул токен другого издателя"), 400

    user = db.session.scalar(
        select(User).where(User.oidc_issuer == issuer, User.oidc_subject == subject)
    )
    if user is None:
        user = User(
            oidc_issuer=issuer,
            oidc_subject=subject,
            name="",
            last_login_at=datetime.now(UTC),
        )
        db.session.add(user)

    crm_object = fresh_identity.get("crm_object")
    if not isinstance(crm_object, dict):
        crm_object = {}
    roles = fresh_identity.get("roles")
    if not isinstance(roles, (list, tuple)):
        roles = []
    user.name = str(
        _claim(
            fresh_identity,
            "name",
            crm_object.get("name") or fresh_identity.get("preferred_username") or "Пользователь",
        )
    )[:255]
    user.preferred_username = (
        str(fresh_identity["preferred_username"])[:255]
        if fresh_identity.get("preferred_username")
        else None
    )
    user.email = str(fresh_identity["email"])[:320] if fresh_identity.get("email") else None
    user.crm_role = str(
        fresh_identity.get("role") or (roles[0] if roles else "")
    )[:80] or None
    user.object_type = (
        str(fresh_identity["object_type"])[:80]
        if fresh_identity.get("object_type")
        else None
    )
    user.last_login_at = datetime.now(UTC)
    db.session.commit()

    target = _safe_next(session.get("post_login_next"))
    id_token = token.get("id_token")
    _rotate_session_id()
    session.clear()
    session["user_id"] = user.id
    session["csrf_token"] = secrets.token_urlsafe(32)
    if isinstance(id_token, str) and id_token:
        # This stays inside the server-side session and is used only as the RP
        # logout hint; access/refresh tokens are never sent to Vue.
        session["oidc_id_token"] = id_token
    return redirect(_frontend_url(target))


@auth_bp.post("/api/v1/auth/logout")
@login_required
@csrf_protected
def oidc_logout():
    id_token = session.get("oidc_id_token")
    session.clear()
    local_target = _frontend_url("/")
    if not id_token or not _oidc_is_configured():
        return jsonify(logout_url=local_target)

    client = _crm_client()
    try:
        response = client.logout_redirect(
            post_logout_redirect_uri=_backend_url("/auth/crm/logout/callback"),
            id_token_hint=id_token,
            state=secrets.token_urlsafe(32),
        )
    except (OAuthError, RequestException, RuntimeError, TypeError, ValueError):
        return jsonify(logout_url=local_target)
    provider_url = _safe_provider_logout_url(response.headers.get("Location"))
    if provider_url is None:
        # logout_redirect stored provider state in this now-anonymous session;
        # discard it when its destination is not trusted.
        session.clear()
        return jsonify(logout_url=local_target)
    return jsonify(logout_url=provider_url)


@auth_bp.get("/auth/crm/logout/callback")
def oidc_logout_callback():
    client = _crm_client()
    try:
        if client is not None:
            client.validate_logout_response()
    except (OAuthError, RuntimeError, TypeError, ValueError):
        session.clear()
        return jsonify(error="Не удалось подтвердить выход из ЛК Силаэдр"), 400
    session.clear()
    return redirect(_frontend_url("/"))


__all__ = [
    "auth_bp",
    "csrf_protected",
    "current_user",
    "login_required",
    "_serialize_user",
]

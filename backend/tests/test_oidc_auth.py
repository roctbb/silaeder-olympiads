from urllib.parse import parse_qs, urlsplit

import pytest
from flask import redirect
from sqlalchemy import func, select

import app.auth as auth_module
from app import create_app
from app.config import TestConfig
from app.extensions import db, oauth
from app.models import User


def test_credentialed_cors_is_exact_and_rejects_wildcard(client):
    allowed = client.get(
        "/api/v1/auth/session", headers={"Origin": "http://localhost:5188"}
    )
    assert allowed.headers["Access-Control-Allow-Origin"] == "http://localhost:5188"
    assert allowed.headers["Access-Control-Allow-Credentials"] == "true"

    untrusted = client.get(
        "/api/v1/auth/session", headers={"Origin": "https://evil.test"}
    )
    assert "Access-Control-Allow-Origin" not in untrusted.headers

    class WildcardCorsConfig(TestConfig):
        CORS_ORIGINS = ["*"]

    with pytest.raises(RuntimeError, match="явных HTTP.*origins"):
        create_app(WildcardCorsConfig)

    class InsecureCorsConfig(TestConfig):
        CORS_ORIGINS = ["http://frontend.internal"]

    with pytest.raises(RuntimeError, match="HTTP разрешён только локально"):
        create_app(InsecureCorsConfig)


def test_crm_credentials_can_only_be_sent_to_secure_service_urls():
    class InsecureNotificationConfig(TestConfig):
        CRM_NOTIFICATION_URL = "http://crm.internal/api/external/notifications"

    with pytest.raises(RuntimeError, match="CRM_NOTIFICATION_URL должен быть HTTPS"):
        create_app(InsecureNotificationConfig)

    class InsecureIssuerConfig(TestConfig):
        CRM_OIDC_ISSUER = "http://crm.internal"

    with pytest.raises(RuntimeError, match="CRM_OIDC_ISSUER должен быть HTTPS"):
        create_app(InsecureIssuerConfig)


def test_production_rejects_missing_or_weak_secret_key():
    for secret in ("dev-only-change-me", "too-short"):
        class UnsafeSecretConfig(TestConfig):
            TESTING = False
            SECRET_KEY = secret
            ALLOW_INSECURE_DEV_SECRET = False

        with pytest.raises(RuntimeError, match="SECRET_KEY должен содержать"):
            create_app(UnsafeSecretConfig)


def test_login_uses_state_nonce_and_pkce_s256(app, client, monkeypatch):
    remote = oauth.create_client("crm")
    metadata = {
        "issuer": "https://lk.silaeder.ru",
        "authorization_endpoint": "https://lk.silaeder.ru/oauth/authorize",
        "token_endpoint": "https://lk.silaeder.ru/api/oauth/token",
        "userinfo_endpoint": "https://lk.silaeder.ru/api/oauth/userinfo",
        "jwks_uri": "https://lk.silaeder.ru/api/oauth/jwks",
    }
    monkeypatch.setattr(remote, "load_server_metadata", lambda: metadata)

    response = client.get("/api/v1/auth/login", query_string={"next": "/my-plan"})
    assert response.status_code == 302
    query = parse_qs(urlsplit(response.location).query)
    assert query["response_type"] == ["code"]
    assert query["scope"] == ["openid profile email roles"]
    assert len(query["state"][0]) >= 16
    assert len(query["nonce"][0]) >= 16
    assert query["code_challenge_method"] == ["S256"]
    assert query["code_challenge"][0]
    with client.session_transaction() as session:
        assert session["post_login_next"] == "/my-plan"
        oidc_state = next(key for key in session if key.startswith("_state_crm_"))
        assert session[oidc_state]["data"]["code_verifier"]
        assert session[oidc_state]["data"]["nonce"] == query["nonce"][0]

    client.get("/api/v1/auth/login", query_string={"next": "https://evil.test/"})
    with client.session_transaction() as session:
        assert session["post_login_next"] == "/"

    client.get(
        "/api/v1/auth/login",
        query_string={"next": "/my-plan\r\nLocation: https://evil.test"},
    )
    with client.session_transaction() as session:
        assert session["post_login_next"] == "/"


class FakeOidcClient:
    def __init__(
        self,
        *,
        subject="subject-1",
        userinfo_subject=None,
        name="Иван Иванов",
        issuer="https://lk.silaeder.ru",
        logout_url="https://lk.silaeder.ru/oauth/logout?state=test",
    ):
        self.subject = subject
        self.userinfo_subject = userinfo_subject or subject
        self.name = name
        self.issuer = issuer
        self.logout_url = logout_url

    def authorize_access_token(self):
        return {
            "id_token": "server-side-id-token",
            "userinfo": {"iss": self.issuer, "sub": self.subject},
        }

    def userinfo(self, token):
        assert token["id_token"] == "server-side-id-token"
        return {
            "sub": self.userinfo_subject,
            "name": self.name,
            "preferred_username": "ivan",
            "email": "ivan@example.test",
            "role": "student",
            "roles": ["student"],
            "object_type": "students",
            "crm_object": {"id": 42, "type": "students", "name": self.name},
        }

    def logout_redirect(self, **kwargs):
        assert kwargs["id_token_hint"] == "server-side-id-token"
        assert kwargs["post_logout_redirect_uri"].endswith("/auth/crm/logout/callback")
        return redirect(self.logout_url)

    def validate_logout_response(self):
        return None


def test_callback_creates_and_synchronizes_user(app, client, monkeypatch):
    fake = FakeOidcClient()
    monkeypatch.setattr(auth_module, "_crm_client", lambda: fake)
    with client.session_transaction() as session:
        session["post_login_next"] = "/my-plan"

    response = client.get("/auth/crm/callback")
    assert response.status_code == 302
    assert response.location == "http://localhost/my-plan"
    with client.session_transaction() as session:
        assert session["user_id"]
        assert session["csrf_token"]
        assert session["oidc_id_token"] == "server-side-id-token"
    with app.app_context():
        user = db.session.scalar(select(User))
        assert user.oidc_issuer == "https://lk.silaeder.ru"
        assert user.oidc_subject == "subject-1"
        assert user.name == "Иван Иванов"
        user.grade = 9
        db.session.commit()

    monkeypatch.setattr(
        auth_module, "_crm_client", lambda: FakeOidcClient(name="Иван Петров")
    )
    client.get("/auth/crm/callback")
    with app.app_context():
        assert db.session.scalar(select(func.count()).select_from(User)) == 1
        user = db.session.scalar(select(User))
        assert user.name == "Иван Петров"
        assert user.grade == 9


def test_callback_rejects_subject_mismatch(client, monkeypatch):
    monkeypatch.setattr(
        auth_module,
        "_crm_client",
        lambda: FakeOidcClient(subject="id-token-sub", userinfo_subject="other-sub"),
    )
    response = client.get("/auth/crm/callback")
    assert response.status_code == 400
    assert "несогласованные" in response.get_json()["error"]


def test_callback_requires_exact_issuer(client, monkeypatch):
    for issuer in (None, "https://lk.silaeder.ru/", "https://evil.test"):
        monkeypatch.setattr(
            auth_module,
            "_crm_client",
            lambda issuer=issuer: FakeOidcClient(issuer=issuer),
        )
        response = client.get("/auth/crm/callback")
        assert response.status_code == 400
        assert "другого издателя" in response.get_json()["error"]


def test_callback_rotates_server_side_session_identifier(client, monkeypatch):
    monkeypatch.setattr(auth_module, "_crm_client", lambda: FakeOidcClient())
    with client.session_transaction() as session:
        session["post_login_next"] = "/my-plan"
        session["pre_auth_marker"] = "must-disappear"
    before = client.get_cookie("session")
    assert before is not None

    response = client.get("/auth/crm/callback")

    after = client.get_cookie("session")
    assert response.status_code == 302
    assert after is not None
    assert after.value != before.value
    with client.session_transaction() as session:
        assert "pre_auth_marker" not in session
        assert session["user_id"]


def test_logout_requires_csrf_and_returns_provider_url(
    client, user_client, csrf_headers, monkeypatch
):
    with client.session_transaction() as session:
        session["oidc_id_token"] = "server-side-id-token"
    monkeypatch.setattr(auth_module, "_crm_client", lambda: FakeOidcClient())

    assert client.post("/api/v1/auth/logout").status_code == 403
    response = client.post("/api/v1/auth/logout", headers=csrf_headers)
    assert response.status_code == 200
    assert response.get_json()["logout_url"].startswith(
        "https://lk.silaeder.ru/oauth/logout"
    )
    assert client.get("/api/v1/auth/session").get_json()["authenticated"] is False


def test_logout_rejects_provider_redirect_to_another_origin(
    client, user_client, csrf_headers, monkeypatch
):
    with client.session_transaction() as session:
        session["oidc_id_token"] = "server-side-id-token"
    monkeypatch.setattr(
        auth_module,
        "_crm_client",
        lambda: FakeOidcClient(logout_url="https://evil.test/steal"),
    )

    response = client.post("/api/v1/auth/logout", headers=csrf_headers)

    assert response.status_code == 200
    assert response.get_json()["logout_url"] == "http://localhost/"
    assert client.get("/api/v1/auth/session").get_json()["authenticated"] is False

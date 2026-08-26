import os

import redis
from cachelib import SimpleCache
from celery.schedules import crontab


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


class Config:
    # Keep local Compose usable even when .env is absent or contains the
    # intentionally empty example value. Production must always override this
    # stable development-only fallback.
    SECRET_KEY = os.getenv("SECRET_KEY") or "dev-only-change-me"
    ALLOW_INSECURE_DEV_SECRET = (
        os.getenv("ALLOW_INSECURE_DEV_SECRET", "false").lower() == "true"
    )
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://olympiads:olympiads@localhost:5433/olympiads",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}
    JSON_AS_ASCII = False

    ACADEMIC_YEAR = os.getenv("ACADEMIC_YEAR", "2026/27")
    CORS_ORIGINS = _split_csv(
        os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:5188")
    )
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"
    SESSION_TYPE = "redis"
    SESSION_REDIS = redis.from_url(
        os.getenv("REDIS_URL", "redis://localhost:6380/2"),
        socket_connect_timeout=1,
        socket_timeout=1,
    )
    SESSION_USE_SIGNER = True
    SESSION_KEY_PREFIX = "olympiads:session:"

    APP_BASE_URL = os.getenv("APP_BASE_URL", "http://localhost:5050").rstrip("/")
    FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL", "http://localhost:5188").rstrip("/")
    CRM_OIDC_ISSUER = os.getenv("CRM_OIDC_ISSUER", "https://lk.silaeder.ru").rstrip("/")
    CRM_OIDC_CLIENT_ID = os.getenv("CRM_OIDC_CLIENT_ID", "")
    CRM_OIDC_CLIENT_SECRET = os.getenv("CRM_OIDC_CLIENT_SECRET", "")
    CRM_OIDC_SCOPES = os.getenv(
        "CRM_OIDC_SCOPES", "openid profile email roles"
    )
    CRM_NOTIFICATION_URL = os.getenv(
        "CRM_NOTIFICATION_URL",
        f"{CRM_OIDC_ISSUER}/api/external/notifications",
    )
    CRM_NOTIFICATION_TIMEOUT_SECONDS = float(
        os.getenv("CRM_NOTIFICATION_TIMEOUT_SECONDS", "10")
    )
    CRM_NOTIFICATION_RETRY_BASE_SECONDS = int(
        os.getenv("CRM_NOTIFICATION_RETRY_BASE_SECONDS", "30")
    )
    CRM_NOTIFICATION_RETRY_MAX_SECONDS = int(
        os.getenv("CRM_NOTIFICATION_RETRY_MAX_SECONDS", "3600")
    )
    CRM_NOTIFICATION_PROCESSING_LEASE_SECONDS = int(
        os.getenv("CRM_NOTIFICATION_PROCESSING_LEASE_SECONDS", "900")
    )
    CRM_NOTIFICATION_MAX_ATTEMPTS = int(
        os.getenv("CRM_NOTIFICATION_MAX_ATTEMPTS", "12")
    )
    CRM_NOTIFICATION_MAX_AGE_DAYS = int(
        os.getenv("CRM_NOTIFICATION_MAX_AGE_DAYS", "1")
    )
    CRM_NOTIFICATION_SCAN_BATCH = int(
        os.getenv("CRM_NOTIFICATION_SCAN_BATCH", "500")
    )
    REMINDER_TIMEZONE = "Europe/Moscow"

    CELERY = {
        "broker_url": os.getenv("CELERY_BROKER_URL", "redis://localhost:6380/0"),
        "result_backend": os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6380/1"),
        "task_ignore_result": True,
        "timezone": REMINDER_TIMEZONE,
        "enable_utc": True,
        "task_acks_late": True,
        "task_reject_on_worker_lost": True,
        "worker_prefetch_multiplier": 1,
        "beat_schedule": {
            "scan-olympiad-reminders-daily": {
                "task": "reminders.scan",
                "schedule": crontab(hour=7, minute=0),
            }
        },
    }


class TestConfig(Config):
    TESTING = True
    SECRET_KEY = "test-secret"
    SQLALCHEMY_DATABASE_URI = "sqlite+pysqlite:///:memory:"
    SQLALCHEMY_ENGINE_OPTIONS = {}
    SESSION_TYPE = "cachelib"
    SESSION_CACHELIB = SimpleCache()
    SESSION_REDIS = None
    SESSION_USE_SIGNER = False
    ALLOW_INSECURE_DEV_SECRET = False
    CRM_OIDC_CLIENT_ID = "test-client"
    CRM_OIDC_CLIENT_SECRET = "test-secret"
    APP_BASE_URL = "http://localhost"
    FRONTEND_BASE_URL = "http://localhost"
    WTF_CSRF_ENABLED = False

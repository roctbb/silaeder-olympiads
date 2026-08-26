from datetime import UTC, datetime

import pytest

from app import create_app
from app.config import TestConfig
from app.extensions import db
from app.models import Admin, User


@pytest.fixture()
def app():
    application = create_app(TestConfig)
    with application.app_context():
        db.create_all()
        admin = Admin(username="editor", password_hash="")
        admin.set_password("correct-horse")
        db.session.add(admin)
        db.session.commit()
        yield application
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def admin_client(client):
    response = client.post(
        "/api/admin/session",
        json={"username": "editor", "password": "correct-horse"},
    )
    assert response.status_code == 200
    client.environ_base["HTTP_X_CSRF_TOKEN"] = response.get_json()["csrf_token"]
    return client


@pytest.fixture()
def user_id(app):
    with app.app_context():
        item = User(
            oidc_issuer="https://lk.silaeder.ru",
            oidc_subject="00000000-0000-0000-0000-000000000001",
            name="Иван Иванов",
            preferred_username="ivan",
            email="ivan@example.test",
            crm_role="student",
            object_type="students",
            last_login_at=datetime.now(UTC),
        )
        db.session.add(item)
        db.session.commit()
        return item.id


@pytest.fixture()
def user_client(client, user_id):
    with client.session_transaction() as session:
        session["user_id"] = user_id
        session["csrf_token"] = "test-csrf-token"
    return client


@pytest.fixture()
def csrf_headers():
    return {"X-CSRF-Token": "test-csrf-token"}


@pytest.fixture()
def olympiad_payload():
    return {
        "slug": "test-math",
        "name": "Тестовая олимпиада — Математика",
        "family_name": "Тестовая олимпиада",
        "profile": "Математика",
        "description": "Описание",
        "organizer": "Организатор",
        "website_url": "https://example.test",
        "geography": "russia",
        "is_team": False,
        "academic_year": "2026/27",
        "cycle_label": "Календарный цикл 2026",
        "status": "published",
        "data_status": "previous_year_estimate",
        "is_in_registry": True,
        "registry_status": "approved",
        "registry_level": 1,
        "is_popular": True,
        "registration_status": "open",
        "registration_checked_on": "2026-08-26",
        "registration_url": "https://example.test/register",
        "previous_year_reference": "2025/26",
        "eligibility_notes": "Учащиеся 8–11 классов.",
        "grades": [8, 9, 10, 11],
        "stages": [
            {
                "name": "Отборочный этап",
                "position": 1,
                "starts_on": "2026-10-01",
                "ends_on": "2026-10-31",
                "date_precision": "approximate",
                "is_date_confirmed": False,
                "format": "online",
                "source_url": "https://example.test/calendar",
            }
        ],
        "materials": [
            {
                "title": "Архив заданий",
                "material_type": "archive",
                "url": "https://example.test/archive",
                "is_official": True,
            }
        ],
        "benefits": [
            {
                "title": "Поступление без вступительных испытаний",
                "benefit_type": "bvi",
                "diploma_requirement": "Победитель или призёр 11 класса",
                "ege_subject": "Математика",
                "ege_min_score": 75,
                "admission_year": 2027,
                "university": {
                    "slug": "test-university",
                    "name": "Тестовый университет",
                    "short_name": "ТУ",
                },
                "source_url": "https://example.test/admission",
            }
        ],
        "sources": [
            {
                "title": "Официальный календарь",
                "url": "https://example.test/calendar",
                "publisher": "Организатор",
                "source_type": "calendar",
                "source_year": "2025/26",
                "accessed_on": "2026-08-25",
            }
        ],
    }

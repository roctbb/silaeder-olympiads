from sqlalchemy.exc import IntegrityError

from app.api import admin as admin_api


def test_admin_requires_login(client, olympiad_payload):
    response = client.post("/api/admin/olympiads", json=olympiad_payload)
    assert response.status_code == 401


def test_login_rejects_wrong_password(client):
    response = client.post(
        "/api/admin/session", json={"username": "editor", "password": "wrong"}
    )
    assert response.status_code == 401


def test_admin_login_rotates_session_and_returns_csrf(client):
    with client.session_transaction() as session:
        session["pre_auth_marker"] = "must-disappear"
    before = client.get_cookie("session")
    assert before is not None

    response = client.post(
        "/api/admin/session",
        json={"username": "editor", "password": "correct-horse"},
    )

    after = client.get_cookie("session")
    assert response.status_code == 200
    assert response.get_json()["csrf_token"]
    assert after is not None
    assert after.value != before.value
    with client.session_transaction() as session:
        assert session["admin_id"]
        assert session["csrf_token"] == response.get_json()["csrf_token"]
        assert "pre_auth_marker" not in session


def test_admin_mutations_and_logout_require_csrf(client, olympiad_payload):
    login = client.post(
        "/api/admin/session",
        json={"username": "editor", "password": "correct-horse"},
    )
    assert login.status_code == 200
    token = login.get_json()["csrf_token"]

    assert client.post(
        "/api/admin/olympiads", json=olympiad_payload
    ).status_code == 403
    assert client.post(
        "/api/admin/olympiads",
        headers={"X-CSRF-Token": "wrong"},
        json=olympiad_payload,
    ).status_code == 403

    created = client.post(
        "/api/admin/olympiads",
        headers={"X-CSRF-Token": token},
        json=olympiad_payload,
    )
    assert created.status_code == 201
    olympiad_payload["updated_at"] = created.get_json()["updated_at"]
    assert client.put(
        "/api/admin/olympiads/test-math", json=olympiad_payload
    ).status_code == 403
    assert client.delete("/api/admin/olympiads/test-math").status_code == 403
    assert client.delete("/api/admin/session").status_code == 403
    assert client.get("/api/admin/session").status_code == 200

    logged_out = client.delete(
        "/api/admin/session", headers={"X-CSRF-Token": token}
    )
    assert logged_out.status_code == 204
    assert client.get("/api/admin/session").status_code == 401


def test_create_update_delete(admin_client, olympiad_payload):
    created = admin_client.post("/api/admin/olympiads", json=olympiad_payload)
    assert created.status_code == 201
    assert created.get_json()["benefits"][0]["has_bvi"] is True
    assert created.get_json()["benefits"][0]["has_hundred_points"] is False
    assert admin_client.get("/api/admin/olympiads/test-math").status_code == 200
    original_updated_at = created.get_json()["updated_at"]
    original_stage_id = created.get_json()["stages"][0]["id"]

    olympiad_payload["description"] = "Обновлено"
    olympiad_payload["grades"] = [10, 11]
    olympiad_payload["benefits"][0]["benefit_type"] = "other"
    olympiad_payload["benefits"][0]["has_bvi"] = True
    olympiad_payload["benefits"][0]["has_hundred_points"] = True
    olympiad_payload["benefits"][0]["university"]["name"] = "Устаревшее название"
    olympiad_payload["updated_at"] = original_updated_at
    updated = admin_client.put("/api/admin/olympiads/test-math", json=olympiad_payload)
    assert updated.status_code == 200
    assert updated.get_json()["description"] == "Обновлено"
    assert updated.get_json()["cycle_label"] == "Календарный цикл 2026"
    assert updated.get_json()["grades"] == [10, 11]
    assert updated.get_json()["stages"][0]["id"] == original_stage_id
    assert updated.get_json()["benefits"][0]["benefit_type"] == "other"
    assert updated.get_json()["benefits"][0]["has_bvi"] is True
    assert updated.get_json()["benefits"][0]["has_hundred_points"] is True
    assert updated.get_json()["benefits"][0]["university"]["name"] == "Тестовый университет"

    stale = admin_client.put("/api/admin/olympiads/test-math", json=olympiad_payload)
    assert stale.status_code == 409

    deleted = admin_client.delete("/api/admin/olympiads/test-math")
    assert deleted.status_code == 204
    assert admin_client.get("/api/v1/olympiads/test-math").status_code == 404


def test_benefit_right_flags_require_booleans(admin_client, olympiad_payload):
    olympiad_payload["benefits"][0]["has_bvi"] = "yes"

    response = admin_client.post("/api/admin/olympiads", json=olympiad_payload)

    assert response.status_code == 400
    assert "has_bvi" in response.get_json()["error"]


def test_cycle_label_is_optional_and_length_limited(admin_client, olympiad_payload):
    olympiad_payload.pop("cycle_label")
    created = admin_client.post("/api/admin/olympiads", json=olympiad_payload)

    assert created.status_code == 201
    assert created.get_json()["cycle_label"] is None

    too_long = {
        **olympiad_payload,
        "slug": "too-long-cycle-label",
        "website_url": "https://cycle-label.example.test",
        "cycle_label": "x" * 121,
    }
    rejected = admin_client.post("/api/admin/olympiads", json=too_long)

    assert rejected.status_code == 400
    assert "cycle_label" in rejected.get_json()["error"]


def test_registration_close_timestamp_roundtrip_and_validation(
    admin_client, olympiad_payload
):
    olympiad_payload["registration_closes_at"] = "2026-08-26T11:50:00+03:00"
    created = admin_client.post("/api/admin/olympiads", json=olympiad_payload)

    assert created.status_code == 201
    assert created.get_json()["registration_url"] == "https://example.test/register"
    assert created.get_json()["registration_status"] == "open"
    assert created.get_json()["registration_checked_on"] == "2026-08-26"
    assert created.get_json()["registration_closes_at"] == (
        "2026-08-26T08:50:00+00:00"
    )
    detail = admin_client.get("/api/admin/olympiads/test-math")
    assert detail.get_json()["registration_closes_at"] == (
        "2026-08-26T08:50:00+00:00"
    )

    naive = {
        **olympiad_payload,
        "slug": "naive-registration-close",
        "registration_closes_at": "2026-08-26T08:50:00",
    }
    rejected_naive = admin_client.post("/api/admin/olympiads", json=naive)
    assert rejected_naive.status_code == 400
    assert "registration_closes_at" in rejected_naive.get_json()["error"]

    missing_url = {
        **olympiad_payload,
        "slug": "registration-close-without-url",
        "registration_url": None,
    }
    rejected_missing_url = admin_client.post(
        "/api/admin/olympiads", json=missing_url
    )
    assert rejected_missing_url.status_code == 400
    assert "registration_closes_at" in rejected_missing_url.get_json()["error"]

    announced_with_cta = {
        **olympiad_payload,
        "slug": "announced-with-registration-url",
        "registration_status": "announced",
        "registration_closes_at": None,
    }
    rejected_announced = admin_client.post(
        "/api/admin/olympiads", json=announced_with_cta
    )
    assert rejected_announced.status_code == 400
    assert "registration_url" in rejected_announced.get_json()["error"]


def test_create_rejects_existing_slug_without_overwrite(admin_client, olympiad_payload):
    created = admin_client.post("/api/admin/olympiads", json=olympiad_payload)
    assert created.status_code == 201

    duplicate = {**olympiad_payload, "name": "Молча перезаписанное название"}
    response = admin_client.post("/api/admin/olympiads", json=duplicate)

    assert response.status_code == 409
    detail = admin_client.get("/api/v1/olympiads/test-math").get_json()
    assert detail["name"] == olympiad_payload["name"]


def test_registry_status_and_flag_must_agree(admin_client, olympiad_payload):
    olympiad_payload["registry_status"] = "draft"
    olympiad_payload["is_in_registry"] = False

    response = admin_client.post("/api/admin/olympiads", json=olympiad_payload)

    assert response.status_code == 400
    assert "противоречат" in response.get_json()["error"]


def test_other_integrity_error_is_not_reported_as_slug_conflict(
    admin_client, olympiad_payload, monkeypatch
):
    def fail_create(_payload):
        raise IntegrityError(
            "INSERT",
            {},
            Exception("UNIQUE constraint failed: universities.slug"),
        )

    monkeypatch.setattr(admin_api, "create_catalog_record", fail_create)

    response = admin_client.post("/api/admin/olympiads", json=olympiad_payload)

    assert response.status_code == 400
    assert response.get_json()["error"] == "Нарушены ограничения целостности данных"


def test_validation_is_atomic(admin_client, olympiad_payload):
    olympiad_payload["grades"] = [4]
    response = admin_client.post("/api/admin/olympiads", json=olympiad_payload)
    assert response.status_code == 400
    listing = admin_client.get("/api/v1/olympiads").get_json()
    assert listing["pagination"]["total"] == 0


def test_javascript_url_is_rejected(admin_client, olympiad_payload):
    olympiad_payload["website_url"] = "javascript:alert(1)"
    response = admin_client.post("/api/admin/olympiads", json=olympiad_payload)
    assert response.status_code == 400


def test_invalid_stage_date_range_is_rejected(admin_client, olympiad_payload):
    olympiad_payload["stages"][0]["starts_on"] = "2026-10-31"
    olympiad_payload["stages"][0]["ends_on"] = "2026-10-01"
    response = admin_client.post("/api/admin/olympiads", json=olympiad_payload)
    assert response.status_code == 400


def test_overlong_stage_name_is_rejected(admin_client, olympiad_payload):
    olympiad_payload["stages"][0]["name"] = "x" * 181
    response = admin_client.post("/api/admin/olympiads", json=olympiad_payload)
    assert response.status_code == 400

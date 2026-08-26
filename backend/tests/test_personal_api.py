import json
from copy import deepcopy

from sqlalchemy import select

from app.extensions import db
from app.models import EditionStatus, Stage, UserOlympiadPlan, UserStageProgress


def _login(client, user_id):
    with client.session_transaction() as session:
        session.clear()
        session["user_id"] = user_id
        session["csrf_token"] = "test-csrf-token"


def test_public_catalog_stays_anonymous_and_personal_writes_require_login(
    admin_client, olympiad_payload
):
    created = admin_client.post("/api/admin/olympiads", json=olympiad_payload)
    assert created.status_code == 201
    stage_id = created.get_json()["stages"][0]["id"]
    with admin_client.session_transaction() as session:
        session.clear()

    assert admin_client.get("/api/v1/metadata").status_code == 200
    assert admin_client.get("/api/v1/olympiads").status_code == 200
    assert admin_client.get("/api/v1/olympiads/test-math").status_code == 200
    assert admin_client.get("/api/v1/calendar?month=2026-10").status_code == 200
    assert admin_client.get("/api/v1/olympiads/test-math/planning").status_code == 200

    assert admin_client.post("/api/v1/olympiads/test-math/planning", json={}).status_code == 401
    assert (
        admin_client.patch("/api/v1/me", json={"grade": 9}).status_code == 401
    )
    assert (
        admin_client.put(
            f"/api/v1/olympiads/test-math/stages/{stage_id}/progress",
            json={"participated": True},
        ).status_code
        == 401
    )
    assert admin_client.post("/api/v1/auth/logout").status_code == 401


def test_plan_privacy_reminders_grade_and_stage_progress(
    app, admin_client, olympiad_payload, user_id, csrf_headers
):
    created = admin_client.post("/api/admin/olympiads", json=olympiad_payload)
    assert created.status_code == 201
    stage = created.get_json()["stages"][0]
    _login(admin_client, user_id)

    session_payload = admin_client.get("/api/v1/auth/session").get_json()
    assert session_payload["authenticated"] is True
    assert session_payload["csrf_token"] == "test-csrf-token"
    assert session_payload["user"]["grade"] is None

    missing_csrf = admin_client.post("/api/v1/olympiads/test-math/planning", json={})
    assert missing_csrf.status_code == 403
    assert admin_client.patch("/api/v1/me", json={"grade": 9}).status_code == 403

    added = admin_client.post(
        "/api/v1/olympiads/test-math/planning",
        headers=csrf_headers,
        json={},
    )
    assert added.status_code == 201
    plan = added.get_json()
    assert plan["status"] == "planned"
    assert plan["academic_year"] == "2026/27"
    assert plan["cycle_label"] == "Календарный цикл 2026"
    assert plan["edition_status"] == "published"
    assert plan["is_name_public"] is False
    assert plan["reminders_enabled"] is True
    assert plan["reminder_days_before"] == [7, 1]
    assert admin_client.put(
        f'/api/v1/olympiads/test-math/stages/{stage["id"]}/progress',
        json={"participated": True},
    ).status_code == 403
    assert admin_client.delete(
        "/api/v1/olympiads/test-math/planning"
    ).status_code == 403
    assert (
        admin_client.post(
            "/api/v1/olympiads/test-math/planning",
            headers=csrf_headers,
            json={},
        ).status_code
        == 409
    )

    with admin_client.session_transaction() as session:
        session["admin_id"] = 1
    protected_delete = admin_client.delete(
        "/api/admin/olympiads/test-math", headers=csrf_headers
    )
    assert protected_delete.status_code == 409
    assert "личных планах" in protected_delete.get_json()["error"]

    anonymous = app.test_client()
    public_before = anonymous.get("/api/v1/olympiads/test-math/planning").get_json()
    assert public_before == {
        "participant_count": 1,
        "public_participants": [],
        "plan": None,
    }

    updated = admin_client.patch(
        "/api/v1/olympiads/test-math/planning",
        headers=csrf_headers,
        json={
            "status": "registered",
            "is_name_public": True,
            "reminders_enabled": False,
            "reminder_days_before": [],
        },
    )
    assert updated.status_code == 200
    assert updated.get_json()["reminder_days_before"] == []
    assert updated.get_json()["status"] == "registered"

    public_after = anonymous.get("/api/v1/olympiads/test-math/planning").get_json()
    assert public_after["participant_count"] == 1
    assert public_after["public_participants"] == [{"name": "Иван Иванов"}]
    detail = anonymous.get("/api/v1/olympiads/test-math").get_json()
    assert detail["participant_count"] == 1
    assert detail["public_participants"] == [{"name": "Иван Иванов"}]

    invalid_grade = admin_client.patch(
        "/api/v1/me", headers=csrf_headers, json={"grade": 12}
    )
    assert invalid_grade.status_code == 400
    grade = admin_client.patch(
        "/api/v1/me", headers=csrf_headers, json={"grade": 9}
    )
    assert grade.status_code == 200
    assert grade.get_json()["user"]["grade"] == 9

    progressed = admin_client.put(
        f'/api/v1/olympiads/test-math/stages/{stage["id"]}/progress',
        headers=csrf_headers,
        json={"participated": True, "advanced": True, "result": "Диплом II степени"},
    )
    assert progressed.status_code == 200
    assert progressed.get_json() == {
        "stage_id": stage["id"],
        "stage_key": stage["key"],
        "stage_name": "Отборочный этап",
        "stage_is_active": True,
        "participated": True,
        "advanced": True,
        "result": "Диплом II степени",
        "updated_at": progressed.get_json()["updated_at"],
    }

    reset = admin_client.put(
        f'/api/v1/olympiads/test-math/stages/{stage["id"]}/progress',
        headers=csrf_headers,
        json={"participated": False, "advanced": True, "result": "Не должно сохраниться"},
    )
    assert reset.status_code == 200
    assert reset.get_json()["advanced"] is None
    assert reset.get_json()["result"] is None

    my_plan = admin_client.get("/api/v1/me/plan").get_json()
    assert len(my_plan["items"]) == 1
    assert len(my_plan["upcoming_stages"]) == 1
    assert my_plan["upcoming_stages"][0]["stage_key"] == stage["key"]

    removed = admin_client.delete(
        "/api/v1/olympiads/test-math/planning", headers=csrf_headers
    )
    assert removed.status_code == 204
    assert admin_client.put(
        f'/api/v1/olympiads/test-math/stages/{stage["id"]}/progress',
        headers=csrf_headers,
        json={"participated": True},
    ).status_code == 409
    with app.app_context():
        assert db.session.scalar(select(UserOlympiadPlan)) is None
        assert db.session.scalar(select(UserStageProgress)) is None


def test_stage_key_preserves_progress_when_a_stage_is_inserted_before_it(
    app, admin_client, olympiad_payload, user_id, csrf_headers
):
    initial = deepcopy(olympiad_payload)
    initial["stages"] = [
        {
            **initial["stages"][0],
            "key": "final",
            "name": "Заключительный этап",
            "position": 2,
        }
    ]
    created = admin_client.post("/api/admin/olympiads", json=initial)
    final_stage_id = created.get_json()["stages"][0]["id"]
    _login(admin_client, user_id)
    assert admin_client.post(
        "/api/v1/olympiads/test-math/planning", headers=csrf_headers, json={}
    ).status_code == 201
    assert admin_client.put(
        f"/api/v1/olympiads/test-math/stages/{final_stage_id}/progress",
        headers=csrf_headers,
        json={"participated": True, "advanced": False, "result": "Финалист"},
    ).status_code == 200

    _login(admin_client, user_id)
    # The admin session is separate from OIDC; restore it only for this catalog update.
    with admin_client.session_transaction() as session:
        session["admin_id"] = 1
    current = admin_client.get("/api/admin/olympiads/test-math").get_json()
    updated_payload = deepcopy(initial)
    updated_payload["updated_at"] = current["updated_at"]
    updated_payload["stages"] = [
        {
            **initial["stages"][0],
            "key": "qualifying",
            "name": "Новый отборочный этап",
            "position": 1,
        },
        {
            **initial["stages"][0],
            "key": "final",
            "name": "Заключительный этап",
            "position": 2,
        },
    ]
    updated = admin_client.put(
        "/api/admin/olympiads/test-math",
        headers=csrf_headers,
        json=updated_payload,
    )
    assert updated.status_code == 200
    stages = {item["key"]: item for item in updated.get_json()["stages"]}
    assert stages["final"]["id"] == final_stage_id

    _login(admin_client, user_id)
    plan = admin_client.get("/api/v1/me/plan").get_json()["items"][0]
    assert plan["stage_progress"][0]["stage_key"] == "final"
    assert plan["stage_progress"][0]["result"] == "Финалист"

    # Retiring the stage hides it from the public calendar but keeps its result history.
    with admin_client.session_transaction() as session:
        session["admin_id"] = 1
    current = admin_client.get("/api/admin/olympiads/test-math").get_json()
    retired_payload = deepcopy(updated_payload)
    retired_payload["updated_at"] = current["updated_at"]
    retired_payload["stages"] = [updated_payload["stages"][0]]
    assert admin_client.put(
        "/api/admin/olympiads/test-math",
        headers=csrf_headers,
        json=retired_payload,
    ).status_code == 200

    _login(admin_client, user_id)
    history = admin_client.get("/api/v1/me/plan").get_json()["items"][0]
    assert history["stage_progress"][0]["stage_key"] == "final"
    assert history["stage_progress"][0]["stage_is_active"] is False
    assert admin_client.put(
        f"/api/v1/olympiads/test-math/stages/{final_stage_id}/progress",
        headers=csrf_headers,
        json={"participated": True, "result": "Нельзя перезаписать"},
    ).status_code == 404
    with app.app_context():
        final_stage = db.session.get(Stage, final_stage_id)
        assert final_stage is not None
        assert final_stage.is_active is False


def test_archived_plan_stays_private_manageable_and_visible_to_its_owner(
    app, admin_client, olympiad_payload, user_id, csrf_headers, tmp_path
):
    created = admin_client.post("/api/admin/olympiads", json=olympiad_payload)
    assert created.status_code == 201
    stage_id = created.get_json()["stages"][0]["id"]

    retained = deepcopy(olympiad_payload)
    retained.update(
        slug="retained-math",
        name="Оставшаяся олимпиада",
        family_name="Оставшаяся олимпиада",
        website_url="https://retained.example.test",
    )
    assert admin_client.post("/api/admin/olympiads", json=retained).status_code == 201

    _login(admin_client, user_id)
    assert admin_client.post(
        "/api/v1/olympiads/test-math/planning",
        headers=csrf_headers,
        json={"is_name_public": True},
    ).status_code == 201
    assert admin_client.put(
        f"/api/v1/olympiads/test-math/stages/{stage_id}/progress",
        headers=csrf_headers,
        json={"participated": True, "result": "Финалист"},
    ).status_code == 200

    source = tmp_path / "catalog.json"
    source.write_text(json.dumps({"records": [retained]}), encoding="utf-8")
    imported = app.test_cli_runner().invoke(
        args=["import-catalog", str(source), "--sync"]
    )
    assert imported.exit_code == 0, imported.output
    assert "архивировано отсутствующих сезонов: 1" in imported.output

    with app.app_context():
        plan_row = db.session.scalar(select(UserOlympiadPlan))
        assert plan_row is not None
        assert plan_row.edition.status == EditionStatus.ARCHIVED
        assert db.session.scalar(select(UserStageProgress)) is not None

    assert admin_client.get("/api/v1/olympiads/test-math").status_code == 404
    assert (
        admin_client.get("/api/v1/olympiads/test-math/planning").status_code
        == 404
    )
    assert admin_client.post(
        "/api/v1/olympiads/test-math/planning",
        headers=csrf_headers,
        json={},
    ).status_code == 404

    personal = admin_client.get("/api/v1/me/plan").get_json()
    assert personal["upcoming_stages"] == []
    assert len(personal["items"]) == 1
    archived = personal["items"][0]
    assert archived["edition_status"] == "archived"
    assert archived["is_name_public"] is True
    assert archived["stage_progress"][0]["result"] == "Финалист"

    deactivated = admin_client.patch(
        "/api/v1/olympiads/test-math/planning",
        headers=csrf_headers,
        json={
            "is_name_public": False,
            "reminders_enabled": False,
            "reminder_days_before": [],
        },
    )
    assert deactivated.status_code == 200
    assert deactivated.get_json()["edition_status"] == "archived"
    assert deactivated.get_json()["is_name_public"] is False
    assert deactivated.get_json()["reminders_enabled"] is False

    removed = admin_client.delete(
        "/api/v1/olympiads/test-math/planning", headers=csrf_headers
    )
    assert removed.status_code == 204
    with app.app_context():
        assert db.session.scalar(select(UserOlympiadPlan)) is None
        assert db.session.scalar(select(UserStageProgress)) is None

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.extensions import db
from app.models import (
    ClassNotificationDispatch,
    ClassStudent,
    EditionStatus,
    Olympiad,
    OlympiadEdition,
    PlanStatus,
    RegistrationStatus,
    ReminderStatus,
    Stage,
    User,
    UserOlympiadPlan,
)
from app.services.class_notifications import (
    deliver_class_notification_once,
    due_class_notification_ids,
    schedule_class_notifications,
)

NOW = datetime(2026, 9, 22, 9, tzinfo=UTC)


def make_user(name, role="student", **kwargs):
    user = User(
        name=name,
        oidc_issuer="https://lk.silaeder.ru",
        oidc_subject=name,
        crm_role=role,
        object_type="students" if role == "student" else "teachers",
        last_login_at=NOW,
        **kwargs,
    )
    db.session.add(user)
    db.session.flush()
    return user


def sign_in(client, user):
    with client.session_transaction() as session:
        session.clear()
        session["user_id"] = user.id
        session["csrf_token"] = "csrf"


def test_permissions_and_csrf(client, user_client):
    assert user_client.get("/api/v1/my-class").status_code == 403
    teacher = make_user("Учитель", "teacher")
    student = make_user("Ученик")
    db.session.commit()
    sign_in(client, teacher)
    assert (
        client.post("/api/v1/my-class/students", json={"student_id": student.id}).status_code == 403
    )
    response = client.post(
        "/api/v1/my-class/students",
        json={"student_id": teacher.id},
        headers={"X-CSRF-Token": "csrf"},
    )
    assert response.status_code == 404
    with client.session_transaction() as session:
        session.clear()
    assert client.get("/api/v1/my-class").status_code == 401
    assert client.get("/api/v1/my-class/candidates").status_code == 401


@pytest.mark.parametrize("role", ["teacher", "admin"])
def test_class_is_personal_search_add_remove_and_duplicate(client, role):
    teacher = make_user("Первый", role)
    other = make_user("Второй", "teacher")
    student = make_user("Анна", grade=9)
    make_user("Борис", grade=10)
    db.session.commit()
    sign_in(client, teacher)
    result = client.get("/api/v1/my-class/candidates?q=Ан&grade=9").get_json()
    assert result["items"] == [{"id": student.id, "name": "Анна", "grade": 9}]
    assert client.get("/api/v1/my-class/candidates?q=%").get_json()["items"] == []
    assert client.get("/api/v1/my-class/candidates?grade=bad").status_code == 400
    for expected in [201, 200]:
        response = client.post(
            "/api/v1/my-class/students",
            json={"student_id": student.id},
            headers={"X-CSRF-Token": "csrf"},
        )
        assert response.status_code == expected
    response = client.get("/api/v1/my-class")
    assert response.headers["Cache-Control"] == "private, no-store"
    assert response.get_json()["items"][0]["plans"] == []
    assert response.get_json()["notifications_available"] is True
    assert len(client.get("/api/v1/my-class/candidates").get_json()["items"]) == 1
    sign_in(client, other)
    assert client.get("/api/v1/my-class").get_json()["items"] == []
    client.delete(f"/api/v1/my-class/students/{student.id}", headers={"X-CSRF-Token": "csrf"})
    sign_in(client, teacher)
    assert len(client.get("/api/v1/my-class").get_json()["items"]) == 1
    client.delete(f"/api/v1/my-class/students/{student.id}", headers={"X-CSRF-Token": "csrf"})
    assert client.get("/api/v1/my-class").get_json()["items"] == []
    assert db.session.get(User, student.id) is not None


def test_local_admin_class(admin_client):
    student = make_user("Анна")
    db.session.commit()
    assert (
        admin_client.post("/api/v1/my-class/students", json={"student_id": student.id}).status_code
        == 201
    )
    response = admin_client.get("/api/v1/my-class").get_json()
    assert response["notifications_available"] is False
    assert response["items"][0]["name"] == "Анна"


@pytest.fixture()
def class_plans(app):
    teacher = make_user("Учитель", "teacher")
    second_teacher = make_user("Другой учитель", "admin")
    students = [make_user("Анна"), make_user("Борис"), make_user("Чужой ученик")]
    olympiad = Olympiad(
        slug="math",
        name="Математика",
        family_name="Олимпиада",
        profile="Математика",
        website_url="https://example.test",
    )
    edition = OlympiadEdition(
        olympiad=olympiad, academic_year="2026/27", status=EditionStatus.PUBLISHED
    )
    stage = Stage(
        edition=edition,
        key="first",
        name="Отбор",
        is_date_confirmed=True,
        starts_on=(NOW + timedelta(days=7)).date(),
    )
    db.session.add(stage)
    plans = [
        UserOlympiadPlan(
            user=s,
            edition=edition,
            reminders_enabled=False,
            is_name_public=False,
            created_at=NOW - timedelta(days=10),
        )
        for s in students
    ]
    db.session.add_all(plans)
    db.session.add_all(
        [
            ClassStudent(teacher=teacher, student=s, created_at=NOW - timedelta(days=10))
            for s in students[:2]
        ]
        + [
            ClassStudent(
                teacher=second_teacher, student=students[1], created_at=NOW - timedelta(days=10)
            )
        ]
    )
    db.session.commit()
    return teacher, second_teacher, students, plans, stage


def test_grouping_delivery_and_isolation(class_plans, client):
    teacher, other, students, plans, stage = class_plans
    sign_in(client, teacher)
    result = client.get("/api/v1/my-class").get_json()
    assert result["items"][0]["plans"][0]["olympiad"]["name"] == "Математика"
    stage.edition.stages.append(
        Stage(
            key="second",
            name="Второй этап",
            is_date_confirmed=True,
            starts_on=(NOW + timedelta(days=1)).date(),
        )
    )
    db.session.commit()
    created = schedule_class_notifications(now=NOW)
    assert len(created) == 2
    assert schedule_class_notifications(now=NOW) == []
    assert due_class_notification_ids(now=NOW) == created
    dispatches = db.session.scalars(select(ClassNotificationDispatch)).all()
    first = next(d for d in dispatches if d.teacher_id == teacher.id)
    assert "Анна" in first.payload["message"] and "Борис" in first.payload["message"]
    assert "Чужой ученик" not in first.payload["message"]
    assert "Отбор" in first.payload["message"] and "Второй этап" in first.payload["message"]
    second = next(d for d in dispatches if d.teacher_id == other.id)
    assert "Анна" not in second.payload["message"]
    calls = []

    def post(url, **kwargs):
        calls.append(kwargs)
        return type("Response", (), {"status_code": 202})()

    assert deliver_class_notification_once(first.id, http_post=post, now=NOW).status == "sent"
    assert deliver_class_notification_once(first.id, http_post=post, now=NOW).status == "finished"
    assert len(calls) == 1
    assert calls[0]["json"]["recipient_sub"] == teacher.oidc_subject
    assert calls[0]["auth"] == ("test-client", "test-secret")


@pytest.mark.parametrize("change", ["removed", "completed", "unconfirmed", "archived", "role"])
def test_cancel_stale_dispatch(class_plans, change):
    teacher, other, students, plans, stage = class_plans
    created = schedule_class_notifications(now=NOW)
    if change == "removed":
        for member in db.session.scalars(select(ClassStudent)).all():
            db.session.delete(member)
    elif change == "completed":
        for plan in plans:
            plan.status = PlanStatus.COMPLETED
    elif change == "unconfirmed":
        stage.is_date_confirmed = False
    elif change == "archived":
        stage.edition.status = EditionStatus.ARCHIVED
    else:
        teacher.crm_role = other.crm_role = "student"
    db.session.commit()
    for item_id in created:
        result = deliver_class_notification_once(
            item_id, now=NOW, http_post=lambda *a, **k: pytest.fail("must not call CRM")
        )
        assert result.status == "cancelled"


def test_retries_keep_body_and_idempotency_key(class_plans):
    [first, _] = schedule_class_notifications(now=NOW)
    calls = []

    def post(url, **kwargs):
        calls.append(kwargs)
        return type(
            "Response", (), {"status_code": 503 if len(calls) == 1 else 200, "headers": {}}
        )()

    outcome = deliver_class_notification_once(first, http_post=post, now=NOW)
    assert outcome.status == "retry"
    next_time = NOW + timedelta(seconds=outcome.retry_after + 1)
    assert first in due_class_notification_ids(now=next_time)
    assert deliver_class_notification_once(first, http_post=post, now=next_time).status == "sent"
    assert calls[0] == calls[1]


def test_removed_student_excluded_before_delivery(class_plans):
    teacher, _, students, _, _ = class_plans
    schedule_class_notifications(now=NOW)
    item = db.session.scalar(
        select(ClassNotificationDispatch).where(ClassNotificationDispatch.teacher_id == teacher.id)
    )
    member = db.session.scalar(
        select(ClassStudent).where(
            ClassStudent.teacher_id == teacher.id, ClassStudent.student_id == students[0].id
        )
    )
    db.session.delete(member)
    db.session.commit()

    def post(url, **kwargs):
        assert "Анна" not in kwargs["json"]["message"]
        assert "Борис" in kwargs["json"]["message"]
        return type("Response", (), {"status_code": 202})()

    assert deliver_class_notification_once(item.id, http_post=post, now=NOW).status == "sent"


def test_registration_groups_with_stage_and_notifies_once(class_plans):
    _, _, _, _, stage = class_plans
    edition = stage.edition
    edition.registration_status = RegistrationStatus.OPEN
    edition.registration_url = "https://example.test/register"
    edition.registration_opened_at = NOW
    db.session.commit()
    ids = schedule_class_notifications(now=NOW)
    assert len(ids) == 2
    for item_id in ids:
        item = db.session.get(ClassNotificationDispatch, item_id)
        assert "Открылась регистрация" in item.payload["message"]
        assert "Отбор" in item.payload["message"]
    assert schedule_class_notifications(now=NOW + timedelta(hours=1)) == []
    assert schedule_class_notifications(now=NOW + timedelta(days=1)) == []


def test_outbox_lease_and_expiry(class_plans):
    first, second = schedule_class_notifications(now=NOW)
    item = db.session.get(ClassNotificationDispatch, first)
    item.status = ReminderStatus.PROCESSING
    item.last_attempt_at = NOW
    item.attempt_count = 1
    db.session.commit()

    def no_post(*args, **kwargs):
        pytest.fail("must not call CRM")

    assert deliver_class_notification_once(first, now=NOW, http_post=no_post).status == "retry"
    assert first not in due_class_notification_ids(now=NOW)
    assert first in due_class_notification_ids(now=NOW + timedelta(hours=1))
    assert (
        deliver_class_notification_once(
            second, now=NOW + timedelta(days=2), http_post=no_post
        ).status
        == "cancelled"
    )

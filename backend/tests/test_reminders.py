from __future__ import annotations

import re
from datetime import UTC, date, datetime, timedelta

import pytest
import requests
from sqlalchemy import func

import app.services.reminders as reminder_service
from app.extensions import db
from app.models import (
    EditionStatus,
    Olympiad,
    OlympiadEdition,
    PlanStatus,
    RegistrationNotificationDispatch,
    RegistrationStatus,
    ReminderDispatch,
    ReminderStatus,
    Stage,
    User,
    UserOlympiadPlan,
)
from app.services.registration_notifications import (
    deliver_registration_notification_once,
    due_registration_notification_ids,
    schedule_registration_notification_dispatches,
)
from app.services.reminders import (
    deliver_reminder_once,
    due_dispatch_ids,
    schedule_reminder_dispatches,
)


class FakeResponse:
    def __init__(self, status_code: int, headers: dict[str, str] | None = None):
        self.status_code = status_code
        self.headers = headers or {}


def _create_plan(
    *,
    event_on: date,
    confirmed: bool = True,
    active: bool = True,
    plan_status: PlanStatus = PlanStatus.PLANNED,
    reminders_enabled: bool = True,
    reminder_days: list[int] | None = None,
    suffix: str = "main",
) -> tuple[UserOlympiadPlan, Stage]:
    olympiad = Olympiad(
        slug=f"test-reminder-{suffix}",
        name=f"Тестовая олимпиада {suffix}",
        family_name="Тестовая олимпиада",
        profile="Математика",
        website_url="https://example.test",
    )
    edition = OlympiadEdition(
        olympiad=olympiad,
        academic_year="2026/27",
        status=EditionStatus.PUBLISHED,
    )
    stage = Stage(
        edition=edition,
        key=f"final-{suffix}",
        name="Заключительный этап",
        position=1,
        is_active=active,
        starts_on=event_on,
        is_date_confirmed=confirmed,
    )
    user = User(
        oidc_issuer="https://lk.silaeder.ru",
        oidc_subject=f"00000000-0000-4000-8000-{len(suffix):012d}",
        name=f"Ученик {suffix}",
        last_login_at=datetime.now(UTC),
    )
    plan = UserOlympiadPlan(
        user=user,
        edition=edition,
        status=plan_status,
        reminders_enabled=reminders_enabled,
        reminder_days_before=reminder_days or [7, 1],
    )
    db.session.add_all([plan, stage])
    db.session.commit()
    return plan, stage


def _create_due_dispatch(today: date) -> ReminderDispatch:
    _create_plan(event_on=today + timedelta(days=7))
    created = schedule_reminder_dispatches(today=today)
    assert len(created) == 2
    dispatch = db.session.scalar(
        db.select(ReminderDispatch).where(ReminderDispatch.scheduled_for == today)
    )
    assert dispatch is not None
    return dispatch


def _open_registration(
    plan: UserOlympiadPlan, *, opened_at: datetime, url: str = "https://example.test/register"
) -> None:
    plan.created_at = opened_at - timedelta(seconds=1)
    plan.edition.registration_status = RegistrationStatus.OPEN
    plan.edition.registration_url = url
    plan.edition.registration_opened_at = opened_at
    db.session.commit()


def test_scanner_persists_confirmed_active_reminders_and_deduplicates(app):
    today = date(2026, 9, 1)
    plan, confirmed = _create_plan(event_on=date(2026, 9, 8))
    edition = plan.edition
    edition.stages.extend(
        [
            Stage(
                key="unconfirmed",
                name="Неподтверждённый этап",
                position=2,
                starts_on=date(2026, 9, 8),
                is_date_confirmed=False,
            ),
            Stage(
                key="inactive",
                name="Архивный этап",
                position=3,
                starts_on=date(2026, 9, 8),
                is_date_confirmed=True,
                is_active=False,
            ),
        ]
    )
    _create_plan(
        event_on=date(2026, 9, 8),
        plan_status=PlanStatus.COMPLETED,
        suffix="completed",
    )
    _create_plan(
        event_on=date(2026, 9, 8),
        reminders_enabled=False,
        suffix="disabled",
    )
    db.session.commit()

    created = schedule_reminder_dispatches(today=today)
    assert len(created) == 2
    assert schedule_reminder_dispatches(today=today) == []

    dispatches = db.session.scalars(db.select(ReminderDispatch)).all()
    assert {item.stage_id for item in dispatches} == {confirmed.id}
    assert {item.days_before for item in dispatches} == {1, 7}
    assert all(item.status == ReminderStatus.PENDING for item in dispatches)
    assert all(
        re.fullmatch(r"[A-Za-z0-9._:-]{8,128}", item.idempotency_key)
        for item in dispatches
    )
    assert all(item.payload["recipient_sub"] == plan.user.oidc_subject for item in dispatches)
    assert all(
        item.payload["url"]
        == "http://localhost/olympiads/test-reminder-main?academic_year=2026%2F27"
        for item in dispatches
    )

    due = due_dispatch_ids(now=datetime(2026, 9, 1, 4, tzinfo=UTC))
    assert due == [next(item.id for item in dispatches if item.days_before == 7)]


def test_scanner_tolerates_a_concurrent_unique_insert(app, monkeypatch):
    today = date(2026, 9, 1)
    plan, stage = _create_plan(
        event_on=date(2026, 9, 8), reminder_days=[7], suffix="race"
    )
    original_payload = reminder_service._notification_payload
    inserted = False

    def insert_competing_dispatch(current_plan, current_stage, days_before):
        nonlocal inserted
        payload = original_payload(current_plan, current_stage, days_before)
        if not inserted:
            inserted = True
            competing = ReminderDispatch(
                plan_id=plan.id,
                stage_id=stage.id,
                event_on=stage.starts_on,
                scheduled_for=today,
                days_before=days_before,
                idempotency_key=reminder_service._idempotency_key(
                    plan, stage, stage.starts_on, days_before
                ),
                payload=payload,
                payload_sha256=reminder_service._payload_digest(payload),
            )
            db.session.add(competing)
            db.session.commit()
        return payload

    monkeypatch.setattr(
        reminder_service, "_notification_payload", insert_competing_dispatch
    )

    assert schedule_reminder_dispatches(today=today) == []
    assert db.session.scalar(db.select(func.count()).select_from(ReminderDispatch)) == 1


def test_successful_delivery_uses_basic_auth_tls_and_saved_body(app):
    today = date(2026, 9, 1)
    dispatch = _create_due_dispatch(today)
    persisted_payload = dict(dispatch.payload)
    calls = []

    def fake_post(url, **kwargs):
        calls.append((url, kwargs))
        return FakeResponse(202)

    outcome = deliver_reminder_once(
        dispatch.id,
        http_post=fake_post,
        now=datetime(2026, 9, 1, 4, tzinfo=UTC),
    )

    db.session.refresh(dispatch)
    assert outcome.status == "sent"
    assert dispatch.status == ReminderStatus.SENT
    assert dispatch.attempt_count == 1
    assert dispatch.response_status == 202
    assert calls == [
        (
            "https://lk.silaeder.ru/api/external/notifications",
            {
                "auth": ("test-client", "test-secret"),
                "headers": {"Idempotency-Key": dispatch.idempotency_key},
                "json": persisted_payload,
                "timeout": 10.0,
                "verify": True,
                "allow_redirects": False,
            },
        )
    ]


@pytest.mark.parametrize("failure", ["timeout", "rate_limit", "server_error"])
def test_transient_failures_are_retried_without_changing_key_or_body(app, failure):
    today = date(2026, 9, 1)
    dispatch = _create_due_dispatch(today)
    key = dispatch.idempotency_key
    payload = dict(dispatch.payload)
    calls = []

    def fake_post(_url, **kwargs):
        calls.append(kwargs)
        if failure == "timeout":
            raise requests.Timeout("details must not be persisted")
        if failure == "rate_limit":
            return FakeResponse(429, {"Retry-After": "120"})
        return FakeResponse(503)

    now = datetime(2026, 9, 1, 4, tzinfo=UTC)
    outcome = deliver_reminder_once(dispatch.id, http_post=fake_post, now=now)

    db.session.refresh(dispatch)
    assert outcome.status == "retry"
    assert outcome.retry_after is not None
    assert dispatch.status == ReminderStatus.RETRY
    assert dispatch.attempt_count == 1
    assert dispatch.idempotency_key == key
    assert dispatch.payload == payload
    stored_next_attempt = dispatch.next_attempt_at
    if stored_next_attempt.tzinfo is None:
        stored_next_attempt = stored_next_attempt.replace(tzinfo=UTC)
    assert stored_next_attempt >= now + timedelta(seconds=30)
    if failure == "rate_limit":
        assert outcome.retry_after >= 120
    assert "details" not in (dispatch.last_error or "")
    assert calls[0]["headers"] == {"Idempotency-Key": key}
    assert calls[0]["json"] == payload


def test_retry_reuses_exact_key_and_body_then_accepts_idempotent_replay(app):
    today = date(2026, 9, 1)
    dispatch = _create_due_dispatch(today)
    calls = []

    def rate_limited(_url, **kwargs):
        calls.append(kwargs)
        return FakeResponse(429, {"Retry-After": "120"})

    first_now = datetime(2026, 9, 1, 4, tzinfo=UTC)
    first = deliver_reminder_once(dispatch.id, http_post=rate_limited, now=first_now)
    assert first.status == "retry"

    def replay(_url, **kwargs):
        calls.append(kwargs)
        return FakeResponse(200)

    second = deliver_reminder_once(
        dispatch.id,
        http_post=replay,
        now=first_now + timedelta(seconds=first.retry_after + 1),
    )
    db.session.refresh(dispatch)
    assert second.status == "sent"
    assert dispatch.status == ReminderStatus.SENT
    assert dispatch.attempt_count == 2
    assert calls[0]["headers"] == calls[1]["headers"]
    assert calls[0]["json"] == calls[1]["json"]


def test_other_client_errors_fail_permanently_and_are_not_due_again(app):
    today = date(2026, 9, 1)
    dispatch = _create_due_dispatch(today)

    outcome = deliver_reminder_once(
        dispatch.id,
        http_post=lambda *_args, **_kwargs: FakeResponse(422),
        now=datetime(2026, 9, 1, 4, tzinfo=UTC),
    )

    db.session.refresh(dispatch)
    assert outcome.status == "permanent_failed"
    assert dispatch.status == ReminderStatus.PERMANENT_FAILED
    assert dispatch.response_status == 422
    assert dispatch.next_attempt_at is None
    assert due_dispatch_ids(now=datetime(2026, 9, 1, 5, tzinfo=UTC)) == []


def test_retry_limit_stops_a_transient_failure_storm(app):
    app.config["CRM_NOTIFICATION_MAX_ATTEMPTS"] = 2
    today = date(2026, 9, 1)
    dispatch = _create_due_dispatch(today)
    calls = 0

    def unavailable(*_args, **_kwargs):
        nonlocal calls
        calls += 1
        return FakeResponse(503)

    first_now = datetime(2026, 9, 1, 4, tzinfo=UTC)
    first = deliver_reminder_once(dispatch.id, http_post=unavailable, now=first_now)
    assert first.status == "retry"
    second = deliver_reminder_once(
        dispatch.id,
        http_post=unavailable,
        now=first_now + timedelta(seconds=first.retry_after + 1),
    )

    db.session.refresh(dispatch)
    assert second.status == "permanent_failed"
    assert calls == 2
    assert dispatch.status == ReminderStatus.PERMANENT_FAILED
    assert dispatch.last_error == "retry_limit_exhausted"


def test_expired_or_stale_identity_dispatch_is_cancelled_without_crm_call(app):
    today = date(2026, 9, 1)
    expired = _create_due_dispatch(today)
    outcome = deliver_reminder_once(
        expired.id,
        http_post=lambda *_args, **_kwargs: pytest.fail("CRM must not be called"),
        now=datetime(2026, 9, 3, 4, tzinfo=UTC),
    )
    assert outcome.status == "cancelled"
    db.session.refresh(expired)
    assert expired.last_error == "reminder_expired"

    stale_plan, _stage = _create_plan(
        event_on=today + timedelta(days=7), suffix="stale-identity"
    )
    stale_id = next(
        dispatch_id
        for dispatch_id in schedule_reminder_dispatches(today=today)
        if db.session.get(ReminderDispatch, dispatch_id).plan_id == stale_plan.id
        and db.session.get(ReminderDispatch, dispatch_id).scheduled_for == today
    )
    stale = db.session.get(ReminderDispatch, stale_id)
    stale.plan.user.oidc_subject = "00000000-0000-4000-8000-999999999999"
    db.session.commit()

    outcome = deliver_reminder_once(
        stale.id,
        http_post=lambda *_args, **_kwargs: pytest.fail("CRM must not be called"),
        now=datetime(2026, 9, 1, 4, tzinfo=UTC),
    )
    assert outcome.status == "cancelled"
    db.session.refresh(stale)
    assert stale.last_error == "reminder_no_longer_current"


def test_fresh_processing_lease_defers_duplicate_delivery(app):
    today = date(2026, 9, 1)
    dispatch = _create_due_dispatch(today)
    now = datetime(2026, 9, 1, 4, tzinfo=UTC)
    dispatch.status = ReminderStatus.PROCESSING
    dispatch.attempt_count = 1
    dispatch.last_attempt_at = now
    db.session.commit()

    outcome = deliver_reminder_once(
        dispatch.id,
        http_post=lambda *_args, **_kwargs: pytest.fail("CRM must not be called"),
        now=now + timedelta(seconds=1),
    )

    assert outcome.status == "retry"
    assert outcome.retry_after >= 899


def test_changed_or_unconfirmed_stage_cancels_persisted_reminder(app):
    today = date(2026, 9, 1)
    dispatch = _create_due_dispatch(today)
    dispatch.stage.is_date_confirmed = False
    db.session.commit()

    outcome = deliver_reminder_once(
        dispatch.id,
        http_post=lambda *_args, **_kwargs: pytest.fail("CRM must not be called"),
        now=datetime(2026, 9, 1, 4, tzinfo=UTC),
    )

    db.session.refresh(dispatch)
    assert outcome.status == "cancelled"
    assert dispatch.status == ReminderStatus.CANCELLED


def test_registration_opening_notifies_existing_subscribers_once(app):
    now = datetime(2026, 9, 5, 9, tzinfo=UTC)
    plan, _stage = _create_plan(
        event_on=date(2026, 10, 1), suffix="registration"
    )
    _open_registration(plan, opened_at=now)

    created = schedule_registration_notification_dispatches(now=now)
    assert len(created) == 1
    assert schedule_registration_notification_dispatches(now=now) == []

    dispatch = db.session.get(RegistrationNotificationDispatch, created[0])
    assert dispatch is not None
    assert dispatch.status == ReminderStatus.PENDING
    assert dispatch.payload == {
        "recipient_sub": plan.user.oidc_subject,
        "title": "Открылась регистрация: Тестовая олимпиада — Математика",
        "message": (
            "На олимпиаду «Тестовая олимпиада — Математика» открылась регистрация. "
            "Проверьте сроки и перейдите к официальной форме со страницы олимпиады."
        ),
        "url": (
            "http://localhost/olympiads/test-reminder-registration"
            "?academic_year=2026%2F27"
        ),
    }
    assert due_registration_notification_ids(now=now) == [dispatch.id]

    calls = []

    def fake_post(url, **kwargs):
        calls.append((url, kwargs))
        return FakeResponse(202)

    outcome = deliver_registration_notification_once(
        dispatch.id, http_post=fake_post, now=now
    )
    db.session.refresh(dispatch)
    assert outcome.status == "sent"
    assert dispatch.status == ReminderStatus.SENT
    assert calls[0][1]["headers"] == {"Idempotency-Key": dispatch.idempotency_key}
    assert calls[0][1]["json"] == dispatch.payload


def test_registration_notification_skips_late_or_unsubscribed_plans(app):
    now = datetime(2026, 9, 5, 9, tzinfo=UTC)
    late_plan, _stage = _create_plan(
        event_on=date(2026, 10, 1), suffix="late-registration"
    )
    _open_registration(late_plan, opened_at=now - timedelta(hours=1))
    late_plan.created_at = now

    disabled_plan, _stage = _create_plan(
        event_on=date(2026, 10, 1),
        suffix="disabled-registration",
        reminders_enabled=False,
    )
    _open_registration(disabled_plan, opened_at=now)
    db.session.commit()

    assert schedule_registration_notification_dispatches(now=now) == []


def test_registration_notification_is_cancelled_if_registration_closes(app):
    now = datetime(2026, 9, 5, 9, tzinfo=UTC)
    plan, _stage = _create_plan(
        event_on=date(2026, 10, 1), suffix="closed-registration"
    )
    _open_registration(plan, opened_at=now)
    [dispatch_id] = schedule_registration_notification_dispatches(now=now)
    plan.edition.registration_status = RegistrationStatus.NOT_OPEN
    plan.edition.registration_url = None
    plan.edition.registration_opened_at = None
    db.session.commit()

    outcome = deliver_registration_notification_once(
        dispatch_id,
        http_post=lambda *_args, **_kwargs: pytest.fail("CRM must not be called"),
        now=now,
    )
    dispatch = db.session.get(RegistrationNotificationDispatch, dispatch_id)
    assert outcome.status == "cancelled"
    assert dispatch.status == ReminderStatus.CANCELLED
    assert dispatch.last_error == "registration_no_longer_open"


def test_periodic_task_schedules_and_enqueues_without_calling_crm(app, monkeypatch):
    from app import tasks

    queued = []
    monkeypatch.setattr(tasks, "schedule_reminder_dispatches", lambda: [10, 11])
    monkeypatch.setattr(
        tasks, "schedule_registration_notification_dispatches", lambda: [20]
    )
    monkeypatch.setattr(tasks, "due_dispatch_ids", lambda: [10])
    monkeypatch.setattr(tasks, "due_registration_notification_ids", lambda: [20])
    monkeypatch.setattr(
        tasks.deliver_reminder,
        "apply_async",
        lambda *, args: queued.append(args),
    )
    monkeypatch.setattr(
        tasks.deliver_registration_notification,
        "apply_async",
        lambda *, args: queued.append(args),
    )

    assert tasks.scan_reminders.run() == {"created": 3, "enqueued": 2}
    assert queued == [(10,), (20,)]
    schedule = app.config["CELERY"]["beat_schedule"][
        "scan-olympiad-notifications"
    ]
    assert schedule["task"] == "reminders.scan"
    assert app.config["CELERY"]["timezone"] == "Europe/Moscow"
